import json
import os
from pathlib import Path
from flask import Flask, jsonify, render_template

app = Flask(__name__)

# Locate simulation_log.json at project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOG_FILE_PATH = PROJECT_ROOT / "simulation_log.json"


@app.route("/")
def index():
    """Renders the EdgeGuard real-time telemetry dashboard."""
    return render_template("index.html")


@app.route("/api/data")
def get_data():
    """Reads simulation_log.json and returns the latest telemetry entry as JSON."""
    if not LOG_FILE_PATH.exists():
        # Fallback check in current working directory
        cwd_log = Path("simulation_log.json")
        target_path = cwd_log if cwd_log.exists() else LOG_FILE_PATH
    else:
        target_path = LOG_FILE_PATH

    if not target_path.exists():
        return jsonify({
            "error": "Simulation log not found",
            "message": "Run core/engine.py to start generating simulation data."
        }), 404

    try:
        with open(target_path, "r", encoding="utf-8") as f:
            log_entries = json.load(f)

        if not log_entries:
            return jsonify({}), 200

        # Return latest entry
        latest = log_entries[-1]
        return jsonify(latest)
    except Exception as e:
        return jsonify({"error": f"Failed to read simulation log: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
