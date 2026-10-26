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

    Supports custom data parameters:
      - voltage: Injects a specific voltage (e.g. 230, 260, 500, 180).
      - grid_load: Grid load level (0.0 to 1.0).
      - battery_temp: Battery temperature in °C (20.0 to 60.0).
      - mode: 'safe' | 'attack' | 'auto'.
    """
    global telemetry_step

    json_data = request.json if request.is_json and request.json else {}
    mode = request.args.get("mode", json_data.get("mode"))
    custom_voltage = request.args.get("voltage", json_data.get("voltage"))
    custom_grid = request.args.get("grid_load", json_data.get("grid_load"))
    custom_temp = request.args.get("battery_temp", json_data.get("battery_temp"))

    cwd_log = Path("simulation_log.json")
    target_path = cwd_log if cwd_log.exists() else LOG_FILE_PATH

    has_custom = custom_voltage is not None or custom_grid is not None or custom_temp is not None or mode in ["safe", "attack"]

    # If no explicit manual test data is requested and local engine log is fresh, use log
    if not has_custom:
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

    # Dynamic calculation for custom test data
    telemetry_step += 1

    if custom_grid is not None:
        try:
            grid_load = round(float(custom_grid), 2)
        except (ValueError, TypeError):
            grid_load = round(random.uniform(0.0, 1.0), 2)
    else:
        grid_load = round(random.uniform(0.0, 1.0), 2)

    if custom_temp is not None:
        try:
            battery_temp = round(float(custom_temp), 1)
        except (ValueError, TypeError):
            battery_temp = round(random.uniform(20.0, 60.0), 1)
    else:
        battery_temp = round(random.uniform(20.0, 60.0), 1)

    # 1. Determine raw AI voltage
    if custom_voltage is not None:
        try:
            ai_voltage = round(float(custom_voltage), 2)
            mode_name = "custom"
        except (ValueError, TypeError):
            ai_voltage = round(random.uniform(220.0, 240.0), 2)
            mode_name = "safe"
    elif mode == "safe":
        ai_voltage = baseline_ai.predict_voltage(grid_load, battery_temp)
        mode_name = "safe"
    elif mode == "attack":
        ai_voltage = ai_controller.generate_unsafe_voltage()
        mode_name = "attack"
    elif custom_grid is not None or custom_temp is not None:
        ai_voltage = baseline_ai.predict_voltage(grid_load, battery_temp)
        mode_name = "custom_telemetry"
    else:
        ai_voltage = ai_controller.predict_voltage(grid_load, battery_temp)
        mode_name = "auto"

    # 2. Hardware watchdog safety validation
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
        "mode": mode_name,
        "active_controller": active_controller,
        "applied_voltage": applied_voltage,
        "raw_ai_voltage": ai_voltage,
        "attack_voltage": ai_voltage if not is_safe else None,
        "fallback_voltage": fallback.get_safe_voltage() if not is_safe else None,
        "failover_time": failover_time,
        "failover_time_ms": failover_time,
        "grid_load": grid_load,
        "battery_temp": battery_temp,
        "watchdog_passed": is_safe,
        "timestamp": round(time.time(), 3),
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
