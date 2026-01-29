# map_control.py

from qgis.utils import iface
from qgis.PyQt.QtCore import Qt

_original_interaction_state = {}

def fix_map_scale(scale=6000):
    canvas = iface.mapCanvas()
    _original_interaction_state["scale"] = canvas.scale()
    _original_interaction_state["enabled"] = canvas.isInteractive()

    canvas.setInteractive(False)
    canvas.zoomScale(scale)
    canvas.refresh()

def restore_map_interaction():
    canvas = iface.mapCanvas()
    if "scale" in _original_interaction_state:
        canvas.zoomScale(_original_interaction_state["scale"])
    if "enabled" in _original_interaction_state:
        canvas.setInteractive(_original_interaction_state["enabled"])
    canvas.refresh()
