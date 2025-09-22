import re
from arcgis.gis import GIS
from datetime import datetime
import pandas as pd
import numpy as np
import os
import glob
import arcpy
import sys
import time

# Access Geoportal login through ArcGIS Pro
gis = GIS("pro")

# Function for sanitising file name
def sanitize_filename(filename):
    # Replace all non-alphanumeric characters except '_' with '_'
    sanitized = re.sub(r'[^a-zA-Z0-9]', '_', filename)
    filename_cleaned = sanitized.replace(" ", "_").replace("-", "_")
    return filename_cleaned

def generate_date():
    # Get today's date without the time component
    return datetime.now().date().strftime("%Y%m%d")

# Function that backsup Feature Services. Run separately after above process has been performed. 
def backup_feature_layers():
    """Backs up feature service layers into a geodatabase and saves the ArcGIS project."""
    
    # Output save location for generated backup layers. Insert reference GDB as needed.
    gdb = r""
    
    # For accessing ArcGIS Project
    project = arcpy.mp.ArcGISProject("current")
    
    # List of feature services for Metro Growth project. Insert links as needed.
    layers = {
        "Traffic Status": "",
        "Construction Status": "",
        "Progress Slider": "",
    }
    
    # Generate date for process
    date = generate_date()
    
    # Looping through URL dictionary list
    for key, value in layers.items():
        layername = sanitize_filename(key)
        print(f"Backing up: {layername}")
        
        # Define backup layer name
        backup_layer = f"{layername}_{date}"
        
        # Perform backup
        try:
            arcpy.conversion.FeatureClassToFeatureClass(value, gdb, backup_layer)
            print(f"{layername} has been backed up successfully.")
        except Exception as e:
            print(f"Error backing up {layername}: {e}")
    
    # Save the project
    project.save()
    print("Project saved after backup.")

# Calling function for backing up layers
backup_feature_layers()
