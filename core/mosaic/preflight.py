# -*- coding: utf-8 -*-
"""
Pré-voo de memória para mosaico (warp + blend) antes da alocação de canvas.

Responsabilidades (SRP):
- Estimar o bbox de saída (em pixels) a partir de H e dimensões das imagens.
- Estimar memória necessária e comparar com a RAM disponível (com margem).
- Decidir: prosseguir, sugerir reescala (f <= 1) ou bloquear com motivo claro.

Boas práticas aplicadas:
- Validação explícita da homografia (NaN/Inf/degenerada);
- Política conservadora quando psutil não está disponível;
- Limites configuráveis de megapixels e margem de segurança;
- Tipagem forte, docstrings e funções puras (testáveis).

Compatibilidade:
- Mantém classes/assinaturas: PreVooConfig, PreVooResultado, prever_canvas_e_memoria(...).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple, Protocol
import math
import numpy as np

try:
    import psutil  # opcional, para RAM livre
except Exception:  # pragma: no cover
    psutil = None


# =========================
# Types & Config
# =========================

@dataclass(frozen=True)
class PreVooConfig:
    """
    Configurações do pré-voo.

    safety_margin:
        Fração da RAM livre que pode ser usada (ex.: 0.6 = 60%).
    max_megapix_canvas:
        Limite duro por canvas em megapixels (ex.: 120–300 MP).
        É aplicado antes de qualquer alocação grande.
    canais:
        Nº de canais previsto do canvas (3 para RGB).
    bytes_por_canal:
        1 para uint8; 2 para uint16; etc.
    """
    safety_margin: float = 0.60
    max_megapix_canvas: float = 300.0
    canais: int = 3
    bytes_por_canal: int = 1  # uint8


@dataclass(frozen=True)
class PreVooResultado:
    """
    Resultado do pré-voo para um par base+alvo.
    """
    pode_prosseguir: bool
    motivo: str
    largura_out: int
    altura_out: int
    pixels_out: int
    memoria_necessaria_bytes: int
    memoria_disponivel_bytes: Optional[int]
    memoria_limite_bytes: Optional[int]
    fator_resize_sugerido: Optional[float]  # <= 1.0 (ex.: 0.7) para caber no orçamento


# =========================
# Strategy: provedor de memória
# =========================

class ProvedorMemoria(Protocol):
    def memoria_disponivel(self) -> Optional[int]:
        """Retorna bytes de memória livre no momento ou None se não disponível."""
        ...


class ProvedorMemoriaPsutil:
    def memoria_disponivel(self) -> Optional[int]:
        if psutil is None:
            return None
        try:
            return int(psutil.virtual_memory().available)
        except Exception:
            return None


class ProvedorMemoriaNulo:
    def memoria_disponivel(self) -> Optional[int]:
        return None


# =========================
# Funções utilitárias
# =========================

def _format_bytes(n: Optional[int]) -> str:
    if n is None:
        return "desconhecido"
    if n <= 0:
        return "0 B"
    unidades = ["B", "KB", "MB", "GB", "TB"]
    i = min(int(math.floor(math.log(n, 1024))), len(unidades) - 1)
    valor = n / (1024 ** i)
    return f"{valor:.2f} {unidades[i]}"


def _cantos_imagem(w: int, h: int) -> np.ndarray:
    """Retorna os quatro cantos (x,y,1) em homogêneas."""
    return np.array([[0,   0,   1],
                     [w-1, 0,   1],
                     [w-1, h-1, 1],
                     [0,   h-1, 1]], dtype=np.float64)


def _aplicar_H(cantos_xy1: np.ndarray, H: np.ndarray) -> np.ndarray:
    """Aplica homografia aos cantos (N,3) → (N,2) em coordenadas cartesianas."""
    proj = (H @ cantos_xy1.T).T  # (N,3)
    w = proj[:, 2:3]
    # Evita divisão por zero / degenerescência
    w = np.where(np.abs(w) < 1e-12, 1e-12, w)
    xy = proj[:, 0:2] / w
    return xy


def _bbox_union_xy(xy: np.ndarray) -> Tuple[int, int, int, int]:
    """BBox inteiro (xmin, ymin, xmax_inclusive, ymax_inclusive) a partir de pontos (N,2)."""
    xmin = int(math.floor(float(np.min(xy[:, 0]))))
    ymin = int(math.floor(float(np.min(xy[:, 1]))))
    xmax = int(math.ceil (float(np.max(xy[:, 0]))))
    ymax = int(math.ceil (float(np.max(xy[:, 1]))))
    return xmin, ymin, xmax, ymax


def _dimensoes_bbox(xmin: int, ymin: int, xmax: int, ymax: int) -> Tuple[int, int]:
    """Converte bbox inclusiva em (largura, altura)."""
    largura = max(1, xmax - xmin + 1)
    altura  = max(1, ymax - ymin + 1)
    return largura, altura


def _memoria_necessaria_bytes(larg: int, alt: int, canais: int, bytes_por_canal: int) -> int:
    return int(larg) * int(alt) * int(canais) * int(bytes_por_canal)


def _homografia_valida(H: np.ndarray) -> bool:
    """
    Valida homografia:
    - shape 3x3;
    - não contém NaN/Inf;
    - não é quase nula (norma muito pequena).
    """
    if not isinstance(H, np.ndarray):
        return False
    if H.shape != (3, 3):
        return False
    if not np.isfinite(H).all():
        return False
    if np.linalg.norm(H) < 1e-12:
        return False
    return True


# =========================
# API principal
# =========================

def prever_canvas_e_memoria(
    tamanho_base: Tuple[int, int],       # (h_base, w_base)
    tamanho_alvo: Tuple[int, int],       # (h_alvo, w_alvo)
    H_alvo2base: np.ndarray,
    cfg: PreVooConfig,
    provedor_memoria: Optional[ProvedorMemoria] = None,
    incluir_base_no_bbox: bool = True
) -> PreVooResultado:
    """
    Estima dimensões do canvas e memória necessária para warpar e fundir alvo sobre base.

    Parâmetros:
        tamanho_base: (h, w) da imagem base.
        tamanho_alvo: (h, w) da imagem alvo.
        H_alvo2base : homografia que leva coordenadas do alvo para o sistema da base.
        cfg         : configurações do pré-voo (limites, canais, bytes/canal).
        provedor_memoria: Strategy para obter RAM livre (psutil por padrão).
        incluir_base_no_bbox: se True, união(base, alvo_warpado); caso False, apenas alvo_warpado.

    Retorna:
        PreVooResultado com decisão e recomendações.
    """
    if provedor_memoria is None:
        provedor_memoria = ProvedorMemoriaPsutil()

    # 0) Validação da homografia
    if not _homografia_valida(H_alvo2base):
        motivo = "Homografia inválida (NaN/Inf/dimensão incorreta/degenerada)."
        return PreVooResultado(
            pode_prosseguir=False,
            motivo=motivo,
            largura_out=1,
            altura_out=1,
            pixels_out=1,
            memoria_necessaria_bytes=_memoria_necessaria_bytes(1, 1, cfg.canais, cfg.bytes_por_canal),
            memoria_disponivel_bytes=_safe_mem(provedor_memoria),
            memoria_limite_bytes=None,
            fator_resize_sugerido=None
        )

    # 1) Medidas
    hB, wB = tamanho_base
    hA, wA = tamanho_alvo
    if min(hB, wB, hA, wA) <= 0:
        return PreVooResultado(
            pode_prosseguir=False,
            motivo="Dimensões inválidas (altura/largura <= 0).",
            largura_out=1,
            altura_out=1,
            pixels_out=1,
            memoria_necessaria_bytes=_memoria_necessaria_bytes(1, 1, cfg.canais, cfg.bytes_por_canal),
            memoria_disponivel_bytes=_safe_mem(provedor_memoria),
            memoria_limite_bytes=None,
            fator_resize_sugerido=None
        )

    # 2) Cantos no sistema da base
    cantos_base = _cantos_imagem(wB, hB)
    cantos_alvo = _cantos_imagem(wA, hA)
    cantos_alvo_w = _aplicar_H(cantos_alvo, H_alvo2base)

    # Verifica projeção numérica
    if not np.isfinite(cantos_alvo_w).all():
        return PreVooResultado(
            pode_prosseguir=False,
            motivo="Projeção do alvo gerou coordenadas não finitas (NaN/Inf).",
            largura_out=1,
            altura_out=1,
            pixels_out=1,
            memoria_necessaria_bytes=_memoria_necessaria_bytes(1, 1, cfg.canais, cfg.bytes_por_canal),
            memoria_disponivel_bytes=_safe_mem(provedor_memoria),
            memoria_limite_bytes=None,
            fator_resize_sugerido=None
        )

    # 3) BBox da união (base + alvo_warpado, se solicitado)
    pontos = [cantos_alvo_w]
    if incluir_base_no_bbox:
        pontos.append(cantos_base[:, :2])
    pts = np.vstack(pontos)

    xmin, ymin, xmax, ymax = _bbox_union_xy(pts)
    larg_out, alt_out = _dimensoes_bbox(xmin, ymin, xmax, ymax)
    pixels_out = int(larg_out) * int(alt_out)

    # 4) Limite duro por MP (proteção rápida antes de memória)
    cap_pixels = int(cfg.max_megapix_canvas * 1_000_000)
    if pixels_out > cap_pixels:
        motivo = (
            f"Canvas estimado {larg_out}x{alt_out} ({pixels_out/1e6:.1f} MP) "
            f"excede o limite {cfg.max_megapix_canvas:.0f} MP."
        )
        memoria_nec = _memoria_necessaria_bytes(larg_out, alt_out, cfg.canais, cfg.bytes_por_canal)
        return PreVooResultado(
            pode_prosseguir=False,
            motivo=motivo,
            largura_out=larg_out,
            altura_out=alt_out,
            pixels_out=pixels_out,
            memoria_necessaria_bytes=memoria_nec,
            memoria_disponivel_bytes=_safe_mem(provedor_memoria),
            memoria_limite_bytes=None,
            fator_resize_sugerido=_resize_sugerido_para_cap(pixels_out, cfg.max_megapix_canvas)
        )

    # 5) Estimativa de memória necessária
    memoria_nec = _memoria_necessaria_bytes(larg_out, alt_out, cfg.canais, cfg.bytes_por_canal)

    # 6) RAM disponível e orçamento com margem
    mem_disp = _safe_mem(provedor_memoria)
    if mem_disp is None:
        # Política conservadora sem psutil: só permite se dentro do CAP de MP.
        return PreVooResultado(
            pode_prosseguir=True,  # dentro do CAP por MP, permitir
            motivo=(f"Memória disponível desconhecida (psutil indisponível). "
                    f"Prosseguindo com CAP {cfg.max_megapix_canvas:.0f} MP."),
            largura_out=larg_out,
            altura_out=alt_out,
            pixels_out=pixels_out,
            memoria_necessaria_bytes=memoria_nec,
            memoria_disponivel_bytes=None,
            memoria_limite_bytes=None,
            fator_resize_sugerido=None
        )

    orcamento = int(mem_disp * cfg.safety_margin)

    if memoria_nec <= orcamento:
        return PreVooResultado(
            pode_prosseguir=True,
            motivo=(f"OK: necessário {_format_bytes(memoria_nec)} ≤ "
                    f"orçamento {_format_bytes(orcamento)} "
                    f"(margem {int(cfg.safety_margin*100)}%)."),
            largura_out=larg_out,
            altura_out=alt_out,
            pixels_out=pixels_out,
            memoria_necessaria_bytes=memoria_nec,
            memoria_disponivel_bytes=mem_disp,
            memoria_limite_bytes=orcamento,
            fator_resize_sugerido=None
        )

    # 7) Excede orçamento → sugerir reescala (f <= 1.0)
    fator = _resize_para_caber(pixels_out, cfg.canais, cfg.bytes_por_canal, orcamento)
    return PreVooResultado(
        pode_prosseguir=False,
        motivo=(f"Excede orçamento: necessário {_format_bytes(memoria_nec)} > "
                f"orçamento {_format_bytes(orcamento)} "
                f"(margem {int(cfg.safety_margin*100)}%)."),
        largura_out=larg_out,
        altura_out=alt_out,
        pixels_out=pixels_out,
        memoria_necessaria_bytes=memoria_nec,
        memoria_disponivel_bytes=mem_disp,
        memoria_limite_bytes=orcamento,
        fator_resize_sugerido=fator
    )


# =========================
# Helpers internos
# =========================

def _safe_mem(provedor: ProvedorMemoria) -> Optional[int]:
    try:
        return provedor.memoria_disponivel()
    except Exception:
        return None


def _resize_para_caber(pixels_out: int, canais: int, bpc: int, orcamento: int) -> float:
    """
    Calcula fator de reescala f <= 1.0 tal que:
        (f^2 * pixels_out) * canais * bpc <= orcamento
      => f <= sqrt( orcamento / (pixels_out * canais * bpc) )

    Retorna f ∈ [0.05, 1.0] (limite inferior evita degenerescência).
    """
    denom = pixels_out * canais * bpc
    if denom <= 0:
        return 1.0
    f = math.sqrt(max(1e-12, orcamento / float(denom)))
    return float(min(1.0, max(0.05, f)))


def _resize_sugerido_para_cap(pixels_out: int, cap_megapix: float) -> Optional[float]:
    """
    Para limite por MP:
        f^2 * pixels_out <= cap_megapix * 1e6  =>  f <= sqrt(cap / pixels)
    """
    if pixels_out <= 0:
        return None
    cap_pixels = cap_megapix * 1_000_000
    f2 = cap_pixels / float(pixels_out)
    if f2 >= 1.0:
        return 1.0
    f = math.sqrt(max(1e-12, f2))
    return float(max(0.05, f))
