# -*- coding: utf-8 -*-

# --------------------------------------------------------------------------
# --------------------------------------------------------------------------
# Clip_Attribute_Export.py
# Version: 0.1
# Date: 
# --------------------------------------------------------------------------
# --------------------------------------------------------------------------
#
# This Python toolbox is called by ArcGIS Pro and simultaneously clips and exports clipped table as an excel file

import arcpy

class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Toolbox"
        self.alias = "toolbox"

        # List of tool classes associated with this toolbox
        self.tools = [Tool]


class Tool(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Clip Attribute Export"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""

        # Layer that will be clipped
        Input1 = arcpy.Parameter(
        displayName="Input layer",
        name="Input1",
        datatype="GPFeatureLayer",
        parameterType="Required",
        direction="Input")

        # Layer that will be used to clip input layer
        Input2 = arcpy.Parameter(
        displayName="Clipping layer",
        name="Input2",
        datatype="GPFeatureLayer",
        parameterType="Required",
        direction="Input")

        # Clipped layer from clipping process
        Clip = arcpy.Parameter(
        displayName="Clipping output",
        name="Clip",
        datatype="GPFeatureLayer",
        parameterType="Required",
        direction="Output")

        # Attribute table of clipped layer converted into excel file
        Attribute = arcpy.Parameter(
        displayName="Attribute table",
        name="Attribute",
        datatype="File",
        parameterType="Derived",
        direction="Output")

        params = [Input1, Input2, Clip, Attribute]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""

        Input1 = parameters[0].valueAsText
        Input2 = parameters[1].valueAsText
        Clip = parameters[2].valueAsText
        Attribute = parameters[3].valueAsText
        
        # Clipping process
        arcpy.analysis.Clip(Input1, Input2, Clip, None)
        # Conversion process 
        # Excel file will be exported into folder where default GDB is found
        arcpy.conversion.TableToExcel(Clip, Attribute, "NAME", "CODE")

        return
