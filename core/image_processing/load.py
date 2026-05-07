from ...dependencies import cv2
from ...dependencies import numpy as np
from typing import Optional
from ...utils.logger import logger

def load_image(image_path: str) -> Optional[np.ndarray]:
    """Carrega uma imagem do caminho especificado."""
    try:
        imagem = cv2.imread(image_path)
        if imagem is None:
            logger.error(f"Não foi possível carregar a imagem: {image_path}")
            return None
        logger.info(f"Imagem carregada com sucesso: {image_path}")
        return imagem
    except Exception as e:
        logger.error(f"Erro ao carregar imagem {image_path}: {e}")
        return None

def convert_to_grayscale(imagem: np.ndarray) -> np.ndarray:
    """Converte uma imagem colorida para escala de cinza, se necessário."""
    try:
        if len(imagem.shape) == 3 and imagem.shape[2] == 3:
            return cv2.cvtColor(imagem, cv2.COLOR_BGR2GRAY)
        return imagem
    except Exception as e:
        logger.error(f"Erro ao converter para escala de cinza: {e}")
        return imagem
