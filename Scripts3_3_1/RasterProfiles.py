#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Raster Profiles
# Coded by Sarah Francis, Minnesota Geological Survey
# Created Date: June 2023
# Edited by Kelsey Forward, MN DNR
# Last Edit Date: October 2024
#       4/29/2024: Deleted 3D output files.
#       11/5/2024: Added descriptive error messages, raster name field, and merge option
'''
This script creates profiles from raster grids and map view cross section lines.
Tool can accept multiple raster surfaces, and outputs are labeled with raster
name. Outputs are 2-dimensional profiles that can be viewed in 2d cross sectional space.
'''

# %% 1 Import modules and define functions

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

# %% 2 Set parameters to work in testing and compiled geopocessing tool

if (len(sys.argv) > 1):
    #parameters retrieved by geoprocessing tool
    output_gdb_location = arcpy.GetParameterAsText(0) #output gdb
    rasters_input = arcpy.GetParameterAsText(1) #input raster surfaces, MUST BE IN FEET
    xsln_file_orig = arcpy.GetParameterAsText(2)
    xsln_etid_field = arcpy.GetParameterAsText(3)
    vertical_exaggeration = int(arcpy.GetParameterAsText(4))
    merge_boolean = arcpy.GetParameter(5) #check for merged output file
    printit("Variables set with tool parameter inputs.")

else:
    # hard-coded parameters used for testing
    rasters_input = 'D:/DakotaSandModel/TINmodel_110122/SandModeling_TIN.gdb/topo_grid_surface;D:/DakotaSandModel/TINmodel_110122/SandModeling_TIN.gdb/topo_grid_bedrock' #input raster surfaces
    xsln_file_orig = r'D:\DakotaSandModel\TINmodel_110122\diagonal_test.gdb\xsln_diagonal'
    xsln_etid_field = 'et_id' #must be text data type
    output_gdb_location = r'D:\Bedrock_Xsec_Scripting\Raster_profiles_062823.gdb' #output gdb
    vertical_exaggeration = int(50)
    printit("Variables set with hard-coded parameters for testing.")
    
# %% 2A Data QC

#determine if input cross section line file is empty
xsln_count_result = arcpy.management.GetCount(xsln_file_orig)
xsln_count = int(xsln_count_result[0])
if xsln_count == 0:
    printerror("Warning: cross section line file is empty. Tool will not run correctly.")

#determine if input cross section lines have multipart features
multipart = False
with arcpy.da.SearchCursor(xsln_file_orig, ["SHAPE@"]) as cursor:
    for row in cursor:
        if row[0].isMultipart:
            multipart = True
            break
if multipart:
    printerror("Warning: cross section file contains multipart features. Continuing may result in errors. To avoid errors, convert multipart feature to single part.")

#check that etid field does not match reserved fields
reserved_fields = ["OBJECTID", "SHAPE", "Shape", "Shape_Length"]
for name in reserved_fields:
    if name in xsln_etid_field:
        printerror("Error: Cannot use reserved fields OBJECTID, SHAPE, or Shape_Length for cross section ID field. Choose a different field.")
        raise SystemExit

#check for invalid VE value
if vertical_exaggeration <= 0 :
    printerror("Error: Vertical Exaggeration must be greater than 0.")
    raise SystemExit
#
# %% 3 Set up raster surfaces list

rasters_list = rasters_input.split(";")

#check raster names for invalid characters
for raster in rasters_list:
    if raster.isalnum() == False :
        printerror("Error: A raster name contains non-alphanumeric characters. Rename raster in Contents pane without using spaces or special characters.")
        raise SystemExit

# %% 4 Set spatial reference based on xsln file

spatialref = arcpy.Describe(xsln_file_orig).spatialReference
if spatialref.name == "Unknown":
    printerror("{0} file has an unknown spatial reference. Continuing may result in errors.".format(os.path.basename(xsln_file_orig)))
else:
    printit("Spatial reference set as {0} to match {1} file.".format(spatialref.name, os.path.basename(xsln_file_orig)))

#Set 2d spatial reference
spatialref_2d = spatialref

# %% 5 define and add fields needed in 2d xsec view output
#fields_2d = [[xsln_etid_field, 'TEXT']]
fields_2d = [[xsln_etid_field, 'TEXT'],['raster_name', 'TEXT']]
                                      
# list fields to be joined after geometry creation
xsln_fields = arcpy.ListFields(xsln_file_orig)
xsln_field_names = []
for field in xsln_fields:
    name = field.name
    xsln_field_names.append(name)

#list fields not to be joined if they exist  
#etid field is already in the file, so it won't need to be joined again  
fields_no_join = [xsln_etid_field, "OBJECTID", "Shape", "Join_Count", "TARGET_FID", "Shape_Length"]

for name in fields_no_join:
    if name in xsln_field_names:
        xsln_field_names.remove(name)

#######create empty output file for merged profiles if boolean is True
if merge_boolean == True:
    merged_profiles_2d_name = "all_profiles_2d" + "_" + str(vertical_exaggeration) + "x"
    merged_profiles_2d = os.path.join(output_gdb_location, merged_profiles_2d_name)
    arcpy.management.CreateFeatureclass(output_gdb_location, merged_profiles_2d_name, 'POLYLINE', '', 'DISABLED', 'DISABLED')

