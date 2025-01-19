#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Get Unlocated CWI Data
# For use with DNR Cross Section Tools3_3.atbx

# Modified by Kelsey Forward, MN DNR
# Modified Date: January 2024
# Last modified date: 9/23/24

# Original script Created by Sarah Francis, Minnesota Geological Survey
# Created Date: November 2023
'''
This script gets unverifiied-location well CWI data for a buffered cross section line file and creates a map-view well point file,
a buffered cross section polygon file, a map-view static water level point file, and stratigraphy/lithology,
construction, & drop pipe tables.
'''

# %%
# 1 Import modules and define functions

import arcpy
from arcpy import env
from arcpy.sa import *
import os
import datetime

# Record tool start time
toolstart = datetime.datetime.now()

# Define print statement function for testing and compiled geoprocessing tool

def printit(message):
    arcpy.AddMessage(message)
    print(message)

def printwarning(message):
    arcpy.AddWarning(message)
    print(message)

def printerror(message):
    arcpy.AddError(message)
    print(message)

# Define file exists function and field exists function

def FileExists(file):
    if not arcpy.Exists(file):
        printerror("Error: {0} does not exist.".format(os.path.basename(file)))
    #else: printit("{0} found.".format(os.path.basename(file)))

def FieldExists(dataset, field_name):
    if field_name in [field.name for field in arcpy.ListFields(dataset)]:
        return True
    else:
        printerror("Error: {0} field does not exist in {1}."
                .format(field_name, os.path.basename(dataset)))

# Define function to check for geometry type

def correctGeometry(file, geometry1, geometry2):
    desc = arcpy.Describe(file)
    if not desc.shapeType == geometry1:
        if not desc.shapeType == geometry2:
            printerror("Error: {0} does not have {1} geometry.".format(os.path.basename(file), geometry1))
    #else: printit("{0} has {1} geometry.".format(os.path.basename(file), geometry))

# %%
# 2 Set parameters to work in testing and compiled geopocessing tool

# !!!!!!!!!!!!!!!!!!!!!!
#change the variable below if running in an IDE.
# MAKE SURE TO CHANGE BACK TO "PRO" WHEN FINISHED
#----------------------------------------------------------------
#run_location = "ide"
run_location = "Pro"
#----------------------------------------------------------------
#!!!!!!!!!!!!!!!!!!!!!!

if run_location == "Pro":
    #variable = arcpy.GetParameterAsText(0)
    output_gdb = arcpy.GetParameterAsText(0)
    xsln = arcpy.GetParameterAsText(1)
    buffer_distance = int(arcpy.GetParameterAsText(2)) #meters
    dem_raster = arcpy.GetParameterAsText(3)
    strat_boolean = arcpy.GetParameter(4)
    dpl_boolean = arcpy.GetParameter(5)
    printit("Variables set with tool parameter inputs.")

else:
    # hard-coded parameters used for testing
    output_gdb = r'D:\Cross_Section_Programming\112123\script_testing\Steele_Script_Testing.gdb'
    xsln = r'D:\Cross_Section_Programming\112123\script_testing\Steele_Script_Testing.gdb\xsln'
    buffer_distance = 500 #meters, half a mile
    printit("Variables set with hard-coded parameters for testing.")

#Input Data QAQC
#check for invalid buffer value
if buffer_distance <= 0 :
    printerror("Error: Buffer distance must be greater than zero.")
    raise SystemExit

#check raster name for invalid characters
if dem_raster != "dem" :
    printerror("Error: Raster name not valid. Rename land surface DEM raster to exactly 'dem' in Contents pane.")
    raise SystemExit

#%% 3 Buffer xsln file
printit("Buffering xsln file.")

xsln_buffer = os.path.join(output_gdb, "xsln_buffer")
arcpy.analysis.Buffer(xsln, xsln_buffer, buffer_distance, '', "FLAT")

#%% 4 Clip statewide wwpt file by xsln buffer

printit("Clipping statewide CWI wwpt file with xsln buffer.")
arcpy.env.overwriteOutput = True

