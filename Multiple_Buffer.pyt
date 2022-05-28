# -*- coding: utf-8 -*-

# --------------------------------------------------------------------------
# --------------------------------------------------------------------------
# Muiltple_Buffer.py
# Version: 0.1
# Date: 
# --------------------------------------------------------------------------
# --------------------------------------------------------------------------
#
# This Python toolbox is called by ArcGIS Pro and creates 100 m, 200 m and 300 m buffers for a given feature layer


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
        self.label = "Multiple Buffer"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""

        # Layer to be buffered
        Input = arcpy.Parameter(
        displayName="Feature Layer",
        name="Input",
        datatype="GPFeatureLayer",
        parameterType="Required",
        direction="Input")

        # 100 m buffer
        Buffer100 = arcpy.Parameter(
        displayName="100 m",
        name="Buffer100",
        datatype="GPFeatureLayer",
        parameterType="Required",
        direction="Output")
        
        # 200 m buffer
        Buffer200 = arcpy.Parameter(
        displayName="200 m",
        name="Buffer200",
        datatype="GPFeatureLayer",
        parameterType="Required",
        direction="Output")

        # 300 m buffer
        Buffer300 = arcpy.Parameter(
        displayName="300 m",
        name="Buffer300",
        datatype="GPFeatureLayer",
        parameterType="Required",
        direction="Output")

        params = [Input, Buffer100, Buffer200, Buffer300]
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
        Input = parameters[0].valueAsText
        Buffer100 = parameters[1].valueAsText
        Buffer200 = parameters[2].valueAsText
        Buffer300 = parameters[3].valueAsText

        arcpy.analysis.Buffer(Input, Buffer100, "100 Meters", "FULL", "ROUND", "NONE", None, "PLANAR")
        arcpy.analysis.Buffer(Input, Buffer200, "200 Meters", "FULL", "ROUND", "NONE", None, "PLANAR")
        arcpy.analysis.Buffer(Input, Buffer300, "300 Meters", "FULL", "ROUND", "NONE", None, "PLANAR")
        return
