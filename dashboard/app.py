import json
import os
import random
import sys
import time
from pathlib import Path
from flask import Flask, jsonify, render_template

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fallback.controller import DeterministicFallback
from models.poisoned_ai import CompromisedAIController
from watchdog.validator import HardwareWatchdog

TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
app = Flask(__name__, template_folder=str(TEMPLATE_DIR))

LOG_FILE_PATH = PROJECT_ROOT / "simulation_log.json"

# Simulation controllers for serverless / on-demand telemetry generation
ai_controller = CompromisedAIController()
watchdog = HardwareWatchdog()
fallback = DeterministicFallback()
telemetry_step = 0


@app.route("/")
def index():
    """Renders the EdgeGuard real-time telemetry dashboard."""
    return render_template("index.html")


@app.route("/api/data")
def get_data():
    """Returns telemetry data.

    If a fresh local simulation_log.json exists, reads from it;
    otherwise generates a real-time telemetry tick dynamically (for Vercel serverless).
    """
    global telemetry_step

    cwd_log = Path("simulation_log.json")
    target_path = cwd_log if cwd_log.exists() else LOG_FILE_PATH

    # Check if a live local simulation log is being actively updated
    if target_path.exists():
        try:
            mtime = os.path.getmtime(target_path)
            if time.time() - mtime < 4.0:
                with open(target_path, "r", encoding="utf-8") as f:
                    log_entries = json.load(f)
                if log_entries:
                    return jsonify(log_entries[-1])
        except Exception:
            pass

    # Dynamic real-time calculation for serverless deployment
    telemetry_step += 1
    grid_load = round(random.uniform(0.0, 1.0), 2)
    battery_temp = round(random.uniform(20.0, 60.0), 1)

    ai_voltage = ai_controller.predict_voltage(grid_load, battery_temp)
    is_safe, validated_voltage = watchdog.validate_output(ai_voltage)

    if is_safe:
        active_controller = "Primary AI"
        applied_voltage = validated_voltage
        failover_time = 0.0
    else:
        start_ts = time.perf_counter()
        applied_voltage = fallback.get_safe_voltage()
        end_ts = time.perf_counter()
        failover_time = round((end_ts - start_ts) * 1000, 4)
        active_controller = "Deterministic Fallback"

    return jsonify({
        "iteration": telemetry_step,
        "active_controller": active_controller,
        "applied_voltage": applied_voltage,
        "failover_time": failover_time,
        "failover_time_ms": failover_time,
        "grid_load": grid_load,
        "battery_temp": battery_temp,
        "raw_ai_voltage": ai_voltage,
        "watchdog_passed": is_safe,
        "timestamp": round(time.time(), 3),
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
