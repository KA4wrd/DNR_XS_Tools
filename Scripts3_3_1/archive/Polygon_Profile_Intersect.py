#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Polygon and Cross Section Profile Intersect
# Created by Sarah Francis, Minnesota Geological Survey
# Created Date: June 2023
'''
This script will intersect a polygon file with a cross section profile. There
will be two outputs: a line file that traces the profile surface and is
attributed based on polygon attributes, and a point file everywhere there is a
polygon intersection. The outputs can be used to view bedrock geology polygons
in cross section view.
'''

#%% 1 Import modules

import arcpy
import os
import sys
import datetime

# Record tool start time
toolstart = datetime.datetime.now()

# Define print statement function for testing and compiled geoprocessing tool

def printit(message):
    if (len(sys.argv) > 1):
        arcpy.AddMessage(message)
    else:
        print(message)
        
        
def printerror(message):
    if (len(sys.argv) > 1):
        arcpy.AddError(message)
    else:
        print(message)

# Define file exists function and field exists function

def FileExists(file):
    if not arcpy.Exists(file):
        printerror("Error: {0} does not exist.".format(os.path.basename(file)))
    
def FieldExists(dataset, field_name):
    if field_name in [field.name for field in arcpy.ListFields(dataset)]:
        return True
    else:
        printerror("Error: {0} field does not exist in {1}."
                .format(field_name, os.path.basename(dataset)))

#%% 2 Set parameters to work in testing and compiled geopocessing tool

if (len(sys.argv) > 1):
    profiles_3d = arcpy.GetParameterAsText(0)  #raster profiles IN 3D (not xsec view). These are created by the profile tool.
    xsln_file = arcpy.GetParameterAsText(1) 
    xsec_id_field = arcpy.GetParameterAsText(2)  #cross section ID in surface profiles, must be text type
    polygons_orig = arcpy.GetParameterAsText(3)  #polygons to intersect with profile
    vertical_exaggeration = int(arcpy.GetParameterAsText(4))
    output_dir = arcpy.GetParameterAsText(5)  #output geodatabase
    printit("Variables set with tool parameter inputs.")

else:
    # hard-coded parameters used for testing
    profiles_3d = r'D:\Bedrock_Xsec_Scripting\Raster_profiles_062823.gdb\topo_grid_bedrock_profiles3d' #raster profiles IN 3D (not xsec view). These are created by the profile tool.
    xsln_file = r'D:\Bedrock_Xsec_Scripting\Reference_grid_062923.gdb\xsln_diagonal'
    xsec_id_field = 'et_id' #cross section ID in surface profiles, must be text type
    polygons_orig = r'D:\Bedrock_Xsec_Scripting\Polygon_intersect_063023.gdb\sgpg' #surficial geology polygons
    vertical_exaggeration = 50
    output_dir = r'D:\Bedrock_Xsec_Scripting\Polygon_intersect_063023.gdb' #output geodatabase
    printit("Variables set with hard-coded parameters for testing.")

#%% 3 Data QC

#check to make sure profiles are 3d, not cross section view
desc = arcpy.Describe(profiles_3d)
if desc.hasZ == False:
    printerror("!!ERROR!! Surface profiles do not have z 3D geometry. Select 3D profiles for this parameter and try again.")

#%% 4 Create temporary polygon file and adding unique ID field to use for join later

arcpy.env.overwriteOutput = True

printit("Creating temporary copy of polygon file.")
input_name = os.path.basename(polygons_orig)
arcpy.conversion.FeatureClassToFeatureClass(polygons_orig, output_dir, input_name + "_temp")
polygons = os.path.join(output_dir, input_name + "_temp")

printit("Adding temporary join field.")
unique_id_field = 'unique_id'

try:
    arcpy.management.AddField(polygons, unique_id_field, 'LONG')
except:
    printit("Unable to add unique_id field. Field may already exist.")

if 'OBJECTID' in [field.name for field in arcpy.ListFields(polygons)]:
    arcpy.management.CalculateField(polygons, unique_id_field, "!OBJECTID!")
elif 'FID' in [field.name for field in arcpy.ListFields(polygons)]:
    arcpy.management.CalculateField(polygons, unique_id_field, "!FID!")
else:
    printerror("Error: input feature class does not contain OBJECTID or FID field. Conversion will not work without one of these fields.") 


#%% 5 Intersect polygons with 3D surface profiles and create line

printit("Intersecting temp polygons with 3d profiles and creating temporary line file.")

#get filename of output
poly_filename = os.path.basename(polygons_orig)
output_name = poly_filename + "_intersect_lines_" + str(vertical_exaggeration) +  "x"
output_line_fc = os.path.join(output_dir, output_name)

#create name and path for temp output
output_line_fc_temp_multi = os.path.join(output_dir, output_name + "_temp_line_3d_multi")
#create temporary 3D intersect file
arcpy.analysis.Intersect([profiles_3d, polygons], output_line_fc_temp_multi, 'NO_FID', '', 'LINE')
#convert multipart to singlepart
output_line_fc_temp = os.path.join(output_dir, output_name + "_temp_line_3d")
arcpy.management.MultipartToSinglepart(output_line_fc_temp_multi, output_line_fc_temp)

#%% 6 Create empty line file and add fields

printit("Creating empty line file for geometry creation.")
arcpy.management.CreateFeatureclass(output_dir, output_name, 'POLYLINE')
arcpy.management.AddField(output_line_fc, xsec_id_field, 'TEXT')
arcpy.management.AddField(output_line_fc, unique_id_field, 'LONG')

#%% 7 Convert geometry to cross section view and write to output file

printit("Creating 2d line geometry.")

