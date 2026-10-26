import atexit
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
DASHBOARD_SCRIPT = ROOT_DIR / "dashboard" / "app.py"
ENGINE_SCRIPT = ROOT_DIR / "core" / "engine.py"
PYTHON_EXE = sys.executable


def main():
    """Simultaneously launches EdgeGuard simulation engine and dashboard."""
    processes = {}

    def cleanup(*args):
        """Terminates all child processes and process trees cleanly."""
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
    print("=" * 60)

    try:
        # 1. Launch Dashboard Web UI
        print(f"[*] Starting Telemetry Dashboard on http://127.0.0.1:5000 ...")
        dashboard_proc = subprocess.Popen(
            [PYTHON_EXE, str(DASHBOARD_SCRIPT)],
            cwd=str(ROOT_DIR),
        )
        processes["Dashboard UI"] = dashboard_proc
        print(f"[+] Dashboard process spawned (PID: {dashboard_proc.pid})")

        # Brief pause to allow Flask server to initialize
        time.sleep(1.2)

        # 2. Launch Simulation Engine
        print(f"[*] Starting Edge Simulation Engine...")
        engine_proc = subprocess.Popen(
            [PYTHON_EXE, str(ENGINE_SCRIPT)],
            cwd=str(ROOT_DIR),
        )
        processes["Simulation Engine"] = engine_proc
        print(f"[+] Engine process spawned (PID: {engine_proc.pid})")
        print("[*] Both services are running. Press Ctrl+C to stop.")

        # Keep parent script alive while child processes run
        while True:
            # Check if dashboard died unexpectedly
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
