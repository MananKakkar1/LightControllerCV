import cv2 as cv
import time
import math
import subprocess
import sys
from pathlib import Path
from HandTrackerModule import HandTracker
import os

# Load config from .env (repo root) and environment variables
def _load_env() -> dict:
    env = {}
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    for k in ("BULB_IP", "BIND_IP", "CLOSE_NORM", "OPEN_NORM", "COOLDOWN_S"):
        if k in os.environ:
            env[k] = os.environ[k]
    return env


_ENV = _load_env()
BULB_IP = _ENV.get("BULB_IP")
BIND_IP = _ENV.get("BIND_IP") or None

def _f(k: str, default: float) -> float:
    try:
        return float(_ENV.get(k, default))
    except Exception:
        return default

# Pinch thresholds (normalized by hand scale)
CLOSE_NORM = _f("CLOSE_NORM", 0.55)  # pinch when <= this
OPEN_NORM = _f("OPEN_NORM", 0.85)    # re-arm when >= this
COOLDOWN_S = _f("COOLDOWN_S", 0.5)   # min seconds between toggles


def _wiz_path() -> str:
    return str((Path(__file__).resolve().parents[1] / "scripts" / "wiz_control.py"))


def toggle_light(light_on: bool) -> bool:
    action = "--off" if light_on else "--on"
    cmd = [sys.executable, _wiz_path(), "--ip", BULB_IP, action]
    if BIND_IP:
        cmd += ["--bind", BIND_IP]
    subprocess.run(cmd, check=False)
    return not light_on


def main():
    tracker = HandTracker(detectionCon=0.6)
    video = cv.VideoCapture(0)
    video.set(cv.CAP_PROP_FRAME_WIDTH, 640)
    video.set(cv.CAP_PROP_FRAME_HEIGHT, 480)

    light_on = False
    pinched = False
    last_toggle = 0.0
    pTime = 0.0

    while True:
        ok, img = video.read()
        if not ok:
            break

        tracker.findHands(img, draw=False)
        lmList = tracker.findPosition(img, draw=False)
        if lmList:
            # Thumb tip (4) and Index tip (8)
            x1, y1 = lmList[4][1], lmList[4][2]
            x2, y2 = lmList[8][1], lmList[8][2]
            # Hand scale ref across palm: 17 ↔ 5 (pinky base to index base)
            ref = math.hypot(lmList[17][1] - lmList[5][1], lmList[17][2] - lmList[5][2])
            pinch = math.hypot(x2 - x1, y2 - y1) / max(ref, 1e-6)

            # Draw
            cv.circle(img, (x1, y1), 10, (255, 0, 255), cv.FILLED)
            cv.circle(img, (x2, y2), 10, (255, 0, 255), cv.FILLED)
            cv.line(img, (x1, y1), (x2, y2), (200, 0, 200), 2)
            cv.putText(img, f"pinch={pinch:.2f}", (10, 100), cv.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)

            # Simple hysteresis state machine
            now = time.time()
            if not pinched and pinch <= CLOSE_NORM:
                pinched = True
                if now - last_toggle >= COOLDOWN_S:
                    light_on = toggle_light(light_on)
                    last_toggle = now
                    cv.putText(img, "Toggled", (10, 140), cv.FONT_HERSHEY_SIMPLEX, 1.0, (0, 200, 0), 2)
            elif pinched and pinch >= OPEN_NORM:
                pinched = False

        # FPS + view
        cTime = time.time()
        fps = 1.0 / max(1e-6, (cTime - pTime))
        pTime = cTime
        cv.putText(img, f"{fps:.1f}", (10, 70), cv.FONT_HERSHEY_COMPLEX, 2, (0, 0, 255), 2)
        cv.imshow('Video', img)
        if cv.waitKey(1) & 0xFF == ord('q'):
            break


if __name__ == "__main__":
    main()
