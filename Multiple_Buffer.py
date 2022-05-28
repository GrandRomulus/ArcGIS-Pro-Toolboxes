# --------------------------------------------------------------------------
# --------------------------------------------------------------------------
# Multiple_Buffers.py
# Version: 0.1
# Date:
# --------------------------------------------------------------------------
# --------------------------------------------------------------------------
#
# This code is called by ArcGIS Pro and allows you to create 100, 200 and 300 Meter buffers

# Import statements
import arcpy

arcpy.AddMessage("Starting buffer...")
# Label as Feature Layer in Tool Properties > Parameters
Input = arcpy.GetParameterAsText(0)
# Label as 100 m in Tool Properties > Parameters
Buffer100 = arcpy.GetParameterAsText(1)
# Label as 200 m in Tool Properties > Parameters
Buffer200 = arcpy.GetParameterAsText(2)
# Label as 300 m in Tool Properties > Parameters
Buffer300 = arcpy.GetParameterAsText(3)

arcpy.analysis.Buffer(Input, Buffer100, "100 Meters", "FULL", "ROUND", "NONE", None, "PLANAR")
arcpy.analysis.Buffer(Input, Buffer200, "200 Meters", "FULL", "ROUND", "NONE", None, "PLANAR")
arcpy.analysis.Buffer(Input, Buffer300, "300 Meters", "FULL", "ROUND", "NONE", None, "PLANAR")