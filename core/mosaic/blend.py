# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Optional, Tuple
import numpy as np
import cv2

def _homografia_valida(H: np.ndarray) -> bool:
    """Valida se H é 3x3, finita e não degenerada."""
    if not isinstance(H, np.ndarray) or H.shape != (3, 3):
        return False
    if not np.isfinite(H).all():
        return False
    if np.linalg.norm(H) < 1e-12:
        return False
    return True


def _ajustar_canais(img_base: np.ndarray, img_alvo: np.ndarray) -> Tuple[np.ndarray, np.ndarray, int]:
    """
    Garante que base e alvo tenham o MESMO nº de canais para fusão.
    - Se uma for cinza (1 canal) e a outra BGR (3 canais), expande a cinza para 3 canais.
    - Mantém dtype uint8 (evita dobrar memória).
    Retorna: (base_ok, alvo_ok, n_canais)
    """
    base = img_base
    alvo = img_alvo

    if base.dtype != np.uint8:
        base = base.astype(np.uint8, copy=False)
    if alvo.dtype != np.uint8:
        alvo = alvo.astype(np.uint8, copy=False)

    # Detecta canais
    cb = 1 if base.ndim == 2 else base.shape[2]
    ca = 1 if alvo.ndim == 2 else alvo.shape[2]

    # Uniformiza para o maior nº de canais
    n_canais = max(cb, ca)
    if n_canais not in (1, 3):
        # normaliza para 3 canais como fallback
        n_canais = 3

    if cb != n_canais:
        if cb == 1 and n_canais == 3:
            base = cv2.cvtColor(base, cv2.COLOR_GRAY2BGR)
        elif cb == 3 and n_canais == 1:
            base = cv2.cvtColor(base, cv2.COLOR_BGR2GRAY)

    if ca != n_canais:
        if ca == 1 and n_canais == 3:
            alvo = cv2.cvtColor(alvo, cv2.COLOR_GRAY2BGR)
        elif ca == 3 and n_canais == 1:
            alvo = cv2.cvtColor(alvo, cv2.COLOR_BGR2GRAY)

    return base, alvo, n_canais


def _bbox_union_com_base(hB: int, wB: int, hA: int, wA: int, H_alvo2base: np.ndarray) -> Tuple[int, int, int, int]:
    """
    Calcula o bbox inteiro mínimo que contém: base e alvo-warpado (no sistema da base).
    Retorna (xmin, ymin, xmax, ymax) inclusivos.
    """
    cantos_base = np.array([[0, 0, 1],
                            [wB - 1, 0, 1],
                            [wB - 1, hB - 1, 1],
                            [0, hB - 1, 1]], dtype=np.float64)
    cantos_alvo = np.array([[0, 0, 1],
                            [wA - 1, 0, 1],
                            [wA - 1, hA - 1, 1],
                            [0, hA - 1, 1]], dtype=np.float64)

    proj = (H_alvo2base @ cantos_alvo.T).T  # (4,3)
    w = proj[:, 2:3]
    w = np.where(np.abs(w) < 1e-12, 1e-12, w)  # evita divisão por zero
    alvo_xy = proj[:, :2] / w

    if not np.isfinite(alvo_xy).all():
        # coordenadas inválidas → bbox trivial para bloquear logo adiante
        return 0, 0, 0, 0

    pts = np.vstack([alvo_xy, cantos_base[:, :2].astype(np.float64)])
    xmin = int(np.floor(pts[:, 0].min()))
    ymin = int(np.floor(pts[:, 1].min()))
    xmax = int(np.ceil(pts[:, 0].max()))
    ymax = int(np.ceil(pts[:, 1].max()))
    return xmin, ymin, xmax, ymax


