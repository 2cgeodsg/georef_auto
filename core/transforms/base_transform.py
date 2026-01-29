from abc import ABC, abstractmethod
from typing import List, Tuple, Optional
import numpy as np
import cv2

class BaseTransform(ABC):
    """
    Classe base para transformações geométricas (Homografia, Affine, TPS, etc).
    """

    @abstractmethod
    def estimate(self, pts1: np.ndarray, pts2: np.ndarray) -> bool:
        """
        Estima a transformação com base em dois conjuntos de pontos.
        """
        pass

    @abstractmethod
    def apply(self, image: np.ndarray, output_shape: Tuple[int, int]) -> np.ndarray:
        """
        Aplica a transformação à imagem de entrada, retornando a imagem transformada.
        """
        pass

    @abstractmethod
    def get_matrix(self) -> Optional[np.ndarray]:
        """
        Retorna a matriz de transformação estimada (se aplicável).
        """
        pass

    @abstractmethod
    def quality_metrics(self) -> dict:
        """
        Retorna métricas de qualidade da transformação.
        """
        pass
