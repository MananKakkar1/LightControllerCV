import cv2 as cv
import time
import math
import subprocess
import sys
from pathlib import Path
from HandTrackerModule import HandTracker
import os


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
    # Allow overriding via real environment
    for k in (
        "BULB_IP",
        "BULB_LEFT_IP",
        "BULB_RIGHT_IP",
        "BULB1_IP",
        "BULB2_IP",
        "BIND_IP",
        "CLOSE_NORM",
        "OPEN_NORM",
        "COOLDOWN_S",
    ):
        if k in os.environ:
            env[k] = os.environ[k]
    return env


_ENV = _load_env()

# Legacy single-bulb var
BULB_IP = _ENV.get("BULB_IP")

# New: per-hand bulbs. Prefer explicit LEFT/RIGHT, fall back to BULB1/BULB2, then legacy BULB_IP
BULB_LEFT_IP = _ENV.get("BULB_LEFT_IP") or _ENV.get("BULB1_IP") or BULB_IP
BULB_RIGHT_IP = _ENV.get("BULB_RIGHT_IP") or _ENV.get("BULB2_IP") or BULB_IP

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


def toggle_light_for_ip(ip: str, light_on: bool) -> bool:
    if not ip:
        return light_on
    action = "--off" if light_on else "--on"
    cmd = [sys.executable, _wiz_path(), "--ip", ip, action]
    if BIND_IP:
        cmd += ["--bind", BIND_IP]
    subprocess.run(cmd, check=False)
    return not light_on


def main():
    tracker = HandTracker(detectionCon=0.6)
    video = cv.VideoCapture(0)
    video.set(cv.CAP_PROP_FRAME_WIDTH, 640)
    video.set(cv.CAP_PROP_FRAME_HEIGHT, 480)

    # Per-hand states
    states = {
        "Left": {"light_on": False, "pinched": False, "last_toggle": 0.0, "ip": BULB_LEFT_IP},
        "Right": {"light_on": False, "pinched": False, "last_toggle": 0.0, "ip": BULB_RIGHT_IP},
    }

    pTime = 0.0

    while True:
        ok, img = video.read()
        if not ok:
            break

        tracker.findHands(img, draw=False)

        # Prefer multi-hand info with handedness
        info = tracker.hands_info(img, draw=False)
        hands_used = 0
        if info:
            for hand in info:
                label = hand.get("label") or ("Left" if hands_used == 0 else "Right")
                hands_used += 1
                lm = hand.get("lm") or []
                if len(lm) < 21:
                    continue

                x1, y1 = lm[4]
                x2, y2 = lm[8]
                # palm width reference (pinky base to index base)
                px, py = lm[17]
                qx, qy = lm[5]
                ref = math.hypot(px - qx, py - qy)
                pinch = math.hypot(x2 - x1, y2 - y1) / max(ref, 1e-6)

                # Draw per-hand overlay
                color = (255, 0, 255) if label == "Left" else (0, 200, 255)
                cv.circle(img, (x1, y1), 10, color, cv.FILLED)
                cv.circle(img, (x2, y2), 10, color, cv.FILLED)
                cv.line(img, (x1, y1), (x2, y2), color, 2)
                cv.putText(
                    img,
                    f"{label} pinch={pinch:.2f}",
                    (10, 100 if label == "Left" else 130),
                    cv.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (255, 255, 0),
                    2,
                )

                # State machine per hand
                s = states.get(label) or {"light_on": False, "pinched": False, "last_toggle": 0.0, "ip": BULB_IP}
                now = time.time()
                if not s["pinched"] and pinch <= CLOSE_NORM:
                    s["pinched"] = True
                    if now - s["last_toggle"] >= COOLDOWN_S:
                        s["light_on"] = toggle_light_for_ip(s["ip"], s["light_on"])
                        s["last_toggle"] = now
                        cv.putText(
                            img,
                            f"{label} toggled",
                            (10, 160 if label == "Left" else 190),
                            cv.FONT_HERSHEY_SIMPLEX,
                            0.8,
                            (0, 200, 0),
                            2,
                        )
                elif s["pinched"] and pinch >= OPEN_NORM:
                    s["pinched"] = False
                states[label] = s
        else:
            # Fallback to single-hand list-based logic (legacy)
            lm_list = tracker.findPosition(img, draw=False)
            if lm_list:
                x1, y1 = lm_list[4][1], lm_list[4][2]
                x2, y2 = lm_list[8][1], lm_list[8][2]
                ref = math.hypot(lm_list[17][1] - lm_list[5][1], lm_list[17][2] - lm_list[5][2])
                pinch = math.hypot(x2 - x1, y2 - y1) / max(ref, 1e-6)

                cv.circle(img, (x1, y1), 10, (255, 0, 255), cv.FILLED)
                cv.circle(img, (x2, y2), 10, (255, 0, 255), cv.FILLED)
                cv.line(img, (x1, y1), (x2, y2), (200, 0, 200), 2)
                cv.putText(img, f"pinch={pinch:.2f}", (10, 100), cv.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)

                s = states["Left"]  # use left as default
                now = time.time()
                if not s["pinched"] and pinch <= CLOSE_NORM:
                    s["pinched"] = True
                    if now - s["last_toggle"] >= COOLDOWN_S:
                        s["light_on"] = toggle_light_for_ip(s["ip"], s["light_on"])
                        s["last_toggle"] = now
                        cv.putText(img, "Toggled", (10, 160), cv.FONT_HERSHEY_SIMPLEX, 0.8, (0, 200, 0), 2)
                elif s["pinched"] and pinch >= OPEN_NORM:
                    s["pinched"] = False
                states["Left"] = s

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

