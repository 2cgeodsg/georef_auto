import subprocess
import sys

def verificar_dependencias():
    pacotes = {
        "cv2": "opencv-python",
        "rasterio": "rasterio",
        "numpy": "numpy"
    }

    for modulo, pacote in pacotes.items():
        try:
            __import__(modulo)
        except ImportError:
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", pacote])
            except Exception as e:
                try:
                    from qgis.PyQt.QtWidgets import QMessageBox
                    QMessageBox.critical(
                        None,
                        "Erro ao instalar dependência",
                        f"Não foi possível instalar '{pacote}'.\n\n"
                        f"Erro: {e}\n\n"
                        f"Instale manualmente com:\n    pip install {pacote}"
                    )
                except Exception:
                    print(f"[Plugin] Erro ao instalar '{pacote}': {e}")
