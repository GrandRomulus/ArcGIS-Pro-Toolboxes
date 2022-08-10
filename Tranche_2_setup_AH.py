import arcpy
import os
from distutils.dir_util import copy_tree

arcpy.env.workspace = r"FOLDER NAME"

#SETUP FOLDER - copy template, rename and copy into received files
def foldersetup(school):
    #copy folder template in
    copy_tree(arcpy.env.workspace + "/_Template", arcpy.env.workspace + "/" + school)
    #copy received files in
    copy_tree(arcpy.env.workspace + "/_Data/FromClient/Tranche2/" + school, arcpy.env.workspace + "/" + school + "/Data/From_Client")

#700m buffer from site
def buffer700(school):
    arcpy.AddMessage(school + " buffer")
    arcpy.Buffer_analysis(arcpy.env.workspace + "/" +school + "/Data/From_Client/SITE_POLY.shp",arcpy.env.workspace + "/" + school + "/Data/Boundary/700m_buffer", "700 Meters")

# set projection
def projection(school):
    arcpy.AddMessage(school + " check projection")
    mxdName = os.path.join(arcpy.env.workspace, school, r"BHA.mxd")
    mxd =  arcpy.mapping.MapDocument(mxdName)
    df = arcpy.mapping.ListDataFrames(mxd)[0]
    utm_zones = arcpy.mapping.ListLayers(mxd, 'utm_zones*', df)[0]
    site = arcpy.mapping.ListLayers(mxd, 'SITE_POLY*', df)[0]
    arcpy.management.SelectLayerByLocation(utm_zones, "INTERSECT", site)
    Zone = [row[0] for row in arcpy.da.SearchCursor(utm_zones,'ZONE')]
    global Projection
    Projection = ("GDA 1994 MGA Zone " + str(Zone[0]))
    del mxd

#zoom to 700m buffer
def BHAsetup(school):
    arcpy.AddMessage(school + " BHA zoom")
    mxdName = os.path.join(arcpy.env.workspace, school, r"BHA.mxd")
    mxd =  arcpy.mapping.MapDocument(mxdName)
    df = arcpy.mapping.ListDataFrames(mxd)[0]
    df.spatialReference = Projection
    lyr = arcpy.mapping.ListLayers(mxd, '700m_Buffer*', df)[0]
    ext = lyr.getExtent()
    df.extent = ext
    df.scale = df.scale*1.1
    global G_Extent
    G_Extent = df.extent
    mxd.save()
    del mxd    

def BFPLsetup(school):
    arcpy.AddMessage(school + " BFPL zoom")
    mxdName = os.path.join(arcpy.env.workspace, school, r"BFPL.mxd")
    mxd =  arcpy.mapping.MapDocument(mxdName)
    df = arcpy.mapping.ListDataFrames(mxd)[0]
    df.spatialReference = Projection
    df.extent = G_Extent
    mxd.save()
    del mxd

def LOCsetup(school):
    arcpy.AddMessage(school + " location zoom")
    mxdName = os.path.join(arcpy.env.workspace, school, r"Location.mxd")
    mxd =  arcpy.mapping.MapDocument(mxdName)
    df = arcpy.mapping.ListDataFrames(mxd)[0]
    df.spatialReference = Projection
    df.extent = G_Extent
    df2 = arcpy.mapping.ListDataFrames(mxd)[1]
    df2.spatialReference = Projection
    lyr2 = arcpy.mapping.ListLayers(mxd, 'SITE_POLY*', df)[0]
    ext2 = lyr2.getExtent()
    df2.extent = ext2
    df2.scale = df2.scale*100
    mxd.save()
    del mxd


for files in next(os.walk(r"FOLDER NAME"))[1]:
    arcpy.AddMessage("starting " + files)
    foldersetup(files)
    buffer700(files)
    projection(files)
    BHAsetup(files)
    BFPLsetup(files)
    LOCsetup(files)
    
