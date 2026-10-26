# EdgeGuard: Edge AI Resilience & Failover Framework

EdgeGuard provides resilient edge computing telemetry monitoring, adversarial poisoning attack detection, and sub-millisecond hardware watchdog failover to deterministic fallback microcontrollers.

## Architecture

- **Primary Edge AI (`models/`)**: Simulates neural network inference for real-time edge voltage regulation. Includes `CompromisedAIController` simulating adversarial poisoning voltage spikes.
- **Hardware Watchdog (`watchdog/`)**: Independent safety validator verifying output parameters against critical physical hardware boundaries (200V – 250V).
- **Deterministic Fallback (`fallback/`)**: Safe, non-AI microcontroller providing guaranteed safe trickle voltage (210V) when watchdog trips.
- **Simulation Engine (`core/`)**: Simulates grid load, battery temperature, attack detection, and logs failover latencies.
- **Telemetry Dashboard (`dashboard/`)**: High-performance real-time Flask web UI monitoring live voltage, active controller states, and millisecond failover events.

## Getting Started

### Installation
```bash
pip install -r requirements.txt
```

### Running EdgeGuard
Execute the master runner to launch both the telemetry dashboard and simulation engine simultaneously:
```bash
python main.py
```
Then navigate to:
[http://127.0.0.1:5000](http://127.0.0.1:5000)
