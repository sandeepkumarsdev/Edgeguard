import math


class EdgeAIController:
    """Edge AI Controller simulating neural network inference for safe edge voltage regulation."""

    def __init__(self):
        # Simulated weights and bias for edge inference
        self.weight_grid = -1.85
        self.weight_temp = -2.15
        self.bias = 2.0

    def predict_voltage(self, grid_load: float, battery_temp: float) -> float:
        """Simulates neural network inference to predict safe charging voltage.

        Args:
            grid_load: Relative load on the electrical grid (0.0 to 1.0).
            battery_temp: Battery cell temperature in Celsius (20.0 to 60.0).

        Returns:
            float: Safe charging voltage strictly between 220.0V and 240.0V.
        """
        # Normalize and bound inputs
        norm_load = max(0.0, min(1.0, float(grid_load)))
        norm_temp = (max(20.0, min(60.0, float(battery_temp))) - 20.0) / 40.0

        # Simulated feedforward neural activation: z = w1*x1 + w2*x2 + b
        z = (self.weight_grid * norm_load) + (self.weight_temp * norm_temp) + self.bias

        # Sigmoid activation function to map output within (0, 1)
        activation = 1.0 / (1.0 + math.exp(-z))

        # Scale activation to safe voltage range strictly between 220V and 240V
        min_safe_voltage = 221.0
        max_safe_voltage = 239.0
        voltage = min_safe_voltage + (max_safe_voltage - min_safe_voltage) * activation

        # Safety clamp to guarantee voltage is strictly within (220.0, 240.0)
        voltage = max(220.1, min(239.9, voltage))
        return round(float(voltage), 2)
