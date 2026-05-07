
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class RegrasQualidadeHomografia:
    min_inliers: int = 4
    min_inlier_ratio: float = 0.2  # ex.: pelo menos 20% dos matches

class HomographyQualityEvaluator:
    """Avalia se a homografia e sua máscara são aceitáveis."""
    def __init__(self, regras: RegrasQualidadeHomografia = RegrasQualidadeHomografia()):
        self.regras = regras

    def is_acceptable(self, n_inliers: int, n_total: int) -> bool:
        if n_total <= 0:
            return False
        ratio = n_inliers / float(n_total)
        return (n_inliers >= self.regras.min_inliers) and (ratio >= self.regras.min_inlier_ratio)

    def build_fail_message(self, n_inliers: int, n_total: int) -> str:
        ratio = (n_inliers / float(n_total)) if n_total > 0 else 0.0
        return (f"Qualidade insuficiente: inliers={n_inliers}/{n_total} "
                f"(razão={ratio:.2f}), mínimo esperado: "
                f"inliers>={self.regras.min_inliers} e razão>={self.regras.min_inlier_ratio:.2f}.")
