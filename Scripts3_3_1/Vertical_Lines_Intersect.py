#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Cross Section Border Intersect Lines
# Created by Sarah Francis, Minnesota Geological Survey
# Created Date: July 2023
'''
This script creates vertical lines in cross section view where mapview 
polygons, lines, or points intersect cross section lines. The output lines
contain attributes from the input feature class.
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
    xsln = arcpy.GetParameterAsText(0)   #mapview xsln file
    xsec_id_field = arcpy.GetParameterAsText(1)  #et_id in xsln
    intersect_fc = arcpy.GetParameterAsText(2)  #polygon or line file to intersect with xsln. county boundary, faults, papg, etc.
    vertical_exaggeration = int(arcpy.GetParameterAsText(3))
    output_line_fc = arcpy.GetParameterAsText(4) 
    printit("Variables set with tool parameter inputs.")

else:
    # hard-coded parameters used for testing
    xsln = r'D:\Bedrock_Xsec_Scripting\Reference_grid_062923.gdb\xsln_diagonal' #mapview xsln file
    xsec_id_field = 'et_id' #et_id in xsln
    intersect_fc = r'D:\Bedrock_Xsec_Scripting\Vertical_line_intersect.gdb\polygon_input' #polygon or line file to intersect with xsln. county boundary, faults, papg, etc.
    vertical_exaggeration = 50
    output_line_fc = r'D:\Bedrock_Xsec_Scripting\Vertical_line_intersect.gdb\polygon_output' #output line file
    printit("Variables set with hard-coded parameters for testing.")

#Data QC

#check for invalid VE value
if vertical_exaggeration <= 0 :
    printerror("Error: Vertical Exaggeration must be greater than 0.")
    raise SystemExit

#%% 3 Read shape type of intersect_fc

desc = arcpy.Describe(intersect_fc)
shape = desc.shapeType

#%% 4 Intersect 
arcpy.env.overwriteOutput = True

printit("Intersecting with xsln and creating temporary file.")
#get directory where output will be saved
output_dir = os.path.dirname(output_line_fc)
#get filename of output
output_name = os.path.basename(output_line_fc)


#create name and path for temp output
output_fc_temp_multi = os.path.join(output_dir, output_name + "_temp_multi")

#create temporary 3D intersect file
if shape == "Polygon":
    arcpy.analysis.Intersect([intersect_fc, xsln], output_fc_temp_multi, 'ALL', '', 'LINE')
elif shape == "Polyline":
    arcpy.analysis.Intersect([xsln, intersect_fc], output_fc_temp_multi, 'ALL', '', 'POINT')
elif shape == "Point":
    arcpy.analysis.Intersect([xsln, intersect_fc], output_fc_temp_multi, 'ALL', '', 'POINT')
else:
    printerror("Input intersect file has invalid shape type.")

#convert multipart to singlepart
output_fc_temp1 = os.path.join(output_dir, output_name + "_temp1")
arcpy.management.MultipartToSinglepart(output_fc_temp_multi, output_fc_temp1)
#%% 5 Dissolve
#dissolve by all fields so that there is only one line segment inside a polygon
#no multipart features

#list all attribute fields
fields_list = arcpy.ListFields(output_fc_temp1)
field_name_list = []
#remove unnecessary fields
for field in fields_list:
    if field.name == "OBJECTID":
        fields_list.remove(field)
    elif field.name == "Shape":
        fields_list.remove(field)
    elif field.name == "FID":
        fields_list.remove(field)
    elif field.name == "Shape_Length":
        fields_list.remove(field)
    else: field_name_list.append(field.name)

output_fc_temp = os.path.join(output_dir, output_name + "_temp")
arcpy.management.Dissolve(output_fc_temp1, output_fc_temp, field_name_list, '', "SINGLE_PART")

#%% 6 Create unique id field for join later

arcpy.env.overwriteOutput = True

printit("Adding temporary join field.")
unique_id_field = 'unique_id'

try:
    arcpy.management.AddField(output_fc_temp, unique_id_field, 'LONG')
except:
    printit("Unable to add unique_id field. Field may already exist.")

if 'OBJECTID' in [field.name for field in arcpy.ListFields(output_fc_temp)]:
    arcpy.management.CalculateField(output_fc_temp, unique_id_field, "!OBJECTID!")
elif 'FID' in [field.name for field in arcpy.ListFields(output_fc_temp)]:
    arcpy.management.CalculateField(output_fc_temp, unique_id_field, "!FID!")
else:
    printerror("Error: input feature class does not contain OBJECTID or FID field. Conversion will not work without one of these fields.") 

#%% 7 Create empty line file and add fields

printit("Creating empty file for geometry creation.")
arcpy.management.CreateFeatureclass(output_dir, output_name, 'POLYLINE')
fields = [[xsec_id_field, 'TEXT'], [unique_id_field, 'LONG']]
arcpy.management.AddFields(output_line_fc, fields)

#%% 8 Convert geometry to cross section view and write to output file

printit("Creating 2d line geometry.")
#get shape type of temporary fc
desc = arcpy.Describe(output_fc_temp)
shape = desc.shapeType

with arcpy.da.SearchCursor(xsln, ['SHAPE@', xsec_id_field]) as xsln_cursor:
    for line in xsln_cursor:
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
        if shape == 'Polyline':
            with arcpy.da.SearchCursor(output_fc_temp, ['SHAPE@', unique_id_field], '"{0}" = \'{1}\''.format(xsec_id_field, xsec)) as cursor:
                for feature in cursor:
                    unique_id = feature[1]
                    #set top and bottom y coordinates for every x
                    #based on min and max elevations for the whole state
                    y_2d_1 = 0
                    y_2d_2 = 2500
                    line1_pointlist = []
                    line2_pointlist = []
                    x_list = []
                    #get geometry and convert to 2d space
                    for vertex in feature[0].getPart(0):
                        #mapview true coordinates
                        x_mp = vertex.X
                        y_mp = vertex.Y
                        xy_mp = arcpy.Point(x_mp, y_mp)    
                        #measure on line to find distance from start of xsln                    
                        x_2d_raw = arcpy.Polyline.measureOnLine(xsln_geometry, xy_mp)
                        #convert to feet and divide by vertical exaggeration to squish the x axis
                        x_2d = (x_2d_raw/0.3048)/vertical_exaggeration
                        #make list of x coordinates in line
                        x_list.append(x_2d)
                    #create 2 vertical lines, one at each endpoint of the line
                    pt1 = arcpy.Point(x_list[0], y_2d_1)
                    pt2 = arcpy.Point(x_list[0], y_2d_2)
                    pt3 = arcpy.Point(x_list[-1], y_2d_1)
                    pt4 = arcpy.Point(x_list[-1], y_2d_2)
                    line1_pointlist.append(pt1)
                    line1_pointlist.append(pt2)
                    line2_pointlist.append(pt3)
                    line2_pointlist.append(pt4)
                    line1_array = arcpy.Array(line1_pointlist)
                    line1_geometry = arcpy.Polyline(line1_array)
                    line2_array = arcpy.Array(line2_pointlist)
                    line2_geometry = arcpy.Polyline(line2_array)
                    #create geometry into output file
                    with arcpy.da.InsertCursor(output_line_fc, ['SHAPE@', xsec_id_field, unique_id_field]) as cursor2d:
                        cursor2d.insertRow([line1_geometry, xsec, unique_id])
                        cursor2d.insertRow([line2_geometry, xsec, unique_id])  
                        
        if shape == 'Point':
            with arcpy.da.SearchCursor(output_fc_temp, ['SHAPE@X', 'SHAPE@Y', unique_id_field], '"{0}" = \'{1}\''.format(xsec_id_field, xsec)) as cursor:
                for feature in cursor:
                    unique_id = feature[2]
                    #set top and bottom y coordinates for every x
                    #based on min and max elevations for the whole state
                    y_2d_1 = 0
                    y_2d_2 = 2500
                    line1_pointlist = []
                    #get geometry and convert to 2d space
                    x_mp = feature[0]
                    y_mp = feature[1]
                    xy_mp = arcpy.Point(x_mp, y_mp)    
                    #measure on line to find distance from start of xsln                    
                    x_2d_raw = arcpy.Polyline.measureOnLine(xsln_geometry, xy_mp)
                    #convert to feet and divide by vertical exaggeration to squish the x axis
                    x_2d = (x_2d_raw/0.3048)/vertical_exaggeration
                    #create 2 vertical lines, one at each endpoint of the line
                    pt1 = arcpy.Point(x_2d, y_2d_1)
                    pt2 = arcpy.Point(x_2d, y_2d_2)
                    line1_pointlist.append(pt1)
                    line1_pointlist.append(pt2)
                    line1_array = arcpy.Array(line1_pointlist)
                    line1_geometry = arcpy.Polyline(line1_array)
                    #create geometry into output file
                    with arcpy.da.InsertCursor(output_line_fc, ['SHAPE@', xsec_id_field, unique_id_field]) as cursor2d:
                        cursor2d.insertRow([line1_geometry, xsec, unique_id])
                    
                     
#%% 9 Join fields

printit("Joining fields from input to output.")
# list fields in input feature class
join_fields = []
in_fc_fields_all = arcpy.ListFields(output_fc_temp)
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

arcpy.management.JoinField(output_line_fc, unique_id_field, output_fc_temp, unique_id_field, join_fields)
                 
#%% 10 Delete temporary files

printit("Deleting temporary files.")
try: arcpy.management.Delete(output_fc_temp_multi)
except: printit("Unable to delete temporary file {0}".format(output_fc_temp_multi))
try: arcpy.management.Delete(output_fc_temp)
except: printit("Unable to delete temporary file {0}".format(output_fc_temp))
try: arcpy.management.Delete(output_fc_temp1)
except: printit("Unable to delete temporary file {0}".format(output_fc_temp1))
try: arcpy.management.DeleteField(output_line_fc, unique_id_field)
except: printit("Unable to delete unique_id field.")

#%% 11 Record and print tool end time
toolend = datetime.datetime.now()
toolelapsed = toolend - toolstart
printit('Tool completed at {0}. Elapsed time: {1}. Youre a wizard!'.format(toolend, toolelapsed))