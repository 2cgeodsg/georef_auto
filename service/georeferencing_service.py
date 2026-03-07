# service/georeferencing_service.py
# -*- coding: utf-8 -*-
import os
from typing import List, Tuple, Dict, Any

from PyQt5.QtWidgets import QProgressDialog, QApplication
from PyQt5.QtCore import Qt

# Usa apenas o pipeline funcional do core
from ..core.georeferencing import georeference_image
from ..utils.logger import logger
from ..utils.qgis_utils import add_raster_layer_to_qgis, get_area_in_square_km
from ..core.config import GeoreferencingConfig

from ..core.mosaic.config import MosaicConfig
from ..core.mosaic.pipeline import gerar_mosaicos_nao_georef

class GeoreferencingService:
    """Serviço de alto nível para operações de georreferenciamento."""

    def __init__(self, iface, config: GeoreferencingConfig | None = None):
            self.iface = iface
            self.config = config or GeoreferencingConfig()


    def georeference_single_image(self, image_path: str, polygon_geom, reference_layer, output_dir: str) -> Tuple[bool, str, str]:
        """
        Georreferencia uma única imagem.
        Parâmetros:
        - image_path: caminho da imagem de entrada
        - polygon_geom: geom do polígono de recorte/ajuste
        - reference_layer: camada de referência
        - output_dir: pasta onde salvar (UI só escolhe a pasta)
        Retorna:
        (ok, msg, output_path)
        """
        progress_dialog = None
        try:
            output_dir = (output_dir or "").strip().strip('"').strip("'")
            if not output_dir:
                output_dir = os.path.dirname(image_path)
            _, maybe_ext = os.path.splitext(output_dir)

            if maybe_ext.lower() in (".tif", ".tiff"):
                output_dir = os.path.dirname(output_dir)
            output_dir = os.path.normpath(output_dir)
            os.makedirs(output_dir, exist_ok=True)
            base_name = os.path.splitext(os.path.basename(image_path))[0]
            if base_name.endswith("_georef"):
                saida_nome = f"{base_name}.tif"
            else:
                saida_nome = f"{base_name}_georef.tif"

            output_path = os.path.join(output_dir, saida_nome)

            crs_authid = reference_layer.crs().authid() if hasattr(reference_layer, "crs") else "EPSG:3857"
            area_km2 = get_area_in_square_km(polygon_geom, crs_authid)
            if area_km2 > self.config.max_polygon_area_km2:
                return False, (f"Polígono muito grande ({area_km2:.1f} km²). "
                            f"Limite: {self.config.max_polygon_area_km2:.1f} km²."), output_path
            if area_km2 > self.config.warn_polygon_area_km2:
                logger.warning(f"Área grande: {area_km2:.1f} km² (pode demorar).")

            progress_dialog = QProgressDialog("Georeferencing image...", "Cancel", 0, 100, self.iface.mainWindow())
            progress_dialog.setWindowTitle("Georeferencing Progress")
            progress_dialog.show()

            def progress_callback(value, message):
                progress_dialog.setValue(value)
                progress_dialog.setLabelText(message)
                QApplication.processEvents()
                return not progress_dialog.wasCanceled()

            ok, msg = georeference_image(
                image_path=image_path,
                polygon_geom=polygon_geom,
                reference_layer=reference_layer,
                output_path=output_path,
                progress_callback=progress_callback,
                config=self.config,
            )

            return ok, msg, output_path

        except Exception as e:
            logger.error(f"Error in Georeferencing single image: {e}")
            return False, str(e), ""

        finally:
            if progress_dialog is not None:
                try:
                    progress_dialog.close()
                except Exception:
                    pass

    def georeference_batch(
        self,
        image_paths: List[str],
        polygon_geom,
        reference_layer,
        output_dir: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """Georreferencia várias imagens em lote"""
        report: Dict[str, Any] = {
            "total": len(image_paths),
            "successful": 0,
            "failed": 0,
            "results": []
        }

        try:
            total = len(image_paths)
            progress = QProgressDialog("Batch georeferencing...", "Cancel", 0, total * 100, self.iface.mainWindow())
            progress.setWindowTitle("Batch Georeferencing Progress")
            progress.setWindowModality(Qt.WindowModal)
            progress.show()

            for i, image_path in enumerate(image_paths):
                if progress.wasCanceled():
                    break

                base = i * 100
                progress.setValue(base)
                progress.setLabelText(f"Processing {os.path.basename(image_path)}...")
                QApplication.processEvents()

                base_name = os.path.splitext(os.path.basename(image_path))[0]
                output_path = os.path.join(output_dir, f"{base_name}_georef.tif")

                # Callback para “encaixar” a barra de 0–100 dentro do slot do item i
                def progress_callback(value: int, message: str):
                    progress.setValue(base + value)
                    progress.setLabelText(f"Processing {os.path.basename(image_path)}... {message}")
                    QApplication.processEvents()
                    return not progress.wasCanceled()

                ok, msg = georeference_image(
                    image_path=image_path,
                    polygon_geom=polygon_geom,
                    reference_layer=reference_layer,
                    output_path=output_path,
                    progress_callback=progress_callback
                )

                result = {
                    "image": os.path.basename(image_path),
                    "success": ok,
                    "message": msg,
                    "output_path": output_path if ok else None
                }
                report["results"].append(result)

                if ok:
                    report["successful"] += 1
                    # Opcional: carregar no QGIS automaticamente
                    try:
                        add_raster_layer_to_qgis(output_path, f"{base_name}_georef")
                    except Exception as e:
                        logger.warning(f"Falha ao adicionar raster ao QGIS: {e}")
                    # garante que o slot atinja 100
                    if not progress.wasCanceled():
                        progress.setValue(base + 100)
                        QApplication.processEvents()
                else:
                    report["failed"] += 1

            progress.setValue(total * 100)
            progress.close()
            return True, report

        except Exception as e:
            logger.error(f"Erro no georreferenciamento em lote: {e}")
            report["error"] = str(e)
            return False, report
    def create_non_georeferenced_mosaic(self, image_paths: list[str], output_path: str) -> tuple[bool, str]:
        try:
            if not image_paths:
                return False, "Nenhuma imagem selecionada."

            pasta_saida = output_path
            nome_base = "mosaico"
            ext = ".tif"  # sempre default para mosaicos

            os.makedirs(pasta_saida, exist_ok=True)  # garante que a pasta exista

            progress = QProgressDialog("Criando mosaico (não georreferenciado)...",
                                    "Cancelar", 0, 0, self.iface.mainWindow())
            progress.setWindowModality(Qt.WindowModal)
            progress.show()
            QApplication.processEvents()

            cfg = MosaicConfig()
            saidas = gerar_mosaicos_nao_georef(image_paths, pasta_saida, cfg, ext)
            progress.close()

            if not saidas:
                return False, "Não foi possível gerar mosaicos."

            # primeiro mosaico -> mosaico1.tif
            destino = os.path.join(pasta_saida, f"{nome_base}1{ext}")
            if os.path.abspath(saidas[0]) != os.path.abspath(destino):
                os.replace(saidas[0], destino)
                saidas[0] = destino

            # demais -> mosaico2.tif, mosaico3.tif, ...
            for idx, p in enumerate(saidas[1:], start=2):
                QApplication.processEvents()
                alvo = os.path.join(pasta_saida, f"{nome_base}{idx}{ext}")
                if os.path.abspath(p) != os.path.abspath(alvo):
                    try:
                        os.replace(p, alvo)
                        saidas[idx - 1] = alvo
                    except Exception:
                        pass

            # Mensagem mais clara
            grupos = len(saidas)
            msg = "Mosaico(s) criado(s):\n- " + "\n- ".join(saidas)
            if grupos > 1:
                msg += f"\nObservação: {grupos} grupos detectados; os arquivos estão separados."
            return True, msg

        except Exception as e:
            logger.exception("Erro ao criar mosaico não georreferenciado.")
            return False, f"Erro ao criar mosaico: {e}"