with arcpy.da.SearchCursor(xsln_file, ['SHAPE@', xsec_id_field]) as xsln:
    for line in xsln:
        xsec = line[1]
        printit("Working on line {0}".format(xsec))
        pointlist = []
        for vertex in line[0].getPart(0):
            # Creates a polyline geometry object from xsln vertex points.
            # Necessary for MeasureOnLine method used later.
            point = arcpy.Point(vertex.X, vertex.Y)
            pointlist.append(point)
        array = arcpy.Array(pointlist)
        xsln_geometry = arcpy.Polyline(array)
        #search cursor to get geometry of 3D profile in this line
        with arcpy.da.SearchCursor(output_line_fc_temp, ['SHAPE@', xsec_id_field, unique_id_field], '"{0}" = \'{1}\''.format(xsec_id_field, xsec)) as cursor:
            for line in cursor:
                unique_id = line[2]
                line_pointlist = []
                #get geometry and convert to 2d space
                for vertex in line[0].getPart(0):
                    #mapview true coordinates
                    x_mp = vertex.X
                    y_mp = vertex.Y
                    z_mp = vertex.Z
                    xy_mp = arcpy.Point(x_mp, y_mp)    
                    #measure on line to find distance from start of xsln                    
                    x_2d_raw = arcpy.Polyline.measureOnLine(xsln_geometry, xy_mp)
                    #convert to feet and divide by vertical exaggeration to squish the x axis
                    x_2d = (x_2d_raw/0.3048)/vertical_exaggeration
                    #y coordinate in 2d space is the same as true elevation (z)
                    y_2d = z_mp
                    xy_2d = arcpy.Point(x_2d, y_2d)
                    #add to list of points
                    line_pointlist.append(xy_2d)
                #create array and geometry, add geometry to output file
                line_array = arcpy.Array(line_pointlist)
                line_geometry = arcpy.Polyline(line_array)
                with arcpy.da.InsertCursor(output_line_fc, ['SHAPE@', xsec_id_field, unique_id_field]) as cursor2d:
                    cursor2d.insertRow([line_geometry, xsec, unique_id])
                     
#%% 8 Delete temporary files

printit("Deleting temporary line files.")
try: arcpy.management.Delete(output_line_fc_temp_multi)
except: printit("Unable to delete temporary file {0}".format(output_line_fc_temp_multi))
try: arcpy.management.Delete(output_line_fc_temp)
except: printit("Unable to delete temporary file {0}".format(output_line_fc_temp))

#%% 9 Create empty point file and add fields
arcpy.env.overwriteOutput = True

#get filename of output
output_name = poly_filename + "_intersect_points_" + str(vertical_exaggeration) +  "x"
output_point_fc = os.path.join(output_dir, output_name)

printit("Creating empty point file for geometry creation.")
arcpy.management.CreateFeatureclass(output_dir, output_name, 'POINT')
arcpy.management.AddField(output_point_fc, xsec_id_field, 'TEXT')
arcpy.management.AddField(output_point_fc, unique_id_field, 'LONG')

#%% 10 Convert geometry to cross section view and write to output file

printit("Creating 2d point geometry.")

#create 2D point geometry at ends of lines for the line file just created.
with arcpy.da.SearchCursor(output_line_fc, ['SHAPE@', xsec_id_field, unique_id_field]) as cursor:
    for line in cursor:
        geom = line[0]
        xsec = line[1]
        unique_id = line[2]
        start = geom.firstPoint
        end = geom.lastPoint
        with arcpy.da.InsertCursor(output_point_fc, ['SHAPE@', xsec_id_field, unique_id_field]) as cursor2d:
            cursor2d.insertRow([start, xsec, unique_id])
            cursor2d.insertRow([end, xsec, unique_id])

#%% 11 Join fields to line and point files

printit("Joining fields from input to output.")
# list fields in input feature class
join_fields = []
in_fc_fields_all = arcpy.ListFields(polygons)
for field in in_fc_fields_all:
    name = field.name
    join_fields.append(name)

#remove redundant fields from list
#join_fields.remove(xsec_id_field)
join_fields.remove(unique_id_field)
if "Shape" in join_fields:
    join_fields.remove("Shape")
if "OBJECTID" in join_fields:
    join_fields.remove("OBJECTID")
if "FID" in join_fields:
    join_fields.remove("FID")
if "Shape_Length" in join_fields:
    join_fields.remove("Shape_Length")
if "Shape_Area" in join_fields:
    join_fields.remove("Shape_Area")
if "TARGET_FID" in join_fields:
    join_fields.remove("TARGET_FID")
if "Join_Count" in join_fields:
    join_fields.remove("Join_Count")
if "et_id" in join_fields:
    join_fields.remove("et_id")

arcpy.management.JoinField(output_line_fc, unique_id_field, polygons, unique_id_field, join_fields)
arcpy.management.JoinField(output_point_fc, unique_id_field, polygons, unique_id_field, join_fields)

#%% 12 Delete temp files and fields

try: arcpy.management.Delete(polygons)
except: printit("Unable to delete temporary file {0}".format(polygons))
try: arcpy.management.DeleteField(output_line_fc, unique_id_field)
except: printit("Unable to delete temp unique id field from {0}.".format(output_line_fc))
try: arcpy.management.DeleteField(output_point_fc, unique_id_field)
except: printit("Unable to delete temp unique id field from {0}.".format(output_point_fc))

#%% 13 Record and print tool end time
toolend = datetime.datetime.now()
toolelapsed = toolend - toolstart
printit('Tool completed at {0}. Elapsed time: {1}. Youre a wizard!'.format(toolend, toolelapsed))