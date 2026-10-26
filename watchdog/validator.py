import hashlib
import logging
import sys
from typing import Optional, Tuple

logger = logging.getLogger("HardwareWatchdog")
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter("%(asctime)s - [%(levelname)s] - %(name)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)


class HardwareWatchdog:
    """Simulates a hardware-level safety watchdog and secure boot validator."""

    def verify_model_integrity(self, filepath: str) -> str:
        """Computes and returns the SHA-256 checksum of a given file for secure boot verification.

        Args:
            filepath: Path to the target model or component file.

        Returns:
            str: Hexadecimal SHA-256 digest of the file.
        """
        sha256_hash = hashlib.sha256()
        with open(filepath, "rb") as f:
            for byte_block in iter(lambda: f.read(65536), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def validate_output(self, voltage: float) -> Tuple[bool, Optional[float]]:
        """Validates that the output voltage lies within safe hardware operating limits.

        Args:
            voltage: Predicted or measured voltage level.

        Returns:
            Tuple[bool, Optional[float]]:
                - (True, voltage) if within the safe 200V - 250V threshold.
                - (False, None) if outside safe threshold, logging a critical alert.
        """
        if voltage is not None and 200.0 <= float(voltage) <= 250.0:
            return True, float(voltage)

        alert_message = (
            f"[CRITICAL SECURITY ALERT] Hardware Watchdog Tripped! "
            f"Anomalous voltage detected: {voltage}V. Safe operating window is 200V - 250V."
        )
        logger.critical(alert_message)
        return False, None