#%% 6 Create 3D profiles from input raster surface
for raster in rasters_list:
    name = os.path.basename(raster)
    printit("Creating 3d profiles for {0} raster surface.".format(name))
    # Use interpolate shape to create 3d profiles along xs lines
    profiles_3d_multi = os.path.join(output_gdb_location, name + "_profiles3d_multi")
    arcpy.ddd.InterpolateShape(raster, xsln_file_orig, profiles_3d_multi)
    # Convert to single part in case there was a gap in the raster
    printit("Converting multipart 3d profiles into single part for {0} raster surface.".format(name))
    profiles_3d = os.path.join(output_gdb_location, name + "_profiles3d")
    arcpy.management.MultipartToSinglepart(profiles_3d_multi, profiles_3d)
    # Delete multipart profiles
    printit("Deleting multipart profiles file for {0} raster surface.".format(name))
    arcpy.management.Delete(profiles_3d_multi)
    
    # Create empty feature dataset for storing 3d profiles by xs number. Necessary for 2d geometry loop below.
    printit("Creating feature dataset for storing 3d profiles by cross section number for {0} raster surface.".format(name))
    profiles_3d_byxsec = os.path.join(output_gdb_location, name + "profiles3d_byxsec")
    arcpy.management.CreateFeatureDataset(output_gdb_location, name + "profiles3d_byxsec", spatialref)

# Convert 3D xsln's to 2D view
    # Create empty 2d profiles file
    printit("Creating empty 2d profiles file for geometry creation for {0} surface.".format(name))
    if merge_boolean == True:
        profiles_2d = merged_profiles_2d
        # Add fields to empty 2d profiles file
        arcpy.management.AddFields(profiles_2d, fields_2d)
    else:
        profiles_2d_name = name + "_profiles2d" + "_" + str(vertical_exaggeration) + "x"
        profiles_2d = os.path.join(output_gdb_location, profiles_2d_name)
        arcpy.management.CreateFeatureclass(output_gdb_location, profiles_2d_name, 'POLYLINE', '', 'DISABLED', 'DISABLED')
        # Add fields to empty 2d profiles file
        arcpy.management.AddFields(profiles_2d, fields_2d)
    #populate raster name field
    raster_name = name
   
# Convert to 2d view and write geometry
    printit("Starting 2D geometry creation for {0} raster surface.".format(name))
    with arcpy.da.SearchCursor(xsln_file_orig, ['OID@', 'SHAPE@', xsln_etid_field]) as xsln:
        for line in xsln:
            et_id = line[2]
            xsln_pointlist = []
            for apex in line[1].getPart(0):
                # Creates a polyline geometry object from xsln vertex points.
                # Necessary for MeasureOnLine method used later.
                point = arcpy.Point(apex.X, apex.Y)
                xsln_pointlist.append(point)
            xsln_array = arcpy.Array(xsln_pointlist)
            xsln_geometry = arcpy.Polyline(xsln_array)
            # Create a new 3d profile file with only line associated with current xsln
            profile_by_xs_file = os.path.join(profiles_3d_byxsec, "{0}_{1}".format(xsln_etid_field, et_id))
            arcpy.analysis.Select(profiles_3d, profile_by_xs_file, '"{0}" = \'{1}\''.format(xsln_etid_field, et_id))
            printit("Writing 2D geometry for profile associated with xsec {0} on {1} surface.".format(et_id, name))
            with arcpy.da.SearchCursor(profile_by_xs_file, ['OID@', 'SHAPE@', xsln_etid_field]) as profile:
                for feature in profile:
                    et_id = feature[2]
                    profile_pointlist = []
                    # Convert vertices into 2d space and put them in an array
                    for vertex in feature[1].getPart(0):
                        xy_mapview = arcpy.Point(vertex.X, vertex.Y)
                        x_2d_meters = xsln_geometry.measureOnLine(xy_mapview)
                        x_2d_feet = x_2d_meters/0.3048
                        x_2d = x_2d_feet/vertical_exaggeration
                        y_2d = vertex.Z
                        xy_xsecview = arcpy.Point(x_2d, y_2d)
                        profile_pointlist.append(xy_xsecview)
                    profile_array = arcpy.Array(profile_pointlist)
                    profile_polyline = arcpy.Polyline(profile_array)
                    # Use Update cursor to write geometry to new file
                    with arcpy.da.InsertCursor(profiles_2d, ['SHAPE@', xsln_etid_field, 'raster_name']) as cursor2d:
                        cursor2d.insertRow([profile_polyline, et_id, name])
    # Delete temporary feature dataset
    printit("Deleting temporary feature dataset for {0} raster surface.".format(name))
    try:
        arcpy.management.Delete(profiles_3d_byxsec)
    except:
        printit("Unable to delete temporary feature dataset.")
    printit("Deleting 3D files.")
    try:
        arcpy.management.Delete(profiles_3d)
    except:
        printit("Unable to delete {0}.".format(profiles_3d))
    
    # join other fields that are in xsln file
    arcpy.management.JoinField(profiles_2d, xsln_etid_field, xsln_file_orig, xsln_etid_field, xsln_field_names)

if merge_boolean == True: 
    arcpy.management.DeleteField(profiles_2d,["OBJECTID", "Shape", "Shape_Length", xsln_etid_field,"raster_name"],"KEEP_FIELDS")





# %% 7 Record and print tool end time
toolend = datetime.datetime.now()
toolelapsed = toolend - toolstart
printit('Tool completed at {0}. Elapsed time: {1}. Youre a wizard!'.format(toolend, toolelapsed))
