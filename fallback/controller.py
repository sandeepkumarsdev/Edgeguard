class DeterministicFallback:
    """Non-AI, hardcoded microcontroller fallback controller.

    Provides a fail-safe, deterministic trickle-charge voltage
    when the primary edge AI is compromised or trips the hardware watchdog.
    """

    def get_safe_voltage(self) -> float:
        """Returns a static, universally safe trickle-charge voltage.

        Returns:
            float: Fixed safe voltage of 210.0V.
        """
        return 210.0
