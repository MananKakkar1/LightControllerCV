#!/usr/bin/env python
"""
Simple WiZ control CLI using raw UDP.

Examples:
  # Query state
  python scripts/wiz_control.py --ip 192.168.1.123 --get --json

  # On / Off
  python scripts/wiz_control.py --ip 192.168.1.123 --on
  python scripts/wiz_control.py --ip 192.168.1.123 --off

  # Brightness (10-100)
  python scripts/wiz_control.py --ip 192.168.1.123 --brightness 60

  # White color temp (Kelvin)
  python scripts/wiz_control.py --ip 192.168.1.123 --temp 3000

  # RGB
  python scripts/wiz_control.py --ip 192.168.1.123 --rgb 255 120 60

  # Scene
  python scripts/wiz_control.py --ip 192.168.1.123 --scene 2
"""

import argparse
import json
import socket
from typing import Optional, Dict, Any


def send_udp(ip: str, payload: Dict[str, Any], *, port: int, timeout: float, bind: Optional[str]) -> Optional[Dict[str, Any]]:
    data = json.dumps(payload).encode()
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.settimeout(timeout)
        if bind:
            try:
                s.bind((bind, 0))
            except Exception:
                pass
        try:
            s.sendto(data, (ip, port))
            buf, _ = s.recvfrom(8192)
            return json.loads(buf.decode(errors="ignore"))
        except Exception:
            return None


def build_payload(args: argparse.Namespace) -> Dict[str, Any]:
    if args.get:
        return {"method": "getPilot", "params": {}}

    params: Dict[str, Any] = {}

    if args.on and args.off:
        raise SystemExit("Cannot specify both --on and --off")
    if args.on:
        params["state"] = True
    if args.off:
        params["state"] = False

    if args.brightness is not None:
        if not (0 <= args.brightness <= 100):
            raise SystemExit("--brightness must be 0..100")
        params["dimming"] = int(args.brightness)
        params.setdefault("state", True)

    if args.temp is not None:
        # Typical Kelvin range: 2200..6500, but pass-through to device
        params["temp"] = int(args.temp)
        params.setdefault("state", True)

    if args.rgb is not None:
        r, g, b = args.rgb
        for v in (r, g, b):
            if not (0 <= v <= 255):
                raise SystemExit("--rgb values must be 0..255")
        params.update({"r": r, "g": g, "b": b})
        params.setdefault("state", True)

    if args.scene is not None:
        params["sceneId"] = int(args.scene)

    if not params:
        raise SystemExit("No action specified. Use --get or one of --on/--off/--brightness/--temp/--rgb/--scene")

    return {"method": "setPilot", "params": params}


def main():
    ap = argparse.ArgumentParser(description="Control a WiZ bulb via UDP")
    ap.add_argument("--ip", required=True, help="Bulb IPv4")
    ap.add_argument("--port", type=int, default=38899, help="UDP port (default 38899)")
    ap.add_argument("--timeout", type=float, default=2.0, help="Socket timeout seconds")
    ap.add_argument("--bind", help="Bind to local IPv4 (interface) before sending")
    ap.add_argument("--json", action="store_true", help="Print response as JSON")

    # Actions
    ap.add_argument("--get", action="store_true", help="Query current state (getPilot)")
    ap.add_argument("--on", action="store_true", help="Turn on")
    ap.add_argument("--off", action="store_true", help="Turn off")
    ap.add_argument("--brightness", type=int, help="Brightness 0..100")
    ap.add_argument("--temp", type=int, help="White color temperature (Kelvin)")
    ap.add_argument("--rgb", nargs=3, type=int, metavar=("R","G","B"), help="RGB values 0..255")
    ap.add_argument("--scene", type=int, help="Scene ID")

    args = ap.parse_args()

    payload = build_payload(args)
    resp = send_udp(args.ip, payload, port=args.port, timeout=args.timeout, bind=args.bind)

    if resp is None:
        print("(no response)")
        return

    if args.json:
        print(json.dumps(resp, indent=2))
    else:
        # Friendly summary for common actions
        if args.get:
            try:
                result = resp.get("result") or resp.get("params") or {}
                on = result.get("state")
                dim = result.get("dimming")
                cct = result.get("cct")
                rgb = tuple(result.get(k) for k in ("r","g","b")) if all(k in result for k in ("r","g","b")) else None
                print(f"Power: {'ON' if on else 'OFF'}")
                if dim is not None:
                    print(f"Brightness: {dim}")
                if cct is not None:
                    print(f"Color Temp: {cct}")
                if rgb is not None:
                    print(f"RGB: {rgb}")
            except Exception:
                print(json.dumps(resp))
        else:
            status = resp.get("result") or resp.get("success") or resp
            print(json.dumps(status))


if __name__ == "__main__":
    main()

