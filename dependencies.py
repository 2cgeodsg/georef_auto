import subprocess
import sys

def ensure_dependencies():
    """
    Check and install required dependencies for the plugin.
    """
    packages = {
        "cv2": "opencv-python",
        "rasterio": "rasterio",
        "numpy": "numpy"
    }
    # Garante que o pip tá instalado
    try:
        __import__("pip")
    except:
        try:
            subprocess.check_call([sys.executable, "-m", "pip"])
        except:
            try:
                subprocess.check_call([sys.executable, "-m", "ensurepip"])
                subprocess.check_call([sys.executable, "-m", "pip"])
            except Exception as e:
                try:
                    from qgis.PyQt.QtWidgets import QMessageBox
                    QMessageBox.critical(
                        None,
                        "Error installing dependency",
                        f"Cannot find or install 'pip'.\n\n"
                        f"Error: {e}\n\n"
                        f"Install manually with:\n    python -m ensurepip\n    OR\n    download and run 'get-pip.py'"
                    )
                except:
                    print(f"[Plugin] Cannot find or install 'pip': {e}")

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

if not ensure_dependencies():
    raise ImportError("Instalação do plugin falhou.")

import cv2
import rasterio
import numpy