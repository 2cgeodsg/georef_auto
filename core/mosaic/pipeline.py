# -*- coding: utf-8 -*-
"""
Pipeline de mosaico (não georreferenciado) - VERSÃO CORRIGIDA 2

Esta versão substitui a lógica complexa do plugin pela implementação direta
adaptada do script original `mosaico_multi_grupos.py`, que demonstrou o
comportamento correto. O objetivo é garantir que o resultado seja idêntico
ao do script standalone.

- Remove dependências do `feature_match`, `preflight`, etc.
- Implementa `_encontrar_pontos_homologos` e `_fazer_mosaico` localmente.
- A função principal `gerar_mosaicos_nao_georef` orquestra o processo em etapas.
"""

from __future__ import annotations

from typing import Iterable, List, Optional, Tuple
import os
import shutil
import gc
import cv2
import numpy as np

from .config import MosaicConfig
from ...utils.logger import logger


# ====================================================================
# FUNÇÕES PORTADAS DIRETAMENTE DO SCRIPT `mosaico_multi_grupos.py`
# ====================================================================

def _rootsift_descriptors(gray: np.ndarray) -> Tuple[Optional[list], Optional[np.ndarray]]:
    """Calcula descritores RootSIFT."""
    sift = cv2.SIFT_create()
    kps, desc = sift.detectAndCompute(gray, None)
    if desc is None:
        return kps, None
    # Normaliza L1 e aplica raiz quadrada
    desc /= (desc.sum(axis=1, keepdims=True) + 1e-7)
    desc = np.sqrt(desc)
    return kps, desc

def _encontrar_pontos_homologos(
    caminho_img1: str, 
    caminho_img2: str,
    resize_factor: float = 1.0
) -> Tuple[np.ndarray, int]:
    """
    Encontra a homografia entre duas imagens. Lógica idêntica ao script original.
    Retorna a matriz de homografia (H) e o número de inliers.
    """
    img1 = cv2.imread(caminho_img1)
    img2 = cv2.imread(caminho_img2)

    if img1 is None or img2 is None:
        logger.warning(f"Não foi possível carregar uma das imagens: {caminho_img1} ou {caminho_img2}")
        return None, 0
    
    gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)

    # Libera as imagens da memória após converter para escala de cinza
    del img1, img2
    gc.collect()
    
    # Redimensionamento opcional para acelerar a detecção de features
    if resize_factor != 1.0:
        fx = fy = resize_factor
        gray1 = cv2.resize(gray1, (0, 0), fx=resize_factor, fy=resize_factor, interpolation=cv2.INTER_AREA)
        gray2 = cv2.resize(gray2, (0, 0), fx=resize_factor, fy=resize_factor, interpolation=cv2.INTER_AREA)

    kps1, desc1 = _rootsift_descriptors(gray1)
    kps2, desc2 = _rootsift_descriptors(gray2)
    
    if desc1 is None or desc2 is None:
        return None, 0

    # Parâmetros do FLANN Matcher (idênticos ao script original)
    index_params = dict(algorithm=1, trees=5)
    search_params = dict(checks=50)
    matcher = cv2.FlannBasedMatcher(index_params, search_params)

    matches = matcher.knnMatch(desc1, desc2, k=2)

    # Filtro de ratio de Lowe
    bons_matches = [m[0] for m in matches if len(m) == 2 and m[0].distance < 0.75 * m[1].distance]

    # Mínimo de 10 bons matches para tentar a homografia (do script original)
    if len(bons_matches) < 10:
        return None, len(bons_matches)

    # Extrai pontos correspondentes
    pts1 = np.float32([kps1[m.queryIdx].pt for m in bons_matches])
    pts2 = np.float32([kps2[m.trainIdx].pt for m in bons_matches])

    # Desfaz o redimensionamento para as coordenadas dos pontos
    if resize_factor != 1.0:
        pts1 /= resize_factor
        pts2 /= resize_factor

    # Calcula a homografia com RANSAC
    H, mascara = cv2.findHomography(pts2, pts1, cv2.RANSAC, 5.0)

    if H is None or mascara is None:
        return None, len(bons_matches)

    n_inliers = np.sum(mascara)
    return H, n_inliers

