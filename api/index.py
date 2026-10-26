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

# State controllers for dynamic real-time telemetry simulation
baseline_ai = EdgeAIController()
ai_controller = CompromisedAIController()
watchdog = HardwareWatchdog()
fallback = DeterministicFallback()
telemetry_step = 0

HTML_PATH = PROJECT_ROOT / "public" / "index.html"
if not HTML_PATH.exists():
    HTML_PATH = PROJECT_ROOT / "dashboard" / "templates" / "index.html"


def generate_telemetry(force_mode=None):
    global telemetry_step
    telemetry_step += 1

    grid_load = round(random.uniform(0.0, 1.0), 2)
    battery_temp = round(random.uniform(20.0, 60.0), 1)

    # 1. Determine raw AI command voltage based on mode
    if force_mode == "safe":
        # Guaranteed safe command within 220V - 240V
        ai_voltage = baseline_ai.predict_voltage(grid_load, battery_temp)
    elif force_mode == "attack":
        # Adversarial poisoned AI command (5000V spike)
        ai_voltage = 5000.0
    else:
        # Auto simulation (85% safe, 15% attack)
        ai_voltage = ai_controller.predict_voltage(grid_load, battery_temp)

    # 2. Hardware watchdog safety validation
    is_safe, validated_voltage = watchdog.validate_output(ai_voltage)

    if is_safe:
        active_controller = "Primary AI"
        applied_voltage = validated_voltage
        failover_time = 0.0
    else:
        # Watchdog intercepted unsafe command: shut down AI and failover to deterministic microcontroller
        start_ts = time.perf_counter()
        applied_voltage = fallback.get_safe_voltage()
        end_ts = time.perf_counter()
        failover_time = round((end_ts - start_ts) * 1000, 4)
        active_controller = "Deterministic Fallback"

    return jsonify({
        "iteration": telemetry_step,
        "mode": force_mode or "auto",
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


@app.route("/", defaults={"path": ""}, methods=["GET", "POST"])
@app.route("/<path:path>", methods=["GET", "POST"])
def handle_all(path):
    """Handles index HTML rendering, API telemetry, and interactive simulation tests."""
    normalized = path.strip("/").lower()

    # Serve index HTML if requested
    if normalized in ["", "index", "index.html"]:
        if HTML_PATH.exists():
            with open(HTML_PATH, "r", encoding="utf-8") as f:
                return f.read(), 200, {"Content-Type": "text/html; charset=utf-8"}
        return "<h1>EdgeGuard Dashboard</h1>", 200

    # Extract simulation mode parameter (e.g., ?mode=safe or ?mode=attack)
    mode = request.args.get("mode")
    if not mode and request.is_json and request.json:
        mode = request.json.get("mode")

    return generate_telemetry(force_mode=mode)


if __name__ == "__main__":
    app.run(port=5000)
