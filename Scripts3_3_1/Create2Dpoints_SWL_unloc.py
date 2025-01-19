#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Create Unloc 2D Static Water Level points (Traditional display, unverified well locations only)
# For use with DNR Cross Section Tools3_3.atbx
# Created by Kelsey Forward, MN DNR, January 2023
# Date last updated: 9/23/24

# Modified from orignal scripts by Sarah Francis, Minnesota Geological Survey
#   Create Well Stick Diagrams (Stacked), October 2022
# Thanks, Sarah!

'''
This script creates point files that are used to visualize well static water level locations
along defined cross sections. Outputs are: a point file in 2D cross-section space
to use for cross-section creation and editing. Data is retrieved from a static water level well
point location feature class.
'''

# %% 1 Import modules

import arcpy
import os
import sys
import datetime

#%% 2 Define functions

# Record tool start time
toolstart = datetime.datetime.now()

# Define print statement functions for testing and compiled geoprocessing tool

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

# Define field exists function

def FieldExists(dataset, field_name):
    if field_name in [field.name for field in arcpy.ListFields(dataset)]:
        return True
    else:
        printerror("Error: {0} field does not exist in {1}."
                .format(field_name, os.path.basename(dataset)))

# %% 3 Set parameters to work in testing and compiled geopocessing tool

if (len(sys.argv) > 1):
    # input parameters for geoprocessing tool
    workspace = arcpy.GetParameterAsText(0)  #output gdb
    wwpt_file_orig = arcpy.GetParameterAsText(1)  #point feature class with well location information
    xsln_file_orig = arcpy.GetParameterAsText(2) #mapview cross section line feature class
    xsln_etid_field = arcpy.GetParameterAsText(3)  #cross section ID field in cross section file, text data type
    wwpt_etid_field = arcpy.GetParameterAsText(4)  #cross section ID field in well point file
    wwpt_wellid_field = arcpy.GetParameterAsText(5)  #well ID number field in well point file
    buffer_dist = int(arcpy.GetParameterAsText(6))
    vertical_exaggeration = int(arcpy.GetParameterAsText(7))
    spatialref_2d = arcpy.GetParameterAsText(8) # .prj file for custom coordinate system for 2D display
    printit("Variables set with tool parameter inputs.")

else:
    # hard-coded parameters used for testing
    workspace = r'C:\Users\Keforwar\Desktop\ArcGISProXS\TESTdataMeadowStar\ARCPRO\PointTest.gdb' #output gdb
    wwpt_file_orig = r'C:\Users\Keforwar\Desktop\ArcGISProXS\TESTdataMeadowStar\ARCPRO\TestOutputJan17.gdb\wwpt' #point feature class with well location information
    xsln_file_orig = r'C:\Users\Keforwar\Desktop\ArcGISProXS\TESTdataMeadowStar\ARCPRO\demo_data_kandiyohi.gdb\User_Generated_Input\cross_section_lines' #mapview cross section line feature class
    xsln_etid_field = 'xsec_id' #cross section ID field in cross section file, text data type
    wwpt_etid_field = 'xsec_id' #cross section ID field in well point file
    wwpt_wellid_field = 'relateid' #well ID number field in well point file
    buffer_dist = 500
    vertical_exaggeration = 50
    printit("Variables set with hard-coded parameters for testing.")


#%% 4  Set 3d spatial reference based on xsln file

spatialref = arcpy.Describe(xsln_file_orig).spatialReference
if spatialref.name == "Unknown":
    printerror("{0} file has an unknown spatial reference. Continuing may result in errors.".format(os.path.basename(xsln_file_orig)))
else:
    printit("Spatial reference set as {0} to match {1} file.".format(spatialref.name, os.path.basename(xsln_file_orig)))

# %% 5 Data QC

#determine if input cross section lines have multipart features
multipart = False
with arcpy.da.SearchCursor(xsln_file_orig, ["SHAPE@"]) as cursor:
    for row in cursor:
        if row[0].isMultipart:
            multipart = True
            break
if multipart:
    printerror("Warning: cross section file contains multipart features. Continuing may result in errors.")

