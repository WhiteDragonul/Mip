# MIP — roadmap to a sellable, offline product

Goal: drop the cloud dependencies so MIP runs fully on-device (laptop now,
Raspberry Pi 4 later), is free to run, and can be mass-produced.

There are **three** cloud pieces to replace, not just Claude:

| Piece | Now (cloud) | Replace with (offline, commercial-friendly) |
|-------|-------------|---------------------------------------------|
| Brain | Claude API  | Local LLM via **Ollama** / llama.cpp |
| Hearing (STT) | Google `recognize_google` | **Vosk** or **whisper.cpp** |
| Voice (TTS)   | edge-tts (Microsoft online) | **Piper** (neural, offline, free for commercial use) |

The code is already structured so each is a swappable module.

---

## 1. Brain — your own AI (already pluggable)

Switch in `mip/config.py`:
```python
BRAIN = "local"            # instead of "claude"
OLLAMA_MODEL = "llama3.2:3b"
```

Setup (dev laptop):
1. Install Ollama: https://ollama.com
2. `ollama pull llama3.2:3b`
3. Run MIP. It talks through the local model — no internet, no cost.

If no model is running, MIP falls back to a small rule-based personality
(`mip/brain/local_brain.py`) so it always talks.

**On the Raspberry Pi 4** (no GPU, 4–8 GB RAM) use a tiny model:
- `llama3.2:1b`, `qwen2.5:1.5b`, or `gemma2:2b` (quantized).
- Expect a few seconds per reply. For snappier responses, consider a small
  fine-tuned model or a more powerful board (Pi 5, or a Jetson / mini-PC).

**Making the personality truly "yours":**
- Short term: shape it entirely through `SYSTEM_PROMPT` + the rule-based layer.
- Medium term: **fine-tune** a small open model (LoRA) on example MIP dialogues
  so the personality is baked in and consistent. Tools: Unsloth, axolotl.
- Keep the `{text, emotion}` JSON contract so the face keeps working.

**Licensing for selling:** prefer permissive models — Qwen2.5 (Apache-2.0),
Gemma (open weights, check terms), Phi (MIT). Llama has a community license
that's fine well below 700M MAU. Always re-check the license before shipping.

---

## 2. Hearing — offline speech-to-text

Replace `recognize_google` with an offline engine behind the same
`Voice.listen()` method (`mip/hardware/voice_local.py`):
- **Vosk** — light, runs on Pi, decent accuracy, many languages. Easy first step.
- **whisper.cpp** / faster-whisper `tiny`/`base` — better accuracy, heavier.

Both are free for commercial use.

---

## 3. Voice — offline text-to-speech (Piper)

Replace edge-tts with **Piper** (https://github.com/rhasspy/piper):
- Neural, natural, runs offline, fast even on a Pi, free for commercial use.
- Outputs WAV → keep the existing `_apply_effect()` to add MIP's cute-robot
  character on top, then play it. The voice tuner (`tune_voice.py`) still works.

---

## 4. Physical product (Raspberry Pi 4) checklist

- Display: SPI TFT — implement `hardware/display_spi.py` (see README porting table).
- Camera: picamera2 — implement `hardware/camera_picam.py`; drive pan/tilt servos.
- Motors: DRV8833 on wheels — new `Motion` backend on GPIO.
- IR edge sensors: `Sensors` backend to stop at table edges.
- Audio: USB mic/speakers — current `LocalVoice` works as-is.
- Boot: run MIP as a systemd service on power-up.

---

## Suggested order

1. ✅ Brain is pluggable (`BRAIN = "local"` + Ollama).
2. Swap TTS → Piper (offline voice, keep the effect).
3. Swap STT → Vosk (offline hearing).
4. Now MIP is 100% offline on the laptop. Validate the personality.
5. Fine-tune the personality model.
6. Port hardware backends to the Pi.
7. Add motors / sensors / pan-tilt.
8. Package: enclosure, systemd autostart, mass production.