def warp_e_fundir(img_base: np.ndarray,
                  img_alvo: np.ndarray,
                  H_alvo2base: np.ndarray,
                  max_megapix: float = 300.0,
                  interp: int = cv2.INTER_LINEAR,
                  border_value: Tuple[int, int, int] = (0, 0, 0)) -> Optional[np.ndarray]:
    """
    Warpa 'img_alvo' para o sistema da 'img_base' e funde por sobreposição simples.

    Regras de segurança de memória:
      - CAP duro por megapixels (max_megapix) aplicado ANTES de alocar canvas.
      - Homografia validada (shape, finitude, não degenerada).
      - Ajuste automático de canais (cinza/BGR) para evitar broadcast indevido.

    Parâmetros
    ---------
    img_base : np.ndarray
        Base (BGR ou cinza).
    img_alvo : np.ndarray
        Alvo (BGR ou cinza).
    H_alvo2base : np.ndarray
        Homografia que leva coordenadas do ALVO para o sistema da BASE.
    max_megapix : float
        Limite duro de pixels do canvas (MP). Ex.: 120–300.
    interp : int
        Interpolação do warp (cv2.INTER_LINEAR por padrão).
    border_value : Tuple[int,int,int]
        Cor de borda no warp (quando extrapola). Para imagens cinza, usa-se o primeiro valor.

    Retorna
    -------
    Optional[np.ndarray]
        Canvas (mesmos canais da base/alvo após harmonização) ou None se
        exceder CAP / homografia inválida / falha de memória.
    """
    # 0) Homografia válida?
    if H_alvo2base is None or not _homografia_valida(H_alvo2base):
        return None

    # 1) Dtype + canais harmonizados (economia de RAM e fusão correta)
    base, alvo, n_canais = _ajustar_canais(img_base, img_alvo)

    hB, wB = base.shape[:2]
    hA, wA = alvo.shape[:2]
    if min(hB, wB, hA, wA) <= 0:
        return None

    # 2) BBox união (base + alvo_warpado)
    xmin, ymin, xmax, ymax = _bbox_union_com_base(hB, wB, hA, wA, H_alvo2base)
    out_w = max(1, xmax - xmin + 1)
    out_h = max(1, ymax - ymin + 1)

    # 3) CAP antes de QUALQUER alocação grande
    total_pix = int(out_w) * int(out_h)
    if total_pix <= 0 or total_pix > int(max_megapix * 1_000_000):
        return None

    # 4) Transformação de translação para origem do canvas
    T = np.array([[1.0, 0.0, -float(xmin)],
                  [0.0, 1.0, -float(ymin)],
                  [0.0, 0.0, 1.0]], dtype=np.float64)
    H_canvas = T @ H_alvo2base

    # 5) Canvas e posicionamento da base
    #    - Usa nº de canais harmonizado
    try:
        if n_canais == 1:
            canvas = np.zeros((out_h, out_w), dtype=np.uint8)
        else:
            canvas = np.zeros((out_h, out_w, 3), dtype=np.uint8)
    except Exception:
        # Falha ao alocar (MemoryError do Python)
        return None

    tx, ty = -xmin, -ymin
    # recorte defensivo caso bbox seja "apertado" no limite:
    y1 = min(ty + hB, canvas.shape[0])
    x1 = min(tx + wB, canvas.shape[1])
    if y1 > ty and x1 > tx:
        canvas[ty:y1, tx:x1] = base[0:(y1 - ty), 0:(x1 - tx)]

    # 6) Warp do alvo no espaço do canvas (com try/except para OOM do OpenCV)
    try:
        if n_canais == 1 and isinstance(border_value, tuple):
            # para cinza usar apenas o primeiro componente
            bv = int(border_value[0]) if border_value else 0
            warped = cv2.warpPerspective(alvo, H_canvas, (out_w, out_h),
                                         flags=interp, borderValue=bv)
        else:
            warped = cv2.warpPerspective(alvo, H_canvas, (out_w, out_h),
                                         flags=interp, borderValue=border_value)
    except cv2.error:
        # inclui caso 'Insufficient memory' do OpenCV
        return None

    # 7) Fusão por máscara (não grava zeros) + recorte mínimo
    if n_canais == 1:
        mask = warped != 0
        canvas[mask] = warped[mask]
        mask_total = mask | (canvas != 0)
    else:
        mask = (warped != 0).any(axis=2)
        canvas[mask] = warped[mask]
        mask_total = mask | ((canvas != 0).any(axis=2))

    ys, xs = np.where(mask_total)
    if ys.size:
        y0, y1 = ys.min(), ys.max() + 1
        x0, x1 = xs.min(), xs.max() + 1
        canvas = canvas[y0:y1, x0:x1]

    return canvas
