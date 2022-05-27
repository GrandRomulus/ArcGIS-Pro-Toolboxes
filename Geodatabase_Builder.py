# --------------------------------------------------------------------------
# --------------------------------------------------------------------------
# Geodatabase_Builder_DrChris.py
# Version: 0.1
# Date:
# Original Author:
# --------------------------------------------------------------------------
# --------------------------------------------------------------------------
#
# This code is called by ArcGIS Pro and allow you create 1 to 10X Geodatabases

# Import the libraries you will need
import os, arcpy
def gdbbuilder(gdbnames):
    """
    Create multiple geodatabases.   

    Parameters
    ----------
    gdbnames : String
        A string with ";" seperators exported from ArcGIS pro
    Returns
    -------
    None.

    """
    arcpy.AddMessage("Starting Geodatabase Builder")
    # Current directory to keep your geodatabases in the same location
    currentdir = os.getcwd()
    # Project name being extracted from directory for naming
    projectname = currentdir.split("\\")[-1]
    for gdbname in gdbnames.split(";"):
        # Creating a new geodatabase name on each cycle
        newgdbname = f"{projectname}_{gdbname}"
        # Creating the geodatabase!
        arcpy.management.CreateFileGDB(currentdir, newgdbname, "CURRENT")
        
# Getting the parameters from ArcGIS Pro too
gdbnames = arcpy.GetParameterAsText(0)
# Calling the functionS
gdbbuilder(gdbnames)