# LightControllerCV

Simple tools to discover and control WiZ bulbs, plus a minimal pinch gesture controller that toggles your room light.

## Setup

- Optional venv:
  - `python -m venv .venv`
  - `.\\.venv\\Scripts\\Activate.ps1`
- Install packages you need:
  - WiZ control: `python -m pip install pywizlight`
  - CV pinch control: `python -m pip install opencv-python mediapipe`

## Configure

- Create `.env` in the repo root (or edit the existing one):
  - `BULB_IP=192.168.1.123`
  - `BIND_IP=192.168.1.34` (optional; only if you needed binding earlier)
  - Pinch tuning (optional): `CLOSE_NORM=0.55`, `OPEN_NORM=0.85`, `COOLDOWN_S=0.5`

## Commands

- Control bulb (raw CLI):
  - `python scripts\\wiz_control.py --ip YOUR_BULB_IP --on` (or `--off`)
  - `python scripts\\wiz_control.py --ip YOUR_BULB_IP --brightness 60`
  - `python scripts\\wiz_control.py --ip YOUR_BULB_IP --temp 3000`
  - `python scripts\\wiz_control.py --ip YOUR_BULB_IP --rgb 255 120 60`

## Pinch Control

- Run the minimal pinch controller (reads `.env`):
  - `python src\\LightControlCV.py`
- Gesture: pinch thumb+index to toggle, open to re‑arm.
- Tuning via `.env`: `CLOSE_NORM`, `OPEN_NORM`, `COOLDOWN_S`.

## Notes

- Get the bulb IP from the WiZ app (device details) or your router’s client list, then put it in `.env`.
- Ensure your PC and bulbs are on the same network.
- Avoid sending rapid repeated commands; some firmware rate‑limits.
