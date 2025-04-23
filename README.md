# Georreferenciamento Automático

Plugin para QGIS que permite georreferenciar imagens antigas automaticamente com base em uma imagem de referência já georreferenciada e um polígono delimitador desenhado sobre ela.

## Funcionalidades

- Carregamento de imagem não georreferenciada;
- Seleção de imagem base entre as camadas raster abertas no QGIS;
- Desenho manual do polígono delimitador da área estimada;
- Georreferenciamento automático por detecção e pareamento de feições locais usando **RootSIFT + FLANN + RANSAC**;
- Exportação da imagem georreferenciada em formato GeoTIFF;
- Detecção automática e instalação de dependências via `pip`.

---

## Dependências

Este plugin depende das seguintes bibliotecas Python externas:

- `opencv-python`
- `numpy`
- `rasterio`

Essas bibliotecas são instaladas automaticamente na primeira execução. Caso a instalação automática falhe (por exemplo, por falta de permissões), será exibida uma mensagem com instruções para instalação manual.

### Instalação Manual (se necessário)

Se você precisar instalar manualmente as dependências, use os comandos abaixo no terminal:

use o QGIS LTR 3.40.6

abra o OSGeo4W Shell e rode o comando:
python3 -m pip install opencv-python rasterio numpy

depois verifique se foi instalado corretamente com o comando:
python -c "import cv2; print(cv2.__version__)"
---

## Requisitos

- QGIS 3.10 ou superior (recomendado: QGIS 3.22+)
- Python 3.7+ com suporte a `pip`

---

## Como usar

1. Abra o QGIS e ative o plugin "Georreferenciamento Automático".
2. Carregue a imagem a ser georreferenciada.
3. Selecione uma camada raster de referência.
4. Desenhe um polígono delimitador da área estimada de sobreposição.
5. Clique em "Executar georreferenciamento" para gerar uma nova imagem georreferenciada.