# 🎮 Gesture Space Shooter

A real-time **2D Space Shooter** controlled entirely by **hand gestures** via your webcam, built with Python, MediaPipe, and Pygame.

---

## ✋ Gesture Controls

| Gesture | Action |
|---|---|
| 🖐 Open Palm | Move ship left/right (wrist tracks X) |
| ✊ Fist | Shoot bullets (hold to rapid-fire) |
| ✌ Peace Sign | Activate Shield (3-second protection) |
| 🤌 Pinch | Mega Blast (8-second cooldown) |
| 👍 Thumbs Up | Pause / Resume |

> **Keyboard fallback** (if no webcam): `← →` to move, `SPACE` to shoot, `P` to pause, `ESC` to quit.

---

## 🛠 Installation

### Requirements
- Python **3.9+** ([python.org](https://python.org))
- A working **webcam** (optional but recommended)

### Step 1 – Install dependencies
Double-click `install.bat` or run in terminal:
```
install.bat
```
This creates a virtual environment and installs:
- `mediapipe` – Hand landmark detection
- `opencv-python` – Webcam capture
- `pygame` – Game rendering
- `numpy` – Numerical operations

### Step 2 – Run the game
```
run.bat
```
Or manually:
```
venv\Scripts\python game.py
```

---

## 🚀 Gameplay

- **Waves** increase in difficulty; every 5th wave has a **Boss fight**
- Kill enemies to earn points and **combo multipliers** (up to x8)
- Collect **power-ups** dropped by enemies:
  - 💚 **Health** – restore 1 life
  - 🔵 **Shield** – instant shield
  - 💜 **Mega** – instant Mega Blast recharge
- Survive all **10 waves** to WIN!

---

## 📁 File Structure
```
gaming/
├── game.py            ← Main entry point
├── gesture_engine.py  ← MediaPipe hand tracking + gesture classifier
├── entities.py        ← Player, enemies, bullets, power-ups
├── particles.py       ← Visual effects (explosions, stars, nebula)
├── hud.py             ← HUD, menus, overlays
├── requirements.txt
├── install.bat
└── run.bat
```

---

## 🧯 Troubleshooting

| Issue | Fix |
|---|---|
| Camera not detected | Game falls back to keyboard. Check webcam permissions |
| `mediapipe` install fails | Ensure Python ≥ 3.9 and pip is up to date |
| Low FPS | Close other apps; reduce `count` in `StarField` constructor |
| Gesture not responding | Ensure good lighting; keep hand clearly in frame |
