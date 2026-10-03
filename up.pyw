"""devin-office local agent — mantém o túnel SSH e o probe vivos.

Corre com pythonw (sem janela). Se um processo morre, re-spawna.
Registado no Task Scheduler como 'DevinOffice-Agent' (ONLOGON).
Log: office/up.log
"""
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LOG = ROOT / "up.log"
CREATE_NO_WINDOW = 0x08000000
SSH_HOST = os.environ.get("OFFICE_SSH_HOST", "")
OFFICE_PORT = int(os.environ.get("OFFICE_PORT", "8790"))
EXPLICIT_HUB = os.environ.get("OFFICE_HUB", "")
OFFICE_HUB = EXPLICIT_HUB or (
    f"http://127.0.0.1:{OFFICE_PORT}" if SSH_HOST else ""
)
CONTROL_ENABLED = os.environ.get("OFFICE_CONTROL_ENABLED", "").lower() in {
    "1", "true", "yes", "on"
}

JOBS = {}
if SSH_HOST and not EXPLICIT_HUB:
    JOBS["tunnel"] = [
        "ssh", "-N", "-o", "BatchMode=yes",
        "-o", "ServerAliveInterval=30", "-o", "ServerAliveCountMax=3",
        "-o", "ExitOnForwardFailure=yes",
        "-L", f"{OFFICE_PORT}:127.0.0.1:{OFFICE_PORT}", SSH_HOST,
    ]
if OFFICE_HUB:
    JOBS["probe"] = [sys.executable, str(ROOT / "probe.py"), "--hub", OFFICE_HUB, "--interval", "3"]
# executor ACP: o probe também o lança sob demanda; a guarda de instância
# única (state/executor.pid) evita duplicados.
if CONTROL_ENABLED:
    JOBS["executor"] = [sys.executable, str(ROOT / "executor.py")]


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
    if not OFFICE_HUB:
        raise SystemExit("Set OFFICE_HUB or OFFICE_SSH_HOST before starting the split-mode agent")
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
