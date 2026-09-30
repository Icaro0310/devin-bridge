"""devin-office local agent — mantém o túnel SSH e o probe vivos.

Corre com pythonw (sem janela). Se um processo morre, re-spawna.
Registado no Task Scheduler como 'DevinOffice-Agent' (ONLOGON).
Log: office/up.log
"""
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LOG = ROOT / "up.log"
CREATE_NO_WINDOW = 0x08000000

JOBS = {
    "tunnel": [
        "ssh", "-N", "-o", "BatchMode=yes",
        "-o", "ServerAliveInterval=30", "-o", "ServerAliveCountMax=3",
        "-o", "ExitOnForwardFailure=yes",
        "-L", "8790:127.0.0.1:8790", "devin-vm",
    ],
    "probe": [sys.executable, str(ROOT / "probe.py"), "--interval", "3"],
}


def log(msg: str) -> None:
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}\n")
    except OSError:
        pass


def spawn(name: str) -> subprocess.Popen:
    p = subprocess.Popen(
        JOBS[name],
        creationflags=CREATE_NO_WINDOW,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        cwd=str(ROOT.parent),
    )
    log(f"START {name} pid={p.pid}")
    return p


def main() -> None:
    procs = {name: spawn(name) for name in JOBS}
    log("devin-office agent up")
    while True:
        time.sleep(5)
        for name, p in list(procs.items()):
            if p.poll() is not None:
                log(f"DIED {name} rc={p.returncode} — respawning")
                procs[name] = spawn(name)


if __name__ == "__main__":
    main()
