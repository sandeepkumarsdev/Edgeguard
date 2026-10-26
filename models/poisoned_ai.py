import random
try:
    from models.baseline_ai import EdgeAIController
except ImportError:
    from baseline_ai import EdgeAIController


class CompromisedAIController(EdgeAIController):
    """Compromised Edge AI Controller simulating an adversarial poisoning attack.

    85% of the time it operates normally using the parent controller's safe logic,
    while 15% of the time it injects a catastrophic voltage spike (5000V).
    """

    def __init__(self, attack_rate: float = 0.15):
        super().__init__()
        self.attack_rate = attack_rate

    def predict_voltage(self, grid_load: float, battery_temp: float) -> float:
        """Predicts charging voltage, simulating intermittent adversarial attack injection.

        Args:
            grid_load: Relative load on the electrical grid (0.0 to 1.0).
            battery_temp: Battery cell temperature in Celsius (20.0 to 60.0).

        Returns:
            float: Safe voltage (220V - 240V) or catastrophic spike (5000V).
        """
        # 15% chance of adversarial voltage spike injection
        if random.random() < self.attack_rate:
            return 5000.0

        # 85% safe operation via parent EdgeAIController
        return super().predict_voltage(grid_load, battery_temp)
