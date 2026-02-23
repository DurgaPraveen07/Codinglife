"""
ROBO AI — Flask + Gemini (google-genai NEW SDK) + pyttsx3 TTS + SpeechRecognition STT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Install:  pip install -r requirements.txt
Run:      python app.py
Browser:  http://localhost:5000  (use Chrome for mic)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from google import genai
from google.genai import types
import pyttsx3
import os
import threading
import queue
import time

# ══════════════════════════════════════════════════
#  >>>  PASTE YOUR GEMINI API KEY HERE  <<<
#  Free key: https://aistudio.google.com/app/apikey
# ══════════════════════════════════════════════════
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# ══════════════════════════════════════════════════

MODEL_NAME = "gemini-1.5-flash"   # Latest fast free model

app = Flask(__name__, static_folder=".")
CORS(app)

# ══════════════════════════════════════════════════
#  GEMINI CLIENT  (google-genai new SDK)
# ══════════════════════════════════════════════════
client    = None
robo_chat = None
chat_lock = threading.Lock()

SYSTEM_INSTRUCTION = (
    "You are ROBO AI, a friendly and intelligent voice assistant robot. "
    "Keep all answers concise and natural for speech — 1 to 3 sentences max "
    "unless the user explicitly asks for more detail. "
    "NEVER use markdown, bullet points, asterisks, hashtags, or special formatting. "
    "Output plain spoken text only. Be warm, helpful, clear, and occasionally witty."
)


def get_client():
    global client
    if client is None:
        client = genai.Client(api_key=GEMINI_API_KEY)
    return client


def get_chat():
    """Return or create the persistent multi-turn chat session."""
    global robo_chat
    if robo_chat is None:
        robo_chat = get_client().chats.create(
            model=MODEL_NAME,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                max_output_tokens=300,
                temperature=0.7,
            ),
        )
    return robo_chat


# ══════════════════════════════════════════════════
#  TTS  —  pyttsx3  (fast, offline, no lag)
# ══════════════════════════════════════════════════
tts_q = queue.Queue()


def _tts_worker():
    engine = pyttsx3.init()
    engine.setProperty('rate',   162)
    engine.setProperty('volume', 1.0)

    voices = engine.getProperty('voices')
    for v in voices:
        if any(w in v.name.lower() for w in ['david','mark','daniel','james','male']):
            engine.setProperty('voice', v.id)
            print(f"[TTS] Voice: {v.name}")
            break

    print("[TTS] Engine ready ✅")

    while True:
        text = tts_q.get()
        if text is None:
            break
        try:
            engine.say(text)
            engine.runAndWait()
        except Exception as e:
            print(f"[TTS ERROR] {e}")
        finally:
            tts_q.task_done()


threading.Thread(target=_tts_worker, daemon=True, name="TTS").start()


def speak(text: str):
    """Queue text for TTS — flushes pending speech first."""
    while not tts_q.empty():
        try:
            tts_q.get_nowait()
            tts_q.task_done()
        except Exception:
            break
    tts_q.put(text)


# ══════════════════════════════════════════════════
#  STT  —  SpeechRecognition  (Python mic capture)
# ══════════════════════════════════════════════════
stt_available  = False
stt_recognizer = None

try:
    import speech_recognition as sr
    stt_recognizer = sr.Recognizer()
    stt_recognizer.energy_threshold        = 300
    stt_recognizer.dynamic_energy_threshold = True
    stt_available = True
    print("[STT] speech_recognition ready ✅")
except ImportError:
    print("[STT] Not installed — browser STT will be used instead")

stt_lock = threading.Lock()


def listen_and_transcribe(timeout: int = 8, phrase_limit: int = 15) -> dict:
    if not stt_available:
        return {"text": "", "error": "speech_recognition not installed"}

    if not stt_lock.acquire(blocking=False):
        return {"text": "", "error": "Microphone already in use"}

    try:
        with sr.Microphone() as source:
            print("[STT] Calibrating...")
            stt_recognizer.adjust_for_ambient_noise(source, duration=0.5)
            print(f"[STT] Listening ({timeout}s max)...")
            audio = stt_recognizer.listen(
                source, timeout=timeout, phrase_time_limit=phrase_limit
            )
        text = stt_recognizer.recognize_google(audio)
        print(f"[STT] Heard: «{text}»")
        return {"text": text, "error": None}

    except sr.WaitTimeoutError:
        return {"text": "", "error": "No speech detected — please try again"}
    except sr.UnknownValueError:
        return {"text": "", "error": "Could not understand audio"}
    except sr.RequestError as e:
        return {"text": "", "error": f"Google STT error: {e}"}
    except Exception as e:
        return {"text": "", "error": str(e)}
    finally:
        stt_lock.release()


# ══════════════════════════════════════════════════
#  ROUTES
# ══════════════════════════════════════════════════

@app.route("/")
def index():
    return send_from_directory(".", "index.html")


@app.route("/chat", methods=["POST"])
def chat():
    """Receive message → Gemini → speak → return JSON."""
    try:
        data     = request.get_json(force=True)
        user_msg = (data.get("message") or "").strip()

        if not user_msg:
            return jsonify({"error": "Empty message"}), 400

        if GEMINI_API_KEY == "YOUR_GEMINI_API_KEY_HERE":
            return jsonify({"error": "API key missing! Set GEMINI_API_KEY in app.py"}), 500

        with chat_lock:
            session = get_chat()
            resp    = session.send_message(user_msg)
            reply   = resp.text.strip()

        print(f"  YOU  → {user_msg}")
        print(f"  ROBO → {reply}")

        speak(reply)   # non-blocking Python TTS

        return jsonify({"response": reply})

    except Exception as e:
        print(f"[ERROR /chat] {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/stt", methods=["POST"])
def stt_endpoint():
    """Capture from system mic → return transcript."""
    data         = request.get_json(force=True) or {}
    timeout      = int(data.get("timeout",      8))
    phrase_limit = int(data.get("phrase_limit", 15))
    return jsonify(listen_and_transcribe(timeout, phrase_limit))


@app.route("/speak", methods=["POST"])
def speak_endpoint():
    """Manually trigger TTS for any text."""
    data = request.get_json(force=True)
    text = (data.get("text") or "").strip()
    if text:
        speak(text)
    return jsonify({"status": "ok"})


@app.route("/reset", methods=["POST"])
def reset():
    """Start a fresh conversation."""
    global robo_chat
    with chat_lock:
        robo_chat = None
    return jsonify({"status": "ok", "message": "Conversation reset!"})


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status":    "ok",
        "model":     MODEL_NAME,
        "sdk":       "google-genai (new)",
        "tts":       "pyttsx3",
        "stt":       "speech_recognition" if stt_available else "browser-only",
        "api_ready": GEMINI_API_KEY != "YOUR_GEMINI_API_KEY_HERE",
    })


# ══════════════════════════════════════════════════
#  STARTUP
# ══════════════════════════════════════════════════
if __name__ == "__main__":
    print()
    print("═" * 60)
    print("   🤖  ROBO AI  —  Powered by google-genai SDK")
    print("═" * 60)

    if GEMINI_API_KEY == "YOUR_GEMINI_API_KEY_HERE":
        print()
        print("  ⚠️  API KEY NOT SET!")
        print("  1. Go to  https://aistudio.google.com/app/apikey")
        print("  2. Click  'Create API Key'  → copy it")
        print("  3. Open   app.py  and replace  YOUR_GEMINI_API_KEY_HERE")
        print("  4. Run    python app.py  again")
        print()
    else:
        print(f"\n  ✅  API key      : set")
        print(f"  ✅  Model        : {MODEL_NAME}")
        print(f"  ✅  SDK          : google-genai  (official new SDK)")
        print(f"  ✅  TTS          : pyttsx3  (fast offline speech output)")
        print(f"  ✅  STT          : {'speech_recognition (Python mic)' if stt_available else 'browser STT (pyaudio not installed)'}")

    print()
    print("  🌐  Browser  →  http://localhost:5000")
    print("  🎤  Use Chrome for best microphone support")
    print()
    print("  🟡 YELLOW = Normal/Speaking   🟢 GREEN = Listening")
    print("  🟠 ORANGE = Thinking          🔴 RED   = Error")
    print("═" * 60)
    print()

    time.sleep(0.8)
    app.run(debug=False, host="0.0.0.0", port=5000, threaded=True)
