import atexit
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
DASHBOARD_SCRIPT = ROOT_DIR / "dashboard" / "app.py"
PYTHON_EXE = sys.executable


def main():
    """Launches the EdgeGuard testing dashboard web UI."""
    processes = {}

    def cleanup(*args):
        """Terminates all child processes cleanly."""
        print("\n[*] Shutting down EdgeGuard services...")
        for name, proc in list(processes.items()):
            if proc.poll() is None:
                print(f"[-] Terminating {name} (PID: {proc.pid})...")
                if sys.platform == "win32":
                    subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                else:
                    proc.terminate()
                    try:
                        proc.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        proc.kill()
        print("[✓] All processes terminated cleanly.")

    # Register exit handlers for graceful termination
    atexit.register(cleanup)
    signal.signal(signal.SIGINT, lambda sig, frame: sys.exit(0))
    signal.signal(signal.SIGTERM, lambda sig, frame: sys.exit(0))

    print("=" * 60)
    print("  EdgeGuard: Edge AI Resilience & Failover Framework  ")
    print("  Mode: On-Demand Test Mode (Autostream Disabled)     ")
    print("=" * 60)

    try:
        # Launch Dashboard Web UI
        print(f"[*] Starting Telemetry Dashboard on http://127.0.0.1:5000 ...")
        dashboard_proc = subprocess.Popen(
            [PYTHON_EXE, str(DASHBOARD_SCRIPT)],
            cwd=str(ROOT_DIR),
        )
        processes["Dashboard UI"] = dashboard_proc
        print(f"[+] Dashboard process spawned (PID: {dashboard_proc.pid})")
        print("[*] Ready. Telemetry values initialize to zero until tested.")
        print("[*] Press Ctrl+C to stop.")

        # Keep parent script alive while dashboard runs
        while True:
            if dashboard_proc.poll() is not None:
                print(f"[!] Dashboard exited with code {dashboard_proc.returncode}")
                break
            time.sleep(0.5)

    except KeyboardInterrupt:
        pass
    finally:
        cleanup()


if __name__ == "__main__":
    main()
