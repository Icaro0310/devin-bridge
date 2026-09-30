#!/usr/bin/env python3
"""office-probe — probe magro do devin-office, corre na máquina local.

Recolhe o WorldState (sessions.db, jev_log.db, heartbeat) e faz POST para
o hub na VM apenas quando o estado muda. Pensado para ~20 MB de RAM.

Uso: python office/probe.py [--hub http://100.102.159.65:8790] [--interval 3]
Env: OFFICE_TOKEN — enviado como X-Office-Token se definido.
"""
import hashlib
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from daemon import collect_state  # noqa: E402

HUB = "http://100.102.159.65:8790"
INTERVAL = 3.0
TOKEN = os.environ.get("OFFICE_TOKEN", "")


def push(state: dict) -> bool:
    req = urllib.request.Request(
        f"{HUB}/api/ingest",
        data=json.dumps(state).encode(),
        headers={
            "Content-Type": "application/json",
            "X-Office-Token": TOKEN,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=4) as resp:
            return resp.status == 200
    except Exception:
        return False


def main() -> None:
    last_hash = ""
    failures = 0
    print(f"devin-office probe -> {HUB} every {INTERVAL}s")
    while True:
        try:
            state = collect_state()
            blob = json.dumps(state, sort_keys=True)
            h = hashlib.sha1(blob.encode()).hexdigest()
            if h != last_hash:
                if push(state):
                    last_hash = h
                    failures = 0
                else:
                    failures += 1
                    if failures in (1, 10, 60):
                        print(f"probe: hub unreachable ({failures} failures)", flush=True)
        except Exception as exc:
            print(f"probe: collect error: {exc}", flush=True)
        time.sleep(INTERVAL)


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--hub" in args:
        HUB = args[args.index("--hub") + 1].rstrip("/")
    if "--interval" in args:
        INTERVAL = float(args[args.index("--interval") + 1])
    main()
