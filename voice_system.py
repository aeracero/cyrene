import os
import re
import asyncio
import datetime
import shutil
import time
import traceback
import ctypes
import urllib.parse
import aiohttp
from pathlib import Path
import discord

# ──────────────────────────────────────────────
# ★ API & Directory Setup
# ──────────────────────────────────────────────
TTS_API_URL = os.getenv("TTS_API_URL", "http://127.0.0.1:9880/")

def set_api_url(new_url: str):
    global TTS_API_URL
    if not new_url.endswith("/"):
        new_url += "/"
    TTS_API_URL = new_url

DEFAULT_REF_WAV = "/Users/aeracero/Desktop/Programming/cyrene_discord_bot/voice_optimized/cyrene_hi2.ogg"
DEFAULT_PROMPT_TEXT = "ハーイ、久しぶりね！2人きりの素敵な時間を、あなたはどう過ごしたいかしら？"
DEFAULT_PROMPT_LANG = "ja"

DATA_DIR = Path("/data") if os.path.exists("/data") else Path("./data")
DATA_DIR.mkdir(parents=True, exist_ok=True)

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

tts_model = "API_MODE_ACTIVE"
def load_tts_model(): print("[System] API Mode.")
async def unload_tts_model(): print("[System] API Mode.")

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
        if len(clean_text) > 300: clean_text = clean_text[:300] + "..."

        target_lang = "en" if lang == "en" else "ja"
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")
        output_path = DATA_DIR / f"tts_{timestamp}.wav"

        url = (
            f"{TTS_API_URL}"
            f"?refer_wav_path={urllib.parse.quote(DEFAULT_REF_WAV)}"
            f"&prompt_text={urllib.parse.quote(DEFAULT_PROMPT_TEXT)}"
            f"&prompt_language={DEFAULT_PROMPT_LANG}"
            f"&text={urllib.parse.quote(clean_text)}"
            f"&text_language={target_lang}"
            f"&text_split_method=cut4"
        )

        headers = {"ngrok-skip-browser-warning": "true"}

        try:
            start_time = time.time()
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        audio_data = await response.read()
                        with open(output_path, "wb") as f:
                            f.write(audio_data)
                        
                        elapsed = time.time() - start_time
                        print(f"[TTS Log] API Generated in {elapsed:.2f}s: '{clean_text}'")
                        
                        if output_path.exists():
                            self.queue.append((str(output_path), voice_client))
                            if not self.is_playing:
                                self.play_next()
                    else:
                        print(f"[TTS Error] API returned status {response.status}: {await response.text()}")
        except Exception as e:
            print(f"[TTS Error] API Request failed: {e}")

voice_states = {}
def get_voice_state(bot, guild_id):
    if guild_id not in voice_states:
        voice_states[guild_id] = VoiceState(bot)
    return voice_states[guild_id]
