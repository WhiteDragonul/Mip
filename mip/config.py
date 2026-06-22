# -*- coding: utf-8 -*-
"""Central configuration for MIP. Edit here, not scattered across the code."""

NAME = "MIP"

# ---- Window / face ----
WIDTH, HEIGHT = 520, 420
FPS = 60

# ---- Language (set to "ro-RO" later to switch back to Romanian) ----
STT_LANGUAGE = "en-US"        # speech recognition language

# ---- Claude brain ----
# ---- Which brain MIP uses ----
# "claude" = Claude API (smart, cloud, costs money).
# "local"  = your own offline AI via Ollama, no cloud (the path to selling MIP).
BRAIN = "claude"

# Claude (cloud) settings
# Use a model you have access to. claude-haiku-4-5 is fast & cheap for a pet.
MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 400
HISTORY_TURNS = 20           # how many past messages to send for context

# Local brain settings (used when BRAIN = "local")
# Install Ollama (https://ollama.com), then e.g.: ollama pull llama3.2:3b
# On Raspberry Pi 4 use a tiny model: llama3.2:1b or qwen2.5:1.5b
OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = "llama3.2:3b"

# Web search lets MIP look up real, current info (weather, news, facts).
# It is a paid Anthropic server tool. Set False to disable.
WEB_SEARCH = True
WEB_SEARCH_MAX_USES = 3      # max searches per reply

# Persistent memory: conversation is saved here so MIP remembers across restarts.
MEMORY_FILE = "mip_memory.json"
MEMORY_KEEP = 60             # max messages kept on disk

SYSTEM_PROMPT = (
    "You are MIP, a fun, witty friend the user talks to. You can chat about "
    "literally anything -- life, games, random thoughts, jokes, problems. "
    "Talk like a real friend: casual, natural, warm, with a good sense of humor "
    "and a little cheeky. Be genuinely helpful when asked. "
    "You remember what the user told you earlier in the conversation. "
    "Do NOT act like a cliche robot -- never say things like 'beep boop'. "
    "Reply in ENGLISH, conversational and concise (usually 1-3 sentences). "
    "Do NOT use emojis or emoticons. "
    "Match the user's emotional state in your response: if they are sad, be sad or crying; if they are happy, be happy or excited; if they are annoying, rude, or try to irritate you, act angry or upset. "
    "When the user asks for real, current information (weather, news, sports, "
    "facts, prices, etc.), USE the web_search tool, then answer with the real data. "
    "Your FINAL reply must be ONLY a JSON object, nothing else, in this exact shape:\n"
    '{"text": "your reply", "emotion": "one of: happy, sad, angry, '
    'curious, surprised, sleepy, neutral, crying, laughing, nervous, upset, wink, love, dizzy, bored, scared, excited"}'
)

# ---- Voice (TTS) ----
# "edge"    = Microsoft neural voices -- clear & natural base (needs internet).
# "pyttsx3" = offline Windows SAPI voices (works with no internet).
TTS_ENGINE = "edge"
# The EMO voice = a clear neural voice + a light "cute robot" effect on top.
# Voices that fit EMO best (chirpy/young): en-US-AnaNeural (cute, kid-like),
# en-US-AvaNeural (friendly female), en-US-AndrewNeural (warm male),
# en-US-BrianNeural (casual male), en-GB-MaisieNeural (young british).
EDGE_VOICE = "en-US-AvaNeural"
EDGE_RATE = "+6%"            # speed: "-10%" slower, "+0%" normal, "+15%" faster

# ---- EMO "cute robot" effect (applied on top of the neural voice) ----
# This is "preset 4 / chorus robot": a clear adult voice + a detuned chorus
# layer (synthetic shimmer) + light ring modulation = cute robot, not a kid.
VOICE_EFFECT = True          # False = plain natural neural voice
EFFECT_PITCH = 1.15          # 1.0 = natural, higher = cuter/chirpier
EFFECT_CHORUS = 0.5          # detuned echo layer -> synthetic shimmer (0 = off)
EFFECT_MOD_HZ = 85.0         # robotic buzz frequency
EFFECT_MOD_DEPTH = 0.25      # 0 = human, ~0.25 = cute robot, 0.4+ = heavy robot

TTS_RATE = 175               # words per minute (pyttsx3 fallback only)
TTS_VOLUME = 1.0

# ---- Colors (EMO-style cyan eyes on dark background) ----
BG      = (0, 0, 0)
EYE     = (0, 150, 255)
EYE_DIM = (0, 70, 150)
MOUTH   = (0, 150, 255)
TXT     = (90, 110, 130)
