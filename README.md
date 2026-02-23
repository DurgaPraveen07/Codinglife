# 🤖 ROBO AI — Full Setup Guide

## Files
```
robo_ai/
├── index.html        ← Full ROBO UI with STT live panel
├── app.py            ← Flask + Gemini + pyttsx3 TTS + SpeechRecognition STT
├── requirements.txt  ← Python packages
└── README.md
```

---

## ⚡ Quick Start

### 1. Get FREE Gemini API Key
→ https://aistudio.google.com/app/apikey
→ Sign in → Create API Key → Copy it

### 2. Add key to app.py
```python
GEMINI_API_KEY = "AIzaSy_your_key_here"
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Run
```bash
python app.py
```

### 5. Open browser
→ **http://localhost:5000** (use Chrome for mic)

---

## 🎨 Robot Color States

| Color  | Meaning |
|--------|---------|
| 🟡 Yellow | Normal / Ready / Speaking |
| 🟢 Green  | Listening — mic is ON |
| 🟠 Orange | Thinking — waiting for Gemini |
| 🔴 Red    | Error occurred |

---

## 🎙️ How STT Works

1. Click the big **MIC** button in the Voice Input panel
2. The robot turns **GREEN** and shows "LISTENING"
3. Your words appear **LIVE in the transcript box** as you speak
4. When you stop talking, words auto-send to Gemini
5. Gemini replies → robot turns **YELLOW** and speaks the answer via TTS

---

## 🔧 PyAudio Installation Fix

### Windows
```bash
pip install pipwin
pipwin install pyaudio
```
OR download wheel from https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio

### Mac
```bash
brew install portaudio
pip install pyaudio
```

### Linux (Ubuntu/Debian)
```bash
sudo apt-get install portaudio19-dev python3-pyaudio
pip install pyaudio
```

---

## 🛠 Troubleshooting

| Problem | Fix |
|---|---|
| Mic says "not-allowed" | Chrome URL bar → 🔒 → Allow Microphone |
| No sound output | Check speaker volume; pyttsx3 uses system audio |
| API key error | Set GEMINI_API_KEY in app.py |
| PyAudio fails | See fix above for your OS |
| STT not working | Must use Chrome or Edge browser |
| "Server offline" | Make sure `python app.py` is running |

---

## 💡 Customise Voice Speed
In `app.py` → `_tts_worker()`:
```python
tts_engine.setProperty('rate', 162)   # 100=slow, 162=normal, 220=fast
tts_engine.setProperty('volume', 1.0) # 0.0 to 1.0
```
