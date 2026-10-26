import json
import os
import random
import sys
import time
from pathlib import Path
from flask import Flask, jsonify, render_template, request

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fallback.controller import DeterministicFallback
from models.baseline_ai import EdgeAIController
from models.poisoned_ai import CompromisedAIController
from watchdog.validator import HardwareWatchdog

TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
app = Flask(__name__, template_folder=str(TEMPLATE_DIR))

LOG_FILE_PATH = PROJECT_ROOT / "simulation_log.json"

# Simulation controllers for serverless / on-demand telemetry generation
baseline_ai = EdgeAIController()
ai_controller = CompromisedAIController()
watchdog = HardwareWatchdog()
fallback = DeterministicFallback()
telemetry_step = 0


@app.route("/")
def index():
    """Renders the EdgeGuard real-time telemetry dashboard."""
    return render_template("index.html")


@app.route("/api/data", methods=["GET", "POST"])
def get_data():
    """Returns telemetry data.

    Supports query parameters:
      - mode=safe: Forces correct AI commands (220V-240V, Watchdog passes).
      - mode=attack: Forces unsafe/poisoned AI commands (5000V spike, Watchdog shuts down AI & fails over).
      - mode=auto or omitted: Continuous stream from local log (if active) or auto simulation.
    """
    global telemetry_step

    mode = request.args.get("mode")
    if not mode and request.is_json and request.json:
        mode = request.json.get("mode")

    cwd_log = Path("simulation_log.json")
    target_path = cwd_log if cwd_log.exists() else LOG_FILE_PATH

    # If no explicit manual mode is requested and a local simulation engine is actively writing, use log
    if not mode or mode == "auto":
        if target_path.exists():
            try:
                mtime = os.path.getmtime(target_path)
                if time.time() - mtime < 4.0:
                    with open(target_path, "r", encoding="utf-8") as f:
                        log_entries = json.load(f)
                    if log_entries:
                        entry = dict(log_entries[-1])
                        entry["mode"] = "auto"
                        return jsonify(entry)
            except Exception:
                pass

    # Dynamic calculation for manual tests or serverless execution
    telemetry_step += 1
    grid_load = round(random.uniform(0.0, 1.0), 2)
    battery_temp = round(random.uniform(20.0, 60.0), 1)

    # 1. Determine raw AI voltage based on simulation mode
    if mode == "safe":
        # Guaranteed safe command within 220V - 240V
        ai_voltage = baseline_ai.predict_voltage(grid_load, battery_temp)
    elif mode == "attack":
        # Malicious adversarial spike simulating poisoned AI
        ai_voltage = 5000.0
    else:
        # Default auto simulation (85% safe, 15% attack)
        ai_voltage = ai_controller.predict_voltage(grid_load, battery_temp)

    # 2. Hardware watchdog safety validation
    is_safe, validated_voltage = watchdog.validate_output(ai_voltage)

    if is_safe:
        active_controller = "Primary AI"
        applied_voltage = validated_voltage
        failover_time = 0.0
    else:
        # Watchdog intercepted unsafe voltage: shut down AI command and switch to deterministic microcontroller
        start_ts = time.perf_counter()
        applied_voltage = fallback.get_safe_voltage()
        end_ts = time.perf_counter()
        failover_time = round((end_ts - start_ts) * 1000, 4)
        active_controller = "Deterministic Fallback"

    return jsonify({
        "iteration": telemetry_step,
        "mode": mode or "auto",
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