state_wwpt = r'V:\gdrs\data\pub\us_mn_state_health\water_well_information\fgdb\water_well_information.gdb\unloc_wells'
wwpt_unloc_temp = os.path.join(output_gdb, 'wwpt_unloc_temp')

arcpy.analysis.Clip(state_wwpt, xsln_buffer, wwpt_unloc_temp)

wwpt_count_result = arcpy.management.GetCount(wwpt_unloc_temp)
wwpt_count = int(wwpt_count_result[0])
if wwpt_count == 0:
    printerror("Error: No wells present within buffer zone. Increase buffer distance to include wells.")
    raise SystemExit

printit("Exporting wwpt points to geodatabase.")

#%%
# 4 Join attributes from xsln to wwpt

printit("Spatial join xsln attributes to well points.")
arcpy.env.overwriteOutput = True
wwpt_unloc = os.path.join(output_gdb, 'wwpt_unloc')
arcpy.analysis.SpatialJoin(wwpt_unloc_temp, xsln_buffer, wwpt_unloc, 'JOIN_ONE_TO_MANY')

#%% ?? Extract elevation from DEM

printit("Extracting well point elevations from DEM.")
arcpy.env.overwriteOutput = True

ExtractMultiValuesToPoints(wwpt_unloc, dem_raster, "NONE")

#Add source
wwpt_cwi_TableSelect_2_ = arcpy.management.AddField(wwpt_unloc, "Data_Source", "TEXT", 12,"", "","","")
wwpt_cwi_TableSelect_3_ = arcpy.management.CalculateField(wwpt_cwi_TableSelect_2_, "Data_Source", "'Unverified'","","","","")

#%%
# 5 Make strat table
if strat_boolean == True:
    printit("Clipping statewide stratigraphy data with xsln buffer.")

    state_strat_tbl = r'I:\EWR\_IMA\HGG\_HYDRO_GEO_GROUNDWATER\Tools\GIS\Pro_DNR_CrossSection_Tool\db20-pg-mgs_cwi-cwiro.sde\mgs_cwi.cwi.unloc_wells_c5st'

    #join statewide construction table and wwpt
    strat_temp = arcpy.management.AddJoin(state_strat_tbl, "relateid", wwpt_unloc, "relateid",'KEEP_COMMON')

    printit("Exporting joined table to geodatabase table.")

    temp_table_view5 = "temp_table_view5"
    arcpy.management.MakeTableView(strat_temp, temp_table_view5)
    strat_table = os.path.join(output_gdb, "strat_unloc")
    try:
        #TableToTable is apparently depricated, but the newer version (ExportTable)
        #isn't working? This way, one of them should work.
        arcpy.conversion.ExportTable(temp_table_view5, strat_table)
    except:
        arcpy.conversion.TableToTable(temp_table_view5, output_gdb, "strat_unloc")

    #Add source
    strat_cwi_TableSelect_1_ = arcpy.management.AddField(strat_table, "Data_Source", "TEXT", 12,"", "","","")
    strat_cwi_TableSelect_2_ = arcpy.management.CalculateField(strat_cwi_TableSelect_1_, "Data_Source", "'Unverified'","","","","")


#%%
# 6 Make SWL table
printit("Clipping statewide SWL data with xsln buffer.")
arcpy.env.overwriteOutput = True

state_swl_tbl = r'I:\EWR\_IMA\HGG\_HYDRO_GEO_GROUNDWATER\Tools\GIS\Pro_DNR_CrossSection_Tool\db20-pg-mgs_cwi-cwiro.sde\mgs_cwi.cwi.unloc_wells_c5wl'

#join statewide construction table and wwpt
swl_temp = arcpy.management.AddJoin(state_swl_tbl, "relateid", wwpt_unloc, "relateid",'KEEP_COMMON')

printit("Exporting joined table to geodatabase table.")

temp_table_view4 = "temp_table_view4"
arcpy.management.MakeTableView(swl_temp, temp_table_view4)
swl_table = os.path.join(output_gdb, "swl_unloc")
try:
    #TableToTable is apparently depricated, but the newer version (ExportTable)
    #isn't working? This way, one of them should work.
    arcpy.conversion.ExportTable(temp_table_view4, swl_table)
except:
    arcpy.conversion.TableToTable(temp_table_view4, output_gdb, "swl_unloc")