#determine if  input tables have the correct matching fields (function defined above)
printit("Checking that data tables have correct fields.")
FieldExists(wwpt_file_orig, "dem")
FieldExists(wwpt_file_orig, "measuremt")
FieldExists(wwpt_file_orig, "meas_elev")
FieldExists(wwpt_file_orig, "Data_Source")

#check for invalid buffer value
if buffer_dist <= 0 :
    printerror("Error: Buffer distance must be greater than zero.")
    raise SystemExit

#check for invalid VE value
if vertical_exaggeration <= 0 :
    printerror("Error: Vertical Exaggeration must be greater than 0.")
    raise SystemExit

#%% 6 Data QC

# Count number of rows in input parameters
wwpt_count_result = arcpy.management.GetCount(wwpt_file_orig)
wwpt_count = int(wwpt_count_result[0])
if wwpt_count == 0:
    printerror("Error: well location point file is empty.")
    raise SystemExit

xsln_count_result = arcpy.management.GetCount(xsln_file_orig)
xsln_count = int(xsln_count_result[0])
if xsln_count == 0:
    printerror("Error: cross section line file is empty.")
    raise SystemExit

#%% 7 Check that well point file, and cross section file match

printit("Checking that well point file, and cross section line file all match.")
# Create empty lists to store well IDs and et_ids in each file
wwpt_wellid_list = []
wwpt_etid_list = []
xsln_etid_list = []

# Populate well point file wellid, et_id, and well label lists
with arcpy.da.SearchCursor(wwpt_file_orig, [wwpt_wellid_field, wwpt_etid_field]) as wwpt_records:
    for row in wwpt_records:
        wellid = row[0]
        etid = row[1]
        if wellid not in wwpt_wellid_list:
            wwpt_wellid_list.append(wellid)
        if etid not in wwpt_etid_list:
            wwpt_etid_list.append(etid)

# Populate cross section line et_id list
with arcpy.da.SearchCursor(xsln_file_orig, [xsln_etid_field]) as xsln_records:
    for line in xsln_records:
        etid = line[0]
        if etid not in xsln_etid_list:
            xsln_etid_list.append(etid)

# Check that et_id fields in well point file have matching xsln et_id
listprint = []
for etid in wwpt_etid_list:
    if etid not in xsln_etid_list:
        listprint.append(etid)
listprint_len = len(listprint)
if listprint_len > 0:
        printit("Warning: there are {0} et_id's in well point file that do not match any et_id's in cross section line file. Well point et_id's are: {1}".format(listprint_len, listprint))

# Check that all cross section lines have matching well points
listprint = []
for etid in xsln_etid_list:
    if etid not in wwpt_etid_list:
        listprint.append(etid)
listprint_len = len(listprint)
if listprint_len > 0:
        printit("Warning: there are {0} cross section lines that do not have any associated well points. Cross section et_id's are: {1}".format(listprint_len, listprint))

# Set boolean variable that stores data type of well id field (needed for defining Where Clause later)
wellid_is_numeric = True
if type(wwpt_wellid_list[0]) == str:
    wellid_is_numeric = False

# %% 8 List fields that are used in 2d point

# set field type of well id so code correctly handles text vs. numeric
if wellid_is_numeric:
    well_id_field_type = 'DOUBLE'
elif not wellid_is_numeric:
    well_id_field_type = 'TEXT'

# fields needed in all output files
fields_base = [[wwpt_wellid_field, well_id_field_type], [xsln_etid_field, 'TEXT', '', 3],
               ['x_coord', 'DOUBLE'], ['y_coord', 'DOUBLE'], ['x_coord_2d', 'DOUBLE'], ['y_coord_2d', 'DOUBLE'],['meas_elev', 'DOUBLE'] ]

# fields only needed in 2d files (point, polyline, and polygon)
fields_2d = [['distance', 'FLOAT'], ['pct_dist', 'FLOAT']]

# fields needed only in 2d point file
fields_2d_point = [['measuremt', 'DOUBLE'],['dem', 'FLOAT'],['BUFF_DIST','DOUBLE'],['VE','DOUBLE'],['Data_Source','TEXT']]


# %% 9 Create empty 2d point file, to show well locations in cross section space

arcpy.env.overwriteOutput = True

