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
from models.poisoned_ai import CompromisedAIController
from watchdog.validator import HardwareWatchdog

app = Flask(__name__)

# State controllers for dynamic real-time telemetry simulation
ai_controller = CompromisedAIController()
watchdog = HardwareWatchdog()
fallback = DeterministicFallback()
telemetry_step = 0

HTML_PATH = PROJECT_ROOT / "public" / "index.html"
if not HTML_PATH.exists():
    HTML_PATH = PROJECT_ROOT / "dashboard" / "templates" / "index.html"


def generate_telemetry():
    global telemetry_step
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


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def handle_all(path):
    """Handles both index HTML rendering and telemetry JSON."""
    normalized = path.strip("/").lower()
    if normalized in ["", "index", "index.html"]:
        if HTML_PATH.exists():
            with open(HTML_PATH, "r", encoding="utf-8") as f:
                return f.read(), 200, {"Content-Type": "text/html; charset=utf-8"}
        return "<h1>EdgeGuard Dashboard</h1>", 200

    # For any /api/*, /api/data, /api/index, or /api/index.py
    return generate_telemetry()


if __name__ == "__main__":
    app.run(port=5000)
