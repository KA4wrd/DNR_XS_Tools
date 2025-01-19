#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Get CWI Data (verified location wells)

# Modified by Kelsey Forward, MN DNR for use with DNR Cross Section Tools.atbx
# Modified Date: January 2024
#
# Modifications made:
# - Altered CWI SDE location address to DNR shared drive
# - Changed strat table name to "strat_lith" table
# - Added Make SWL, Make Conspy, and Make drop pipe table sections
#
# Original script created by Sarah Francis, Minnesota Geological Survey for use with the MGS_Bedrock_CrossSection_Tools.atbx
# Created Date: July 2023

'''
This script gets CWI data for a buffered cross section line file and creates a map-view well point file (verified well locations only),
a buffered cross section polygon file, a map-view static water level point file, and stratigraphy/lithology,
construction, & drop pipe tables.
'''

# %%
# 1 Import modules and define functions

import arcpy
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
    printit("Variables set with tool parameter inputs.")

else:
    # hard-coded parameters used for testing
    output_gdb = r'D:\Cross_Section_Programming\112123\script_testing\Steele_Script_Testing.gdb'
    xsln = r'D:\Cross_Section_Programming\112123\script_testing\Steele_Script_Testing.gdb\xsln'
    buffer_distance = 500 #meters, half a mile
    printit("Variables set with hard-coded parameters for testing.")


#%% 3 Buffer xsln file
printit("Buffering xsln file.")

xsln_buffer = os.path.join(output_gdb, "xsln_buffer")
arcpy.analysis.Buffer(xsln, xsln_buffer, buffer_distance, '', "FLAT")

#%% 4 Clip statewide wwpt file by xsln buffer

printit("Clipping statewide CWI wwpt file with xsln buffer.")
arcpy.env.overwriteOutput = True

state_wwpt = r'I:\EWR\_IMA\HGG\_HYDRO_GEO_GROUNDWATER\Tools\GIS\Pro_DNR_CrossSection_Tool\CWI_db20.sde\mgs_cwi.cwi.loc_wells'
wwpt_temp = os.path.join(output_gdb, 'wwpt_temp')

arcpy.analysis.Clip(state_wwpt, xsln_buffer, wwpt_temp)
printit("Exporting wwpt points to geodatabase.")

#%%
# 4 Join attributes from xsln to wwpt

printit("Spatial join xsln attributes to well points.")
arcpy.env.overwriteOutput = True
wwpt = os.path.join(output_gdb, 'wwpt')
arcpy.analysis.SpatialJoin(wwpt_temp, xsln_buffer, wwpt, 'JOIN_ONE_TO_MANY')


#%%
# 5 Make strat table
printit("Clipping statewide stratigraphy data with xsln buffer.")

#I think this point file has all of the attributes needed?
state_strat_points = r'I:\EWR\_IMA\HGG\_HYDRO_GEO_GROUNDWATER\Tools\GIS\Pro_DNR_CrossSection_Tool\CWI_db20.sde\mgs_cwi.cwi.stratigraphy'

#clip statewide strat points
strat_points_temp = os.path.join(output_gdb, "strat_temp")
arcpy.analysis.Clip(state_strat_points, xsln_buffer, strat_points_temp)

#spatial join with xsln buffer
printit("Spatial join xsln attributes to stratigraphy points.")
strat_points_temp2 = os.path.join(output_gdb, "strat_temp2")
arcpy.analysis.SpatialJoin(strat_points_temp, xsln_buffer, strat_points_temp2, 'JOIN_ONE_TO_MANY')

#export strat points temp2 to geodatabase table
printit("Exporting temp stratigraphy points to geodatabase table.")
temp_table_view = "temp_table_view"
arcpy.management.MakeTableView(strat_points_temp2, temp_table_view)
strat_table = os.path.join(output_gdb, "strat_lith_cwi")
try:
    #TableToTable is apparently depricated, but the newer version (ExportTable)
    #isn't working? This way, one of them should work.
    arcpy.conversion.ExportTable(temp_table_view, strat_table)
