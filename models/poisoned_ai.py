import random
try:
    from models.baseline_ai import EdgeAIController
except ImportError:
    from baseline_ai import EdgeAIController


class CompromisedAIController(EdgeAIController):
    """Compromised Edge AI Controller simulating an adversarial poisoning attack.

    85% of the time it operates normally using the parent controller's safe logic,
    while 15% of the time it injects a dangerous voltage spike strictly exceeding safe limits (> 250V).
    """

    def __init__(self, attack_rate: float = 0.15):
        super().__init__()
        self.attack_rate = attack_rate

    @staticmethod
    def generate_unsafe_voltage() -> float:
        """Generates a random dangerous voltage strictly exceeding the safe limit (> 250V).

        Simulates realistic edge power overvoltages across diverse hazard tiers:
        - Moderate overvoltage surge (260.0V - 480.0V)
        - High-energy industrial spike (500.0V - 1500.0V)
        - Catastrophic flashover surge (1600.0V - 5500.0V)
        """
        tier = random.choices(["moderate", "high", "catastrophic"], weights=[0.45, 0.35, 0.20])[0]
        if tier == "moderate":
            voltage = random.uniform(260.0, 480.0)
        elif tier == "high":
            voltage = random.uniform(500.0, 1500.0)
        else:
            voltage = random.uniform(1600.0, 5500.0)
        return round(float(voltage), 2)

    def predict_voltage(self, grid_load: float, battery_temp: float) -> float:
        """Predicts charging voltage, simulating intermittent adversarial attack injection.

        Args:
            grid_load: Relative load on the electrical grid (0.0 to 1.0).
            battery_temp: Battery cell temperature in Celsius (20.0 to 60.0).

        Returns:
            float: Safe voltage (220V - 240V) or dangerous attack spike (> 250V).
        """
        # 15% chance of adversarial voltage spike injection
        if random.random() < self.attack_rate:
            return self.generate_unsafe_voltage()

        # 85% safe operation via parent EdgeAIController
        return super().predict_voltage(grid_load, battery_temp)
