from abc import ABC, abstractmethod
from typing import Tuple, List, Optional
from ...dependencies import numpy as np

class BaseDetector(ABC):
    @abstractmethod
    def detect_and_compute(self, image_gray: np.ndarray) -> Tuple[List, Optional[np.ndarray]]:
        pass

    @property
    @abstractmethod
    def descriptor_type(self) -> str:
        """Retorna o tipo do descritor ('float32' ou 'uint8')."""
        pass