def _fazer_mosaico(
    caminho_img1: str, 
    caminho_img2: str, 
    H: np.ndarray
):
    """Cria o mosaico a partir de duas imagens e a homografia. Lógica idêntica ao script original."""
    img1 = cv2.imread(caminho_img1)
    img2 = cv2.imread(caminho_img2)

    if img1 is None or img2 is None:
        logger.warning(f"Erro ao carregar imagens para criar mosaico: {caminho_img1} ou {caminho_img2}")
        return None

    if H is None:
        return None
    h1, w1 = img1.shape[:2]
    h2, w2 = img2.shape[:2]

    # Calcula o canvas do resultado
    corners_img2 = np.float32([[0, 0], [0, h2], [w2, h2], [w2, 0]]).reshape(-1, 1, 2)
    warped_corners = cv2.perspectiveTransform(corners_img2, H)
    corners = np.concatenate((warped_corners, np.float32([[0, 0], [0, h1], [w1, h1], [w1, 0]]).reshape(-1, 1, 2)), axis=0)

    [xmin, ymin] = np.int32(corners.min(axis=0).ravel() - 0.5)
    [xmax, ymax] = np.int32(corners.max(axis=0).ravel() + 0.5)
    translate = [-xmin, -ymin]
    H_translate = np.array([[1, 0, translate[0]], [0, 1, translate[1]], [0, 0, 1]])

    result = cv2.warpPerspective(img2, H_translate @ H, (xmax - xmin, ymax - ymin))

    # Mescla a imagem 1 sobre o resultado
    y_offset = translate[1]
    x_offset = translate[0]

    # Verifica limites válidos
    h_res, w_res = result.shape[:2]
    h1_end = min(y_offset + h1, h_res)
    w1_end = min(x_offset + w1, w_res)

    h_crop = h1_end - y_offset
    w_crop = w1_end - x_offset

    if h_crop <= 0 or w_crop <= 0:
        del img1, img2 # Libera memória
        gc.collect()
        return result  # Nada a mesclar ou sobreposição inválida

    img1_crop = img1[:h_crop, :w_crop]
    roi = result[y_offset:y_offset+h_crop, x_offset:x_offset+w_crop]
    
    # Máscara para evitar que pixels muito escuros (<=10) da img1 sobrescrevam o mosaico
    mascara = np.any(img1_crop > 10, axis=2)  # True onde algum canal é > 10
    roi[mascara] = img1_crop[mascara]

    del img1, img2
    gc.collect()
    return result