#create point shapefile
printit("Creating empty 2d point file to show well locations.")
arcpy.management.CreateFeatureclass(workspace, "swl_unloc_2d_xsecview", "POINT", '',
                                    'DISABLED', 'DISABLED')

#set point shapefile filepath variable
pointfile = os.path.join(workspace, "swl_unloc_2d_xsecview")

#define field names and types: base fields, 2d fields, and 2d point fields
point_2d_fields = fields_base + fields_2d + fields_2d_point

#Add fields to 2D point file
arcpy.management.AddFields(pointfile, point_2d_fields)

#%% 10 Create feature dataset to store wwpt files by xs
# wwpt files need to be split by xs to ensure that each well is referencing the correct xsln
arcpy.env.overwriteOutput = True
printit("Creating feature dataset for temporary file storage and copying well point file.")
arcpy.management.CreateFeatureDataset(workspace, "wwpt_by_xs")
wwpt_by_xs_fd = os.path.join(workspace, "wwpt_by_xs")


# Make a temporary copy of the wwpt file and put it in the new feature dataset
# Code below will grab selected features from this temporary wwpt file.
# The temporary file will be deleted when geometry is completed.
wwpt_file_temp = os.path.join(wwpt_by_xs_fd, "wwpt_temp")
arcpy.management.CopyFeatures(wwpt_file_orig, wwpt_file_temp)

#%% 11 Add fields to temporary wwpt point feature class
# These fields will be populated by near analysis and measure on line functions

wwpt_fields = [["NEAR_FID", "LONG"], ["NEAR_DIST", "DOUBLE"], ["NEAR_X", "DOUBLE"],
               ["NEAR_Y", "DOUBLE"], ["OnLine_DIST", "FLOAT"],["VE","DOUBLE"]]

for newfield in wwpt_fields:
    if newfield[0] in [field.name for field in arcpy.ListFields(wwpt_file_temp)]:
        printit("{0} field already exists in well point file. Tool will overwrite data in this field.".format(newfield[0]))
    else:
        printit("Adding {0} field to well point file.".format(newfield[0]))
        arcpy.management.AddField(wwpt_file_temp, newfield[0], newfield[1])

#%% 12 Create a temporary xsln file and extend the lines equal to buffer distance
    # The extended xsln file is used to define 2d x coordinates of wells
    # to ensure that wells beyond the xsln plot correctly
# Create temporary xsln file (empty for now)
xsln_temp = os.path.join(workspace, "xsln_temp")
arcpy.management.CreateFeatureclass(workspace, "xsln_temp", "POLYLINE", '', 'DISABLED', 'DISABLED', spatialref)

# add et_id and mn_et_id fields to temp xsln file
arcpy.management.AddField(xsln_temp, xsln_etid_field, "TEXT")
arcpy.management.AddField(xsln_temp, 'mn_et_id', "TEXT")
printit("Creating temporary xsln file to ensure wells beyond xsln endpoints plot correctly.")
# Read geometries of original xsln file and create new geometry in temp xsln file
# Temp xsln file will have the first and last segments extended equal to xsln spacing
# This is to ensure that near analysis function will find the correct point for
# wells beyond the from and to nodes of the cross section line.

