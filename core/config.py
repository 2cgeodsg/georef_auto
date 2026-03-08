from dataclasses import dataclass

@dataclass(frozen=True)
class GeoreferencingConfig:
    # Render
    render_width_px: int = 2000

    # RANSAC/USAC
    ransac_reproj_thresh_px: float = 5.0
    ransac_confidence: float = 0.995

    # Warp
    warp_interpolation: int = 3  # cv2.INTER_CUBIC

    # Reamostragem
    target_resolution: float = 1.0
    resampling: str = "cubic"     # "nearest"|"bilinear"|"cubic"
    clamp_upsampling: bool = False

    # Qualidade/aceitação (georeferenciamento)
    min_features: int = 8              # recomendado >= 8; 4 é piso teórico
    min_inlier_ratio: float = 0.25     # aceita se inliers >= 25% dos good matches

    # Limites de área (proteção operacional)
    max_polygon_area_km2: float = 3050.0   # evita WMS/render pesados
    warn_polygon_area_km2: float = 1500.0  # apenas aviso no log

    # Procura do MI
    search_division: int = 8
    search_min_features: int = 1    # mínimo para não descartar a região como possibilidade.
