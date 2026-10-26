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

# On-demand simulation controllers
baseline_ai = EdgeAIController()
ai_controller = CompromisedAIController()
watchdog = HardwareWatchdog()
fallback = DeterministicFallback()
test_iteration = 0


@app.route("/")
def index():
    """Renders the EdgeGuard testing dashboard."""
    return render_template("index.html")


@app.route("/api/data", methods=["GET", "POST"])
def get_data():
    """Returns telemetry data strictly on-demand.

    When no test parameters are supplied (or mode='standby'/'reset'),
    all values return zero/standby.
    """
    global test_iteration

    json_data = request.json if request.is_json and request.json else {}
    mode = request.args.get("mode", json_data.get("mode"))
    custom_voltage = request.args.get("voltage", json_data.get("voltage"))
    custom_grid = request.args.get("grid_load", json_data.get("grid_load"))
    custom_temp = request.args.get("battery_temp", json_data.get("battery_temp"))

    has_test = (
        mode in ["safe", "attack"]
        or custom_voltage is not None
        or (custom_grid is not None and str(custom_grid).strip() != "")
        or (custom_temp is not None and str(custom_temp).strip() != "")
    )

    # If no test action requested or reset, return zero state
    if not has_test or mode in ["standby", "reset"]:
        return jsonify({
            "iteration": 0,
            "mode": "standby",
            "active_controller": "Standby",
            "applied_voltage": 0.0,
            "raw_ai_voltage": 0.0,
            "attack_voltage": None,
            "fallback_voltage": None,
            "failover_time": 0.0,
            "failover_time_ms": 0.0,
            "grid_load": 0.0,
            "battery_temp": 0.0,
            "watchdog_passed": None,
            "timestamp": round(time.time(), 3),
        })

    # Execute on-demand test iteration
    test_iteration += 1

    if custom_grid is not None and str(custom_grid).strip() != "":
        try:
            grid_load = round(float(custom_grid), 2)
        except (ValueError, TypeError):
            grid_load = round(random.uniform(0.3, 0.9), 2)
    else:
        grid_load = round(random.uniform(0.3, 0.9), 2)

    if custom_temp is not None and str(custom_temp).strip() != "":
        try:
            battery_temp = round(float(custom_temp), 1)
        except (ValueError, TypeError):
            battery_temp = round(random.uniform(25.0, 50.0), 1)
    else:
        battery_temp = round(random.uniform(25.0, 50.0), 1)

    # 1. Determine raw AI voltage
    if custom_voltage is not None and str(custom_voltage).strip() != "":
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
        ai_voltage = round(random.uniform(220.0, 240.0), 2)
        mode_name = "safe"

    # 2. Hardware watchdog safety validation (200.0V - 250.0V)
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
        "iteration": test_iteration,
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
    app.run(port=5000)
