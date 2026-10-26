import json
import os
import random
import sys
import time
from pathlib import Path
from flask import Flask, jsonify, request

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fallback.controller import DeterministicFallback
from models.baseline_ai import EdgeAIController
from models.poisoned_ai import CompromisedAIController
from watchdog.validator import HardwareWatchdog

app = Flask(__name__)

# State controllers for on-demand test execution
baseline_ai = EdgeAIController()
ai_controller = CompromisedAIController()
watchdog = HardwareWatchdog()
fallback = DeterministicFallback()
test_step = 0

HTML_PATH = PROJECT_ROOT / "public" / "index.html"
if not HTML_PATH.exists():
    HTML_PATH = PROJECT_ROOT / "dashboard" / "templates" / "index.html"


def generate_telemetry(force_mode=None, custom_voltage=None, custom_grid=None, custom_temp=None):
    global test_step

    has_test = (
        force_mode in ["safe", "attack", "ramp"]
        or custom_voltage is not None
        or (custom_grid is not None and str(custom_grid).strip() != "")
        or (custom_temp is not None and str(custom_temp).strip() != "")
    )

    # Standby / zero response if no test requested
    if not has_test or force_mode in ["standby", "reset"]:
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

    test_step += 1

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

    # 1. Determine raw AI command voltage
    if custom_voltage is not None and str(custom_voltage).strip() != "":
        try:
            ai_voltage = round(float(custom_voltage), 2)
            mode_name = "custom" if force_mode != "ramp" else "ramp"
        except (ValueError, TypeError):
            ai_voltage = round(random.uniform(220.0, 240.0), 2)
            mode_name = "safe"
    elif force_mode == "safe":
        ai_voltage = baseline_ai.predict_voltage(grid_load, battery_temp)
        mode_name = "safe"
    elif force_mode == "attack":
        ai_voltage = ai_controller.generate_unsafe_voltage()
        mode_name = "attack"
    elif force_mode == "ramp":
        ai_voltage = round(random.uniform(255.0, 275.0), 2)
        mode_name = "ramp"
    elif custom_grid is not None or custom_temp is not None:
        ai_voltage = baseline_ai.predict_voltage(grid_load, battery_temp)
        mode_name = "custom_telemetry"
    else:
        ai_voltage = round(random.uniform(220.0, 240.0), 2)
        mode_name = "safe"

    # 2. Hardware watchdog safety validation (200.0V - 250.0V window)
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
        "iteration": test_step,
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


@app.route("/", defaults={"path": ""}, methods=["GET", "POST"])
@app.route("/<path:path>", methods=["GET", "POST"])
def handle_all(path):
    """Handles index HTML rendering and on-demand test requests."""
    normalized = path.strip("/").lower()

    # Serve index HTML if root requested
    if normalized in ["", "index", "index.html"]:
        if HTML_PATH.exists():
            with open(HTML_PATH, "r", encoding="utf-8") as f:
                return f.read(), 200, {"Content-Type": "text/html; charset=utf-8"}
        return "<h1>EdgeGuard Dashboard</h1>", 200

    # Extract test parameters (support GET query params and JSON payload)
    json_data = request.json if request.is_json and request.json else {}
    mode = request.args.get("mode", json_data.get("mode"))
    voltage = request.args.get("voltage", json_data.get("voltage"))
    grid_load = request.args.get("grid_load", json_data.get("grid_load"))
    battery_temp = request.args.get("battery_temp", json_data.get("battery_temp"))

    return generate_telemetry(
        force_mode=mode,
        custom_voltage=voltage,
        custom_grid=grid_load,
        custom_temp=battery_temp,
    )


if __name__ == "__main__":
    app.run(port=5000)
