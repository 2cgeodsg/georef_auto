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

    for module, package in packages.items():
        try:
            __import__(module)
        except ImportError:
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            except Exception as e:
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
