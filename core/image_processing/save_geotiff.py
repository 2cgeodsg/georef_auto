# -*- coding: utf-8 -*-
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal, Tuple, Optional

import numpy as np
import rasterio
import rasterio.transform
from rasterio.warp import reproject, Resampling

import logging
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ReamostragemConfig:
    # Resolução alvo (unidade do CRS por pixel, e.g., metros/px)
    resolucao_alvo: float = 1.0

    # Método de reamostragem
    metodo: Literal["nearest", "bilinear", "cubic"] = "cubic"

    # NoData
    nodata_src: int = 0
    nodata_dst: int = 0

    # Compressão/Perfil de saída
    compress: str = "JPEG"              # "JPEG" | "DEFLATE" | "LZW" | ...
    jpeg_quality: int = 85
    photometric: Optional[str] = "YCBCR"  # para JPEG: "YCBCR" é o padrão comum

    # Tiles/BigTIFF
    tiled: bool = True
    blockxsize: int = 512
    blockysize: int = 512
    bigtiff: Literal["YES", "NO", "IF_NEEDED", "IF_SAFER"] = "IF_SAFER"

    # Paralelismo
    gdal_threads: str = "ALL_CPUS"      # GDAL_NUM_THREADS
    num_threads: Optional[int] = None   # None → usa os.cpu_count()

    # Overviews (opcional)
    build_overviews: bool = False
    overview_levels: Tuple[int, ...] = (2, 4, 8, 16)
    overview_resampling: Literal["nearest", "average", "cubic"] = "nearest"

    # Segurança de dtype
    enforce_uint8: bool = True          # JPEG exige uint8; se não for, converte/clampa


def _resampling_enum(nome: str) -> Resampling:
    mapa = {
        "nearest": Resampling.nearest,
        "bilinear": Resampling.bilinear,
        "cubic": Resampling.cubic,
        # Nota: adicione mais se necessário
    }
    return mapa.get(nome, Resampling.cubic)


def _overview_resampling_enum(nome: str) -> Resampling:
    mapa = {
        "nearest": Resampling.nearest,
        "average": Resampling.average,
        "cubic": Resampling.cubic,
    }
    return mapa.get(nome, Resampling.nearest)


def _prepare_profile_and_dtype(
    bands: int,
    dtype: np.dtype,
    dst_crs: str,
    dst_transform,
    altura_final: int,
    largura_final: int,
    cfg: ReamostragemConfig,
) -> Tuple[dict, np.dtype]:
    """
    Monta o profile do GTiff de saída e valida compatibilidade compress/photometric/dtype.
    Retorna (profile, dtype_final).
    """
    # Normaliza compress/photometric
    compress = (cfg.compress or "DEFLATE").upper()

    # JPEG: requer 3 bandas (ou 1) e dtype uint8. Fotometria típica: YCBCR para 3 bandas.
    final_dtype = dtype
    if compress == "JPEG":
        if bands not in (1, 3) or dtype != np.uint8:
            logger.warning(
                "Pedido compress=JPEG incompatível com bands=%d dtype=%s. "
                "Trocando para DEFLATE + predictor=2.", bands, dtype
            )
            compress = "DEFLATE"
        else:
            # ok: 3 bandas uint8 → photometric YCBCR; 1 banda → photometric MINISBLACK
            pass

    profile = dict(
        driver='GTiff',
        height=altura_final,
        width=largura_final,
        count=bands,
        dtype=final_dtype,
        crs=dst_crs,
        transform=dst_transform,
        nodata=cfg.nodata_dst,
        tiled=cfg.tiled,
        BIGTIFF=cfg.bigtiff,
    )

    if cfg.tiled:
        profile.update(blockxsize=cfg.blockxsize, blockysize=cfg.blockysize)

    if compress == "JPEG":
        profile.update(
            compress="JPEG",
            jpeg_quality=cfg.jpeg_quality,
            photometric=cfg.photometric or ("YCBCR" if bands == 3 else "MINISBLACK"),
        )
    else:
        # Preferível DEFLATE com predictor para dados contínuos; fotometria RGB se 3 bandas
        profile.update(compress=compress)
        if compress in ("DEFLATE", "LZW"):
            # predictor=2 ajuda em dados contínuos (não se aplica a JPEG)
            profile.update(predictor=2)
        if bands == 3:
            profile.update(photometric="RGB")

    return profile, final_dtype


