import os
import re
import asyncio
import datetime
import functools
import gc
import shutil
import time
import traceback
import ctypes
from pathlib import Path
import discord

# ──────────────────────────────────────────────
# ★ Coqui TTS License & Import
# ──────────────────────────────────────────────
os.environ["COQUI_TOS_AGREED"] = "1"

# 省メモリ・高速化のための環境変数設定
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

try:
    from TTS.api import TTS
    import torch
    
    torch.set_num_threads(4) 
    
    HAS_TTS = True
    print("[System] TTS library and Torch imported.")
except ImportError:
    HAS_TTS = False
    print("[System] TTS library not found. Voice features disabled.")

# ──────────────────────────────────────────────
# ★ Directory Setup & WAV Mapping
# ──────────────────────────────────────────────
DATA_DIR = Path("/data") if os.path.exists("/data") else Path("./data")
VOICE_DIR = Path(__file__).parent / "voices" 
DATA_DIR.mkdir(parents=True, exist_ok=True)
VOICE_DIR.mkdir(parents=True, exist_ok=True)

# ★ 3つのWAVファイルをリストとして指定してクオリティを最大化する
# もし日本語と英語で使う3つのファイルを分けたい場合は、ここのリストの中身を変更してください。
# 現在は、アップロードされている3つのファイルを両方の言語で共通して使用する設定にしています。
WAV_MAPPING = {
    "ja": [
        str(VOICE_DIR / "VO_JA_Archive_Cyrene_1-_1_.wav"),
        str(VOICE_DIR / "VO_JA_Archive_Cyrene_5.wav"),
        str(VOICE_DIR / "VO_JA_Archive_Cyrene_14.wav")
    ],
    "en": [
        str(VOICE_DIR / "VO_Archive_Cyrene_1.wav"),
        str(VOICE_DIR / "VO_Archive_Cyrene_5.wav"),
        str(VOICE_DIR / "VO_Archive_Cyrene_14.wav")
    ]
}

# ──────────────────────────────────────────────
# ★ Opus Loader & FFmpeg Setup
# ──────────────────────────────────────────────
def init_opus():
    if not discord.opus.is_loaded():
        try:
            discord.opus.load_opus('libopus.so.0')
        except Exception as e:
            import ctypes.util
            fallback = ctypes.util.find_library('opus')
            if fallback:
                try: discord.opus.load_opus(fallback); return
                except: pass
            print(f"[Player Error] Opus library could not be loaded: {e}")

def get_ffmpeg_path():
    return shutil.which("ffmpeg") or "ffmpeg"

# ──────────────────────────────────────────────
# ★ TTS Global Model & Lock
# ──────────────────────────────────────────────
tts_model = None
TTS_LOCK = asyncio.Lock()

def load_tts_model():
    global tts_model
    if not HAS_TTS or tts_model is not None: return

    print("[TTS Log] Loading TTS model (XTTS v2)...")
    try:
        use_gpu = torch.cuda.is_available()
        model = TTS("tts_models/multilingual/multi-dataset/xtts_v2", gpu=use_gpu)
        tts_model = model
        print(f"[TTS Log] TTS model loaded successfully. (GPU Enabled: {use_gpu})")
        
    except Exception as e:
        print(f"[TTS Error] Failed to load TTS model: {e}")
        traceback.print_exc()

async def unload_tts_model():
    global tts_model
    async with TTS_LOCK:
        if tts_model is not None:
            print("[System Log] Unloading TTS model to free RAM...")
            try: del tts_model.synthesizer
            except: pass
            del tts_model
            tts_model = None
            
            gc.collect()
            try:
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    torch.cuda.ipc_collect()
            except: pass
            
            try:
                libc = ctypes.CDLL("libc.so.6")
                libc.malloc_trim(0)
            except: pass

# ──────────────────────────────────────────────
# ★ VoiceState Manager
# ──────────────────────────────────────────────
class VoiceState:
    def __init__(self, bot):
        self.bot = bot
        self.queue = []
        self.is_playing = False
        self.mode = "bot_only"
        self.target_user_id = None
        self.read_channel_id = None

    def play_next(self, error=None):
        if error: print(f"[Player Error] Previous track error: {error}")
        
        if self.queue:
            self.is_playing = True
            file_path, voice_client = self.queue.pop(0)
            
            def after_playing(e):
                if os.path.exists(file_path):
                    try: os.remove(file_path)
                    except: pass
                self.play_next(e)

            if voice_client and voice_client.is_connected():
                try:
                    ffmpeg_executable = get_ffmpeg_path()
                    source = discord.FFmpegPCMAudio(executable=ffmpeg_executable, source=file_path)
                    voice_client.play(source, after=after_playing)
                except Exception as e:
                    self.play_next(e)
            else:
                self.play_next(None)
        else:
            self.is_playing = False

    async def add_text_to_queue(self, text: str, voice_client, lang: str = "ja"):
        current_model = tts_model
        if current_model is None: return

        clean_text = re.sub(r'https?://\S+', '', text)
        clean_text = re.sub(r'<[^>]+>', '', clean_text)
        clean_text = re.sub(r'[♪♡♥❤♫♬♩*＊_~〜]', '', clean_text)
        
        clean_text = clean_text.replace('。', '. ').replace('、', ', ')
        clean_text = clean_text.replace('？', '?').replace('！', '!')
        clean_text = re.sub(r'\.{2,}|…', ',', clean_text)
        clean_text = re.sub(r'\?+', '?', clean_text)
        clean_text = re.sub(r'!+', '!', clean_text)
        clean_text = re.sub(r'([,.?!])', r'\1 ', clean_text)
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()
        
        if not clean_text: return
        if len(clean_text) > 150: clean_text = clean_text[:150] + "..."

        target_lang = "en" if lang == "en" else "ja"
        
        # ★ ここでリスト（3つのファイルパス）を取得します
        speaker_wav_paths = WAV_MAPPING.get(target_lang)
        
        # 万が一指定したファイルが見つからない場合のフォールバック（voices内の全wavを使う）
        if not speaker_wav_paths or not all(os.path.exists(p) for p in speaker_wav_paths):
            ref_wavs = list(VOICE_DIR.glob("*.wav"))
            if not ref_wavs: return
            speaker_wav_paths = [str(w) for w in ref_wavs] # 見つかったWAVをすべてリスト化

        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")
        output_path = DATA_DIR / f"tts_{timestamp}.wav"

        try:
            async with TTS_LOCK:
                start_time = time.time()
                
                # speaker_wav にリストを渡して実行
                func = functools.partial(
                    current_model.tts_to_file,
                    text=clean_text,
                    file_path=str(output_path),
                    speaker_wav=speaker_wav_paths, # ★ 複数のファイルを同時に使用
                    language=target_lang
                )
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, func)
                
                elapsed = time.time() - start_time
                print(f"[TTS Log] Generated in {elapsed:.2f}s (Lang: {target_lang}): '{clean_text}'")
                
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            
            if output_path.exists():
                self.queue.append((str(output_path), voice_client))
                if not self.is_playing:
                    self.play_next()
        except Exception as e:
            print(f"[TTS Error] Generation failed: {e}")
            traceback.print_exc()

voice_states = {}
def get_voice_state(bot, guild_id):
    if guild_id not in voice_states:
        voice_states[guild_id] = VoiceState(bot)
    return voice_states[guild_id]