#Add source
swl_cwi_TableSelect_1_ = arcpy.management.AddField(swl_table, "Data_Source", "TEXT", 12,"", "","","")
swl_cwi_TableSelect_2_ = arcpy.management.CalculateField(swl_cwi_TableSelect_1_, "Data_Source", "'Unverified'","","","","")

#%%
# 7 Make conspy table
printit("Joining statewide construction data table with wwpt.")

state_construction_tbl = r'I:\EWR\_IMA\HGG\_HYDRO_GEO_GROUNDWATER\Tools\GIS\Pro_DNR_CrossSection_Tool\db20-pg-mgs_cwi-cwiro.sde\mgs_cwi.cwi.unloc_wells_c5c2'

#join statewide construction table and wwpt
const_temp = arcpy.management.AddJoin(state_construction_tbl, "relateid", wwpt_unloc, "relateid",'KEEP_COMMON')

printit("Exporting joined table to geodatabase table.")

temp_table_view2 = "temp_table_view2"
arcpy.management.MakeTableView(const_temp, temp_table_view2)
cons_table = os.path.join(output_gdb, "cons_unloc")
try:
    #TableToTable is apparently depricated, but the newer version (ExportTable)
    #isn't working? This way, one of them should work.
    arcpy.conversion.ExportTable(temp_table_view2, cons_table)
except:
    arcpy.conversion.TableToTable(temp_table_view2, output_gdb, "cons_unloc")

#Add source
cons_cwi_TableSelect_1_ = arcpy.management.AddField(cons_table, "Data_Source", "TEXT", 12,"", "","","")
cons_cwi_TableSelect_2_ = arcpy.management.CalculateField(cons_cwi_TableSelect_1_, "Data_Source", "'Unverified'","","","","")

#%%
# 8 Make drop pipe table
if dpl_boolean == True:
    printit("Joining statewide drop pipe data table with wwpt.")

    state_droppipe_tbl = r'I:\EWR\_IMA\HGG\_HYDRO_GEO_GROUNDWATER\Tools\GIS\Pro_DNR_CrossSection_Tool\db20-pg-mgs_cwi-cwiro.sde\mgs_cwi.cwi.unloc_wells_c5c1'

    #join statewide construction table and wwpt
    const_temp1 = arcpy.management.AddJoin(state_droppipe_tbl, "relateid", wwpt_unloc, "relateid",'KEEP_COMMON')

    printit("Exporting joined table to geodatabase table.")

    temp_table_view3 = "temp_table_view3"
    arcpy.management.MakeTableView(const_temp1, temp_table_view3)
    cons_table1 = os.path.join(output_gdb, "dpl_unloc")
    try:
        #TableToTable is apparently depricated, but the newer version (ExportTable)
        #isn't working? This way, one of them should work.
        arcpy.conversion.ExportTable(temp_table_view3, cons_table1)
    except:
        arcpy.conversion.TableToTable(temp_table_view3, output_gdb, "dpl_unloc")

    #Add source
    cons1_cwi_TableSelect_1_ = arcpy.management.AddField(cons_table1, "Data_Source", "TEXT", 12,"", "","","")
    cons1_cwi_TableSelect_2_ = arcpy.management.CalculateField(cons1_cwi_TableSelect_1_, "Data_Source", "'Unverified'","","","","")

#%%
# 9 Delete temporary files
printit("Deleting temporary files.")
try: arcpy.management.Delete(wwpt_unloc_temp)
except: printit("Unable to delete {0}.".format(wwpt_unloc_temp))

try: arcpy.management.Delete(cons_temp)
except: printit("Unable to delete {0}.".format(const_temp))

try: arcpy.management.Delete(cons_temp1)
except: printit("Unable to delete {0}.".format(const_temp1))

try: arcpy.management.Delete(swl_temp)
except: printit("Unable to delete {0}.".format(swl_temp))


# %%
# 10 Record and print tool end time
toolend = datetime.datetime.now()
toolelapsed = toolend - toolstart
printit('Tool completed at {0}. Elapsed time: {1}. Youre a wizard!'.format(toolend, toolelapsed))
# %%