def _combinar_passada(
    imagens: List[str], 
    tmp_dir: str, 
    etapa: int, 
    resize_factor: float = 1.0
) -> List[str]:
    """Função que combina os pares em cada etapa. Lógica idêntica a `combinar_todos` do script original."""
    os.makedirs(tmp_dir, exist_ok=True)
    nova_lista = []
    imagens_usadas = set()

    logger.info(f"\n>> Etapa {etapa}: Processando {len(imagens)} imagens...")
    imagens_disponiveis = list(imagens)

    for i in range(len(imagens_disponiveis)):
        if imagens_disponiveis[i] in imagens_usadas:
            continue

        caminho1 = imagens_disponiveis[i]
        melhor_mosaico_data = None # Armazenará o array numpy do melhor mosaico
        melhor_n_matches = 0
        melhor_caminho2 = None

        for j in range(i + 1, len(imagens_disponiveis)):
            if imagens_disponiveis[j] in imagens_usadas:
                continue

            caminho2 = imagens_disponiveis[j]
            H, n_matches = _encontrar_pontos_homologos(caminho1, caminho2, resize_factor)
            logger.info(f"Par: {os.path.basename(caminho1)} vs {os.path.basename(caminho2)} -> {n_matches} inliers")

            # Se o par for válido (>= 50 inliers) e melhor que o anterior
            if H is not None and n_matches >= 50:
                if n_matches > melhor_n_matches:
                    # CRIA O MOSAICO IMEDIATAMENTE para validar
                    mosaico_atual = _fazer_mosaico(caminho1, caminho2, H)
                    if mosaico_atual is not None:
                        # Libera o mosaico anterior se existir
                        melhor_n_matches = n_matches
                        melhor_mosaico_data = mosaico_atual
                        melhor_caminho2 = caminho2
                    del mosaico_atual # Libera memória do mosaico temporário
                    gc.collect()

        if melhor_mosaico_data is not None:
            nome_mosaico = os.path.join(tmp_dir, f"mosaico_tmp_{etapa}_{len(nova_lista)}.jpg")
            cv2.imwrite(nome_mosaico, melhor_mosaico_data)
            nova_lista.append(nome_mosaico)
            imagens_usadas.add(caminho1)
            imagens_usadas.add(melhor_caminho2)
            print(f"✅ Mosaico: {os.path.basename(caminho1)} + {os.path.basename(melhor_caminho2)} ({melhor_n_matches} inliers)")
            del melhor_mosaico_data # Libera memória do melhor mosaico
            gc.collect()

    for caminho in imagens:
        if caminho not in imagens_usadas:
            destino = os.path.join(tmp_dir, f"solo_tmp_{etapa}_{len(nova_lista)}.jpg")
            shutil.copy2(caminho, destino)
            nova_lista.append(destino)
            print(f"🧩 Mantida isolada: {os.path.basename(caminho)}")

    return nova_lista

# ====================================================================
# FUNÇÃO PRINCIPAL DO PIPELINE (orquestrador)
# ====================================================================

def gerar_mosaicos_nao_georef(
    paths: Iterable[str], 
    pasta_saida: str, 
    cfg: MosaicConfig, 
    ext_final: str
) -> List[str]:
    """
    Orquestra a criação de mosaicos em etapas, usando a lógica portada do script original.
    """
    # --- Setup inicial ---
    os.makedirs(pasta_saida, exist_ok=True)
    tmp_dir_base = os.path.join(pasta_saida, "_tmp_mosaic")
    if os.path.exists(tmp_dir_base):
        shutil.rmtree(tmp_dir_base, ignore_errors=True)
    os.makedirs(tmp_dir_base, exist_ok=True)

    imagens = sorted([p for p in map(str, paths) if os.path.exists(p)])
    if not imagens:
        raise FileNotFoundError("Nenhuma imagem de entrada válida foi encontrada.")

    # Força a extensão para .jpg nos arquivos temporários, como no script original
    ext_temp = ".jpg"

    # --- Loop de etapas ---
    etapa = 1
    while len(imagens) > 1:
        num_antes = len(imagens)
        tmp_dir_etapa = os.path.join(tmp_dir_base, f"etapa_{etapa}")
        
        imagens = _combinar_passada(imagens, tmp_dir_etapa, etapa, resize_factor=1.0)
        
        if len(imagens) >= num_antes:
            logger.info("\n⚠️ Nenhuma nova combinação possível. Finalizando o processo.")
            break
        etapa += 1

    # --- Finalização e limpeza ---
    saidas_finais: List[str] = []
    if not ext_final.startswith("."): ext_final = "." + ext_final

    for i, caminho_tmp in enumerate(imagens, 1):
        nome_final = f"mosaico_final_{i}{ext_final}"
        caminho_final = os.path.join(pasta_saida, nome_final)
        shutil.copy2(caminho_tmp, caminho_final)
        saidas_finais.append(caminho_final)
        logger.info(f"💾 Resultado salvo: {nome_final}")

    shutil.rmtree(tmp_dir_base, ignore_errors=True)
    logger.info(f"\n✨ Processo concluído! {len(saidas_finais)} mosaicos finais gerados.")
    
    return saidas_finais

