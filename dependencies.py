import subprocess
import sys

def check_dependencies():
    """
    Check and install required dependencies for the plugin.
    """
    packages = {
        "cv2": "opencv-python",
        "rasterio": "rasterio",
        "numpy": "numpy"
    }
    dependencies_all_ok = True

    for module, package in packages.items():
        try:
            __import__(module)
        except ImportError:
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            except Exception as e:
                dependencies_all_ok = False
                try:
                    from qgis.PyQt.QtWidgets import QMessageBox
                    QMessageBox.critical(
                        None,
                        "Error installing dependency",
                        f"Could not install '{package}'.\n\n"
                        f"Error: {e}\n\n"
                        f"Install manually with:\n    pip install {package}"
                    )
                except Exception:
                    print(f"[Plugin] Error installing '{package}': {e}")
    return dependencies_all_ok

if not check_dependencies():
    raise ImportError("Instalação do plugin falhou.")

import cv2
import rasterio
import numpy