with arcpy.da.SearchCursor(xsln_file_orig, ['SHAPE@', xsln_etid_field]) as xsln:
    for line in xsln:
        et_id = line[1]
        geompointlist = []
        # Fill geompoint list with list of vertices in the xsln as point geometry objects
        for vertex in line[0].getPart(0): #for each vertex in array of point objects
            point = arcpy.PointGeometry(arcpy.Point(vertex.X, vertex.Y))
            geompointlist.append(point)
        # Set variables to define first two points
        beg_pt = geompointlist[0]
        beg_pt2 = geompointlist[1]
        # Calculate angle of beginning line segment from second point to beginning
        beg_angle_and_dist = beg_pt2.angleAndDistanceTo(beg_pt, "PLANAR")
        beg_angle = beg_angle_and_dist[0]
        # Set variables to define last two points
        end_pt = geompointlist[-1]
        end_pt2 = geompointlist[-2]
        # Calculate angle of end line segment
        end_angle_and_dist = end_pt2.angleAndDistanceTo(end_pt, "PLANAR")
        end_angle = end_angle_and_dist[0]
        # Calculate new beginning and end points based on angle of segment and buffer distance
        # extending lines equal to buffer distance should capture all of the points
        new_beg = beg_pt.pointFromAngleAndDistance(beg_angle, buffer_dist, method='PLANAR')
        new_end = end_pt.pointFromAngleAndDistance(end_angle, buffer_dist, method='PLANAR')
        # Change first and last coordinate values in geompointlist to use in creating temporary xsln file
        geompointlist[0] = new_beg
        geompointlist[-1] = new_end
        # Turn geompointlist into point object list instead of point geometry objects
        pointlist = []
        for vertex in geompointlist:
            newpt = vertex[0]
            pointlist.append(newpt)
        # Create arcpy array for writing geometry
        xsln_array = arcpy.Array(pointlist)
        # Turn array of point vertices into polyline object
        new_xsln_geometry = arcpy.Polyline(xsln_array, spatialref, True)
        with arcpy.da.InsertCursor(xsln_temp, ['SHAPE@', xsln_etid_field]) as cursor:
            # Create geometry and fill in field values
            cursor.insertRow([new_xsln_geometry, et_id])

#%% 13 Populate near analysis fields in wwpt file
# This is populating fields in wwpt file that are used later to create geometry
arcpy.env.overwriteOutput = True
starttime = datetime.datetime.now()
# Loop through each xsln_temp and create a geometry object for each line
with arcpy.da.SearchCursor(xsln_temp, ['SHAPE@', xsln_etid_field]) as xsln:
    for line in xsln:
        et_id = line[1]
        pointlist = []
        for vertex in line[0].getPart(0):
            # Creates a polyline geometry object from xsln_temp vertex points.
            # Necessary for near analysis
            point = arcpy.Point(vertex.X, vertex.Y)
            pointlist.append(point)
        array = arcpy.Array(pointlist)
        xsln_geometry = arcpy.Polyline(array)
        # Create a new wwpt file with only points associated with current xsln
        printit("Calculating well locations in cross section view for xsln {0} out of {1}.".format(et_id, xsln_count))
        wwpt_by_xs_file = os.path.join(wwpt_by_xs_fd, "wwpt_{0}".format(et_id))
        arcpy.analysis.Select(wwpt_file_temp, wwpt_by_xs_file, '"{0}" = \'{1}\''.format(wwpt_etid_field, et_id))
        # Do near analysis on wwpt file to populate near x, near y, and near dist fields
        # Near x and y are the coordinates of the point along the xsln that are closest to the well
        # "dist" is the distance between the well and the nearest point on the line
        arcpy.analysis.Near(wwpt_by_xs_file, xsln_geometry, '', 'LOCATION', '', 'PLANAR')
        # Create update cursor object that defines values gathered in near analysis
        with arcpy.da.UpdateCursor(wwpt_by_xs_file, ['OID@', 'NEAR_X', 'NEAR_Y', 'OnLine_DIST']) as wellpts:
            for well in wellpts:
                index = well[0]
                x =  well[1]
                y = well[2]
                # Create point geometry object from nearest point on the xsln
                point = arcpy.Point(x, y)
                # Measure distance from start of xsln geometry object to defined point
                # This is the "OnLine_DIST" which turns into 2d x coordinate after vertical exaggeration calculation
                n = arcpy.Polyline.measureOnLine(xsln_geometry, point)
                #subtract extended line distance so points before start nodes will have negative values
                well[3] = n - buffer_dist
                # Update field values in wwpt table to track near x, y, and OnLine dist
                wellpts.updateRow(well)

endtime = datetime.datetime.now()
elapsed = endtime - starttime
printit('Near analysis and line measuring completed at {0}. Elapsed time: {1}'.format(endtime, elapsed))

#%% 14 Delete wwpt_temp from feature dataset
arcpy.management.Delete(wwpt_file_temp)

