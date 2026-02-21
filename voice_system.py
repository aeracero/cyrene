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
# ★ Directory Setup
# ──────────────────────────────────────────────
DATA_DIR = Path("/data") if os.path.exists("/data") else Path("./data")
VOICE_DIR = Path(__file__).parent / "voices" 
DATA_DIR.mkdir(parents=True, exist_ok=True)
VOICE_DIR.mkdir(parents=True, exist_ok=True)

# ──────────────────────────────────────────────
# ★ Opus Loader
# ──────────────────────────────────────────────
def init_opus():
    if not discord.opus.is_loaded():
        try:
            discord.opus.load_opus('libopus.so.0')
            print("[System Log] Successfully loaded Opus library (libopus.so.0)")
        except Exception as e:
            import ctypes.util
            fallback = ctypes.util.find_library('opus')
            if fallback:
                try:
                    discord.opus.load_opus(fallback)
                    print(f"[System Log] Successfully loaded Opus from {fallback}")
                    return
                except: pass
            print(f"[Player Error] Opus library could not be loaded: {e}")

# ──────────────────────────────────────────────
# ★ FFmpeg Setup
# ──────────────────────────────────────────────
def get_ffmpeg_path():
    return shutil.which("ffmpeg") or "ffmpeg"

# ──────────────────────────────────────────────
# ★ TTS Global Model & Lock
# ──────────────────────────────────────────────
tts_model = None
TTS_LOCK = asyncio.Lock()

def load_tts_model():
    global tts_model
    if not HAS_TTS: return
    if tts_model is not None: return

    print("[TTS Log] Loading TTS model (XTTS v2)...")
    try:
        model = TTS("tts_models/multilingual/multi-dataset/xtts_v2", gpu=False)
        tts_model = model
        print("[TTS Log] TTS model loaded successfully.")
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
                import torch
                if torch.cuda.is_available(): torch.cuda.empty_cache()
            except: pass
            
            try:
                libc = ctypes.CDLL("libc.so.6")
                libc.malloc_trim(0)
                print("[System Log] malloc_trim(0) executed. RAM returned to OS.")
            except: pass

# ──────────────────────────────────────────────
# ★ VoiceState Manager (日本語バグ対策版)
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
        if error:
            print(f"[Player Error] Previous track error: {error}")
        
        if self.queue:
            self.is_playing = True
            file_path, voice_client = self.queue.pop(0)
            print(f"[Player Log] Preparing to play file: {file_path}")
            
            def after_playing(e):
                print(f"[Player Log] Finished playing: {file_path}")
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
                    print(f"[Player Error] Exception in play_next: {e}")
                    traceback.print_exc()
                    self.play_next(e)
            else:
                self.play_next(None)
        else:
            self.is_playing = False

    async def add_text_to_queue(self, text: str, voice_client, lang: str = "ja"):
        current_model = tts_model
        if current_model is None: return

        ref_wavs = list(VOICE_DIR.glob("*.wav"))
        if not ref_wavs: 
            print("[TTS Error] No reference audio found!")
            return

        ref_wavs.sort()
        speaker_wav_paths = [str(p) for p in ref_wavs[:3]]
        
        # 記号の徹底除去
        clean_text = re.sub(r'<[^>]+>', '', text)
        clean_text = re.sub(r'[♪♡♥❤♫♬♩*＊_~〜]', '', clean_text)
        clean_text = clean_text.replace("\n", "。").replace("http", "URL")
        
        if not clean_text.strip(): return
        if len(clean_text) > 300: clean_text = clean_text[:300] + "..."

        raw_sentences = re.split(r'(?<=[。！？.!?])', clean_text)
        
        sentences = []
        for s in raw_sentences:
            s = s.strip()
            if not s: continue
            
            # ★ 最重要バグ対策: 文末に句読点がない場合、強制的に「。」を追加して暴走を防ぐ
            if not re.search(r'[。！？.!?]$', s):
                s += '。'
            
            sentences.append(s)

        for i, sentence in enumerate(sentences):
            if len(sentence) < 2 and not re.search(r'[ぁ-んァ-ン一-龥]', sentence):
                continue
                
            target_lang = "ja" if re.search(r'[ぁ-んァ-ン一-龥]', sentence) else "en"

            timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")
            output_path = DATA_DIR / f"tts_{timestamp}_{i}.wav"

            try:
                async with TTS_LOCK:
                    start_time = time.time()
                    func = functools.partial(
                        current_model.tts_to_file,
                        text=sentence,
                        file_path=str(output_path),
                        speaker_wav=speaker_wav_paths, 
                        language=target_lang
                    )
                    loop = asyncio.get_running_loop()
                    await loop.run_in_executor(None, func)
                    elapsed = time.time() - start_time
                    print(f"[TTS Log] Chunk {i} generated in {elapsed:.2f}s: '{sentence}' (Lang: {target_lang})")
                
                if output_path.exists():
                    self.queue.append((str(output_path), voice_client))
                    if not self.is_playing:
                        self.play_next()
            except Exception as e:
                print(f"[TTS Error] Chunk {i} failed: {e}")
                traceback.print_exc()

voice_states = {}

def get_voice_state(bot, guild_id):
    if guild_id not in voice_states:
        voice_states[guild_id] = VoiceState(bot)
    return voice_states[guild_id]