except:
    arcpy.conversion.TableToTable(temp_table_view, output_gdb, "strat_lith_cwi")

#%%
# 6 Make SWL table
printit("Clipping statewide SWL data with xsln buffer.")
arcpy.env.overwriteOutput = True

state_swl_points = r'I:\EWR\_IMA\HGG\_HYDRO_GEO_GROUNDWATER\Tools\GIS\Pro_DNR_CrossSection_Tool\CWI_db20.sde\mgs_cwi.cwi.water_level'

#clip statewide SWL points
swl_points_temp = os.path.join(output_gdb, "swl_temp")
arcpy.analysis.Clip(state_swl_points, xsln_buffer, swl_points_temp)

#spatial join with xsln buffer
printit("Spatial join xsln attributes to swl points.")
arcpy.env.overwriteOutput = True
swl_pt = os.path.join(output_gdb, "swl_cwi")
arcpy.analysis.SpatialJoin(swl_points_temp, xsln_buffer, swl_pt, 'JOIN_ONE_TO_MANY')
printit("Exporting swl points to geodatabase.")

#%%
# 7 Make conspy table
printit("Joining statewide construction data table with wwpt.")

state_construction_tbl = r'I:\EWR\_IMA\HGG\_HYDRO_GEO_GROUNDWATER\Tools\GIS\Pro_DNR_CrossSection_Tool\CWI_db20.sde\mgs_cwi.cwi.loc_wells_c5c2'

#join statewide construction table and wwpt
const_temp = arcpy.management.AddJoin(state_construction_tbl, "relateid", wwpt, "relateid",'KEEP_COMMON')

printit("Exporting joined table to geodatabase table.")

temp_table_view2 = "temp_table_view2"
arcpy.management.MakeTableView(const_temp, temp_table_view2)
cons_table = os.path.join(output_gdb, "cons_cwi")
try:
    #TableToTable is apparently depricated, but the newer version (ExportTable)
    #isn't working? This way, one of them should work.
    arcpy.conversion.ExportTable(temp_table_view2, cons_table)
except:
    arcpy.conversion.TableToTable(temp_table_view2, output_gdb, "cons_cwi")

#%%
# 8 Make drop pipe table
printit("Joining statewide drop pipe data table with wwpt.")

state_droppipe_tbl = r'I:\EWR\_IMA\HGG\_HYDRO_GEO_GROUNDWATER\Tools\GIS\Pro_DNR_CrossSection_Tool\CWI_db20.sde\mgs_cwi.cwi.loc_wells_c5c1'

#join statewide construction table and wwpt
const_temp1 = arcpy.management.AddJoin(state_droppipe_tbl, "relateid", wwpt, "relateid",'KEEP_COMMON')

printit("Exporting joined table to geodatabase table.")

temp_table_view3 = "temp_table_view3"
arcpy.management.MakeTableView(const_temp1, temp_table_view3)
cons_table1 = os.path.join(output_gdb, "drop_pipe_cwi")
try:
    #TableToTable is apparently depricated, but the newer version (ExportTable)
    #isn't working? This way, one of them should work.
    arcpy.conversion.ExportTable(temp_table_view3, cons_table1)
except:
    arcpy.conversion.TableToTable(temp_table_view3, output_gdb, "drop_pipe_cwi")


#%%
# 9 Delete temporary files
printit("Deleting temporary files.")
try: arcpy.management.Delete(wwpt_temp)
except: printit("Unable to delete {0}.".format(wwpt_temp))

try: arcpy.management.Delete(strat_points_temp)
except: printit("Unable to delete {0}.".format(strat_points_temp))

try: arcpy.management.Delete(strat_points_temp2)
except: printit("Unable to delete {0}.".format(strat_points_temp2))

try: arcpy.management.Delete(swl_points_temp)
except: printit("Unable to delete {0}.".format(swl_points_temp))


# %%
# 10 Record and print tool end time
toolend = datetime.datetime.now()
toolelapsed = toolend - toolstart
printit('Tool completed at {0}. Elapsed time: {1}. You did it!'.format(toolend, toolelapsed))
# %%
