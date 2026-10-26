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


def run_simulation(iterations: int = 0, sleep_interval: float = 0.5, log_path: str = "simulation_log.json", continuous: bool = True):
    """Runs the EdgeGuard edge computing simulation.

    Simulates an edge computing node processing grid load and battery temperature,
    detecting adversarial model poisoning attacks via a hardware watchdog,
    and failing over to a deterministic non-AI microcontroller.

    Args:
        iterations: Number of simulation iterations (if continuous is False).
        sleep_interval: Sleep duration between iterations in seconds (default: 0.5).
        log_path: Path to output JSON log file.
        continuous: If True, runs indefinitely until stopped.

    Returns:
        list: Full telemetry history of the simulation.
    """
    ai_controller = CompromisedAIController()
    watchdog = HardwareWatchdog()
    fallback = DeterministicFallback()

    log_history = []
    abs_log_path = os.path.abspath(log_path)

    mode_str = "continuous" if continuous else f"{iterations} iterations"
    print(f"[*] Starting EdgeGuard simulation: {mode_str} (interval: {sleep_interval}s)...")

    i = 0
    try:
        while True:
            i += 1
            if not continuous and iterations > 0 and i > iterations:
                break

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
            if len(log_history) > 100:
                log_history.pop(0)

            # Incrementally persist simulation log for real-time monitoring
            with open(abs_log_path, "w", encoding="utf-8") as f:
                json.dump(log_history, f, indent=2)

            time.sleep(sleep_interval)

    except KeyboardInterrupt:
        print("\n[*] Simulation paused by user.")

    print(f"[*] Simulation ended. Telemetry saved to {abs_log_path}")
    return log_history


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="EdgeGuard Simulation Engine")
    parser.add_argument("--iterations", type=int, default=0, help="Number of iterations (default: 0 for continuous)")
    parser.add_argument("--interval", type=float, default=0.5, help="Interval between ticks in seconds (default: 0.5)")
    args = parser.parse_args()

    is_continuous = args.iterations <= 0
    run_simulation(iterations=args.iterations, sleep_interval=args.interval, continuous=is_continuous)

