import json
import os
import random
import sys
import time
from pathlib import Path

# Ensure project root is in sys.path for direct execution
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from fallback.controller import DeterministicFallback
from models.poisoned_ai import CompromisedAIController
from watchdog.validator import HardwareWatchdog


def run_simulation(iterations: int = 50, sleep_interval: float = 0.5, log_path: str = "simulation_log.json"):
    """Runs the EdgeGuard edge computing simulation.

    Simulates an edge computing node processing grid load and battery temperature,
    detecting adversarial model poisoning attacks via a hardware watchdog,
    and failing over to a deterministic non-AI microcontroller.

    Args:
        iterations: Number of simulation iterations (default: 50).
        sleep_interval: Sleep duration between iterations in seconds (default: 0.5).
        log_path: Path to output JSON log file.

    Returns:
        list: Full telemetry history of the simulation.
    """
    ai_controller = CompromisedAIController()
    watchdog = HardwareWatchdog()
    fallback = DeterministicFallback()

    log_history = []
    abs_log_path = os.path.abspath(log_path)

    print(f"[*] Starting EdgeGuard simulation: {iterations} iterations...")

    for i in range(1, iterations + 1):
        # 1. Generate random edge telemetry
        grid_load = round(random.uniform(0.0, 1.0), 2)
        battery_temp = round(random.uniform(20.0, 60.0), 1)

        # 2. Query compromised Edge AI
        ai_voltage = ai_controller.predict_voltage(grid_load, battery_temp)

        # 3. Hardware watchdog validation
        is_safe, validated_voltage = watchdog.validate_output(ai_voltage)

        failover_time = 0.0
        if is_safe:
            active_controller = "Primary AI"
            applied_voltage = validated_voltage
        else:
            # Watchdog tripped: measure failover latency to deterministic fallback
            start_timestamp = time.perf_counter()
            applied_voltage = fallback.get_safe_voltage()
            end_timestamp = time.perf_counter()

            failover_time = round((end_timestamp - start_timestamp) * 1000, 4)
            active_controller = "Deterministic Fallback"
            print(
                f"[!] Iteration {i}: Compromise detected ({ai_voltage}V)! "
                f"Switched to {active_controller} -> {applied_voltage}V in {failover_time:.4f} ms"
            )

        status = {
            "iteration": i,
            "active_controller": active_controller,
            "applied_voltage": applied_voltage,
            "failover_time": failover_time,
            "failover_time_ms": failover_time,
            "grid_load": grid_load,
            "battery_temp": battery_temp,
            "raw_ai_voltage": ai_voltage,
            "watchdog_passed": is_safe,
            "timestamp": round(time.time(), 3),
        }

        log_history.append(status)

        # Incrementally persist simulation log for real-time monitoring
        with open(abs_log_path, "w", encoding="utf-8") as f:
            json.dump(log_history, f, indent=2)

        # Sleep between iterations if not the last loop
        if i < iterations:
            time.sleep(sleep_interval)

    print(f"[*] Simulation completed. Telemetry saved to {abs_log_path}")
    return log_history


if __name__ == "__main__":
    run_simulation()