def reamostrar_e_salvar_geotiff(
    img_crop_bgr: np.ndarray,
    extensao_geo,               # ExtensaoGeo: contém xmin, ymin, xmax, ymax
    crs_epsg: str,              # ex.: "EPSG:3857"
    x_res_ref: float,
    y_res_ref: float,
    caminho_saida: str,
    cfg: ReamostragemConfig = ReamostragemConfig()
) -> Tuple[int, int]:
    """
    Reamostra a imagem recortada para a resolução alvo e grava um GeoTIFF RGB **em streaming**,
    escrevendo direto no dataset por banda (menos uso de RAM).

    Retorna (largura_final_px, altura_final_px).
    """
    if img_crop_bgr.ndim != 3 or img_crop_bgr.shape[2] != 3:
        raise ValueError("Esperada imagem cropped BGR (H,W,3).")

    # Garante uint8 se necessário (JPEG)
    if cfg.enforce_uint8 and img_crop_bgr.dtype != np.uint8:
        logger.warning("Convertendo dtype %s -> uint8 para compatibilidade.", img_crop_bgr.dtype)
        img_crop_bgr = np.clip(img_crop_bgr, 0, 255).astype(np.uint8, copy=False)

    h_src, w_src = img_crop_bgr.shape[:2]

    # Transform de origem (coordenadas do recorte na grade da referência)
    src_transform = rasterio.transform.from_origin(
        extensao_geo.xmin, extensao_geo.ymax, x_res_ref, y_res_ref
    )
    src_crs = crs_epsg

    # Dimensões alvo pela resolução solicitada
    geo_width = float(extensao_geo.xmax - extensao_geo.xmin)
    geo_height = float(extensao_geo.ymax - extensao_geo.ymin)
    largura_final = max(1, int(round(geo_width / cfg.resolucao_alvo)))
    altura_final  = max(1, int(round(geo_height / cfg.resolucao_alvo)))

    dst_transform = rasterio.transform.from_origin(
        extensao_geo.xmin, extensao_geo.ymax, cfg.resolucao_alvo, cfg.resolucao_alvo
    )
    dst_crs = src_crs

    logger.info(
        "Reamostrando (streaming) para %dx%d (resolução=%.3f). Método=%s",
        largura_final, altura_final, cfg.resolucao_alvo, cfg.metodo
    )

    # OpenCV é BGR; Rasterio espera bandas individuais em ordem RGB
    bandas_src_rgb = [
        img_crop_bgr[:, :, 2],  # R
        img_crop_bgr[:, :, 1],  # G
        img_crop_bgr[:, :, 0],  # B
    ]
    resampling = _resampling_enum(cfg.metodo)
    overview_resampling = _overview_resampling_enum(cfg.overview_resampling)

    # Monta profile de saída e valida compress/photometric
    profile, _ = _prepare_profile_and_dtype(
        bands=3,
        dtype=img_crop_bgr.dtype,
        dst_crs=dst_crs,
        dst_transform=dst_transform,
        altura_final=altura_final,
        largura_final=largura_final,
        cfg=cfg,
    )

    # Threads: GDAL e algoritmo
    gdal_threads = cfg.gdal_threads or "ALL_CPUS"
    num_threads = cfg.num_threads if (cfg.num_threads and cfg.num_threads > 0) else max(1, (os.cpu_count() or 1))

    with rasterio.Env(GDAL_NUM_THREADS=gdal_threads):
        with rasterio.open(caminho_saida, 'w', **profile) as dst:
            # Reprojetar e escrever diretamente no arquivo por banda
            for i, src in enumerate(bandas_src_rgb, start=1):
                reproject(
                    source=src,
                    destination=rasterio.band(dst, i),
                    src_transform=src_transform,
                    src_crs=src_crs,
                    src_nodata=cfg.nodata_src,
                    dst_transform=dst_transform,
                    dst_crs=dst_crs,
                    dst_nodata=cfg.nodata_dst,
                    resampling=resampling,
                    num_threads=num_threads
                )

        # Overviews opcionais (reabre r+)
        if cfg.build_overviews and len(cfg.overview_levels) > 0:
            try:
                with rasterio.open(caminho_saida, 'r+') as dst_ovr:
                    dst_ovr.build_overviews(list(cfg.overview_levels), overview_resampling)
                    # A anotação abaixo é só informativa (não obrigatória)
                    dst_ovr.update_tags(ns='rio_overview', resampling=cfg.overview_resampling)
            except Exception as e:
                logger.warning("Falha ao gerar overviews: %s", e)

    logger.info("GeoTIFF salvo: %s", caminho_saida)
    return (largura_final, altura_final)
