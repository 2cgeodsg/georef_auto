# GeorefAuto Plugin

## Overview
GeorefAuto is a QGIS plugin for automatic georeferencing of aerial images using computer vision algorithms (RootSIFT, FLANN, and RANSAC). It allows you to georeference images by simply defining a bounding polygon that approximately contains the area where the image should be located.

## Key Features
1. **Batch Processing** - Process multiple images at once using the same bounding polygon
2. **Large Area Support** - Efficiently handle large bounding polygons (up to 3050 km²)
3. **Automatic Scale Recognition** - Automatically detects image scale regardless of zoom level
4. **User-Friendly Interface** - Intuitive UI with clear workflow

## Installation
1. Open QGIS
2. Go to Plugins → Manage and Install Plugins
3. Click on "Install from ZIP"
4. Browse to the GeorefAuto.zip file and click "Install Plugin"

## Requirements
- QGIS 3.0 or higher
- Python dependencies (automatically installed if missing):
  - OpenCV (cv2)
  - Rasterio
  - NumPy

## Usage
See the included documentation.html file for detailed usage instructions.