#%% 15 Merge together wwpt by xs files into one file
arcpy.env.workspace = wwpt_by_xs_fd
wwpt_list = arcpy.ListFeatureClasses()
printit("Creating mapview well point file with cross section locations calculated.")
wwpt_list_paths = []
for file in wwpt_list:
    path = os.path.join(wwpt_by_xs_fd, file)
    wwpt_list_paths.append(path)

wwpt_merge = os.path.join(workspace, "wwpt_merge")
arcpy.management.Merge(wwpt_list_paths, wwpt_merge)


#%%16 Create 2d well point geometry from merged wwpt file
starttime = datetime.datetime.now()
printit('2D point geometry creation started at {0}'.format(starttime))

with arcpy.da.SearchCursor(wwpt_merge, ['OID@', wwpt_wellid_field, wwpt_etid_field,
                                        'NEAR_DIST', 'SHAPE@X', 'SHAPE@Y', 'OnLine_DIST','dem','meas_elev','measuremt','BUFF_DIST','VE','Data_Source']) as wwpt:
    for well in wwpt:
        index = well[0]
        wellid = well[1]
        et_id = well[2]
        #mn_etid_int = int(mn_et_id)
        dist = well[3] #NEAR_DIST field
        pct_dist = dist / buffer_dist * 200 #percent distance
        real_x = well[4] #true x coordinate of well
        real_y = well[5] #true y coordinate of well
        well_z = well[7] #well sfc elevation
        if well_z == None:
            printit("Error: Well number {0} is null in ""dem"" (surface elevation) field. Skipping.".format(wellid))
            continue
        swl_z = well[8]  #swl elevation
        if swl_z == None:
            printit("Error: Well number {0} is null in ""meas_elev"" field. Skipping.".format(wellid))
            continue
        x_coord_meters = well[6]
        x_coord_feet = (int(x_coord_meters))/0.3048
        x_coord_2d = x_coord_feet/vertical_exaggeration
        y_coord_2d = swl_z
        dtw = well[9] #depth to water a.k.a measuremt
        buff_dist = buffer_dist
        vert_ex = vertical_exaggeration
        data_source = well[12]
        index_int = int(index)
        if index_int % 5000 == 0: #Print statement every 5000th well to track progress
            printit('Working on well number {0} out of {1}'.format(index, wwpt_count))

        point_geometry = arcpy.Point(x_coord_2d, y_coord_2d)

        with arcpy.da.InsertCursor(pointfile, ['SHAPE@', wwpt_wellid_field, wwpt_etid_field,'x_coord',
                                               'y_coord', 'x_coord_2d','y_coord_2d','distance', 'dem', 'meas_elev', 'pct_dist','measuremt','BUFF_DIST','VE','Data_Source']) as cursor:
            # Create geometry and fill in field values, saving true coordinates in attribute
            cursor.insertRow([point_geometry, wellid, et_id, real_x, real_y, x_coord_2d, y_coord_2d, dist, well_z, swl_z, pct_dist, dtw, buff_dist, vert_ex, data_source])

endtime = datetime.datetime.now()
elapsed = endtime - starttime
printit('2D point geometry completed at {0}. Elapsed time: {1}'.format(endtime, elapsed))

pt_file_copy1= arcpy.management.DeleteField(pointfile,['x_coord',
                                               'y_coord', 'x_coord_2d','y_coord_2d','distance','pct_dist'])[0]
                               
# # make copy of unprojected 2D pt file
pointfile_copy = os.path.join(workspace, "swl_unloc_2d_xsecview_prj")
arcpy.management.CopyFeatures(pt_file_copy1, pointfile_copy)

# #%% Defining 2D coordinate system for output feature class
arcpy.management.DefineProjection(pointfile_copy, spatialref_2d)

# 

#%% 17 Delete temporary files/fields

printit("Deleting temporary files from output geodatabase.")
try:
    arcpy.management.Delete(wwpt_by_xs_fd)
    arcpy.management.Delete(wwpt_merge)
    arcpy.management.Delete(xsln_temp)
except:
    printit("Warning: unable to delete all temporary files.")

#%% 18 Record and print tool end time
toolend = datetime.datetime.now()
toolelapsed = toolend - toolstart
printit('Create 2D SWL Points tool completed at {0}. Elapsed time: {1}. You did it!'.format(toolend, toolelapsed))
