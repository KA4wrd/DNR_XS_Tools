#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Get CWI Data (verified location wells)

# Created by Kelsey Forward, MN DNR for use with DNR Cross Section Tools3_3.atbx
# Last Modified Date: 10/29/24
#
# Modifications made:
# - Altered CWI SDE connection file location address to DNR shared drive
# - Added Make SWL, Make Conspy, and Make drop pipe table sections
# - DEM input for extracting DEM values to wwpt, swl_pt, and strat_cwi table. This overwrites elevation values from CWI.
# - Updated for ArcGIS Pro 3.3
# - Added descriptive error messages, Made DPL and strat output optional, added Data_Source field.
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
# 2 Set parameters

output_gdb = arcpy.GetParameterAsText(0)
xsln = arcpy.GetParameterAsText(1)
buffer_distance = int(arcpy.GetParameterAsText(2)) #meters
dem_raster = arcpy.GetParameterAsText(3)
strat_boolean = arcpy.GetParameter(4)
dpl_boolean = arcpy.GetParameter(5)
printit("Variables set with tool parameter inputs.")

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

state_wwpt = r'I:\EWR\_IMA\HGG\_HYDRO_GEO_GROUNDWATER\Tools\GIS\Pro_DNR_CrossSection_Tool\db20-pg-mgs_cwi-cwiro.sde\mgs_cwi.cwi.loc_wells'
wwpt_temp = os.path.join(output_gdb, 'wwpt_temp')

arcpy.analysis.Clip(state_wwpt, xsln_buffer, wwpt_temp)

wwpt_count_result = arcpy.management.GetCount(wwpt_temp)
wwpt_count = int(wwpt_count_result[0])
if wwpt_count == 0:
    printerror("Error: No wells present within buffer zone. Increase buffer distance to include wells.")
    raise SystemExit

printit("Exporting wwpt points to geodatabase.")

#%% 5 Join attributes from xsln to wwpt

printit("Spatial join xsln attributes to well points.")
arcpy.env.overwriteOutput = True
wwpt = os.path.join(output_gdb, 'wwpt')
arcpy.analysis.SpatialJoin(wwpt_temp, xsln_buffer, wwpt, 'JOIN_ONE_TO_MANY')


#%% 6 Extract elevation from DEM and replace CWI elevation value in elevation field only

printit("Extracting well point land surface elevations from DEM.")
arcpy.env.overwriteOutput = True

#ExtractMultiValuesToPoints(wwpt, [dem_raster, "dem"], "NONE")
ExtractMultiValuesToPoints(wwpt, dem_raster, "NONE")

printit("Copying DEM values to elevation field.")
wwpt_cwi_TableSelect_1_ = arcpy.management.CalculateFields(wwpt,"PYTHON3",[["elevation", "!dem!", ""]])[0]

#Add source
wwpt_cwi_TableSelect_2_ = arcpy.management.AddField(wwpt, "Data_Source", "TEXT", 12,"", "","","")
wwpt_cwi_TableSelect_3_ = arcpy.management.CalculateField(wwpt_cwi_TableSelect_2_, "Data_Source", "'Verified'","","","","")

#%%
# 7 Make strat table
if strat_boolean == True:
    printit("Clipping statewide stratigraphy data with xsln buffer.")

    #I think this point file has all of the attributes needed?
    state_strat_points = r'I:\EWR\_IMA\HGG\_HYDRO_GEO_GROUNDWATER\Tools\GIS\Pro_DNR_CrossSection_Tool\db20-pg-mgs_cwi-cwiro.sde\mgs_cwi.cwi.stratigraphy'

    #clip statewide strat points
    strat_points_temp = os.path.join(output_gdb, "strat_temp")
    arcpy.analysis.Clip(state_strat_points, xsln_buffer, strat_points_temp)

    #spatial join with xsln buffer
    printit("Spatial join xsln attributes to stratigraphy points.")
    strat_points_temp2 = os.path.join(output_gdb, "strat_temp2")
    arcpy.analysis.SpatialJoin(strat_points_temp, xsln_buffer, strat_points_temp2, 'JOIN_ONE_TO_MANY')

    ###%% Extract elevation from DEM
    ##
    printit("Extracting well point elevations from DEM.")
    arcpy.env.overwriteOutput = True

    #ExtractMultiValuesToPoints(strat_points_temp2, [dem_raster, "dem"], "NONE")
    ExtractMultiValuesToPoints(strat_points_temp2, dem_raster, "NONE")

    #export strat points temp2 to geodatabase table
    printit("Exporting temp stratigraphy points to geodatabase table.")
    temp_table_view = "temp_table_view"
    arcpy.management.MakeTableView(strat_points_temp2, temp_table_view)
    strat_table = os.path.join(output_gdb, "strat")
    try:
        #TableToTable is apparently depricated, but the newer version (ExportTable)
        #isn't working? This way, one of them should work.
        arcpy.conversion.ExportTable(temp_table_view, strat_table)
    except:
        arcpy.conversion.TableToTable(temp_table_view, output_gdb, "strat")

    #Add source
    strat_cwi_TableSelect_1_ = arcpy.management.AddField(strat_table, "Data_Source", "TEXT", 12,"", "","","")
    strat_cwi_TableSelect_2_ = arcpy.management.CalculateField(strat_cwi_TableSelect_1_, "Data_Source", "'Verified'","","","","")

#%%
# 8 Make SWL table
printit("Clipping statewide SWL data with xsln buffer.")
arcpy.env.overwriteOutput = True

state_swl_points = r'I:\EWR\_IMA\HGG\_HYDRO_GEO_GROUNDWATER\Tools\GIS\Pro_DNR_CrossSection_Tool\db20-pg-mgs_cwi-cwiro.sde\mgs_cwi.cwi.water_level'

#clip statewide SWL points
swl_points_temp = os.path.join(output_gdb, "swl_temp")
arcpy.analysis.Clip(state_swl_points, xsln_buffer, swl_points_temp)

#spatial join with xsln buffer
printit("Spatial join xsln attributes to swl points.")
arcpy.env.overwriteOutput = True
swl_pt = os.path.join(output_gdb, "swl")
arcpy.analysis.SpatialJoin(swl_points_temp, xsln_buffer, swl_pt, 'JOIN_ONE_TO_MANY')
printit("Exporting swl points to geodatabase.")


#################################################################
###%% ?? Extract elevation from DEM
##
printit("Extracting well point elevations from DEM.")
arcpy.env.overwriteOutput = True

#ExtractMultiValuesToPoints(swl_pt, [dem_raster, "dem"], "NONE")
ExtractMultiValuesToPoints(swl_pt, dem_raster, "NONE")
####################################################################
#%%

#Add source
swl_cwi_TableSelect_1_ = arcpy.management.AddField(swl_pt, "Data_Source", "TEXT", 12,"", "","","")
swl_cwi_TableSelect_2_ = arcpy.management.CalculateField(swl_cwi_TableSelect_1_, "Data_Source", "'Verified'","","","","")

#%%
# 9 Make conspy table
printit("Joining statewide construction data table with wwpt.")

state_construction_tbl = r'I:\EWR\_IMA\HGG\_HYDRO_GEO_GROUNDWATER\Tools\GIS\Pro_DNR_CrossSection_Tool\db20-pg-mgs_cwi-cwiro.sde\mgs_cwi.cwi.loc_wells_c5c2'

#join statewide construction table and wwpt
const_temp = arcpy.management.AddJoin(state_construction_tbl, "relateid", wwpt, "relateid",'KEEP_COMMON')

printit("Exporting joined table to geodatabase table.")

temp_table_view2 = "temp_table_view2"
arcpy.management.MakeTableView(const_temp, temp_table_view2)
cons_table = os.path.join(output_gdb, "cons")
try:
    #TableToTable is apparently depricated, but the newer version (ExportTable)
    #isn't working? This way, one of them should work.
    arcpy.conversion.ExportTable(temp_table_view2, cons_table)
except:
    arcpy.conversion.TableToTable(temp_table_view2, output_gdb, "cons")

#Add source
cons_cwi_TableSelect_1_ = arcpy.management.AddField(cons_table, "Data_Source", "TEXT", 12,"", "","","")
cons_cwi_TableSelect_2_ = arcpy.management.CalculateField(cons_cwi_TableSelect_1_, "Data_Source", "'Verified'","","","","")



# 
# %%
# 10 Make drop pipe table

#check if DPL data is wanted
if dpl_boolean == True:
    printit("Joining statewide drop pipe data table with wwpt.")

    state_droppipe_tbl = r'I:\EWR\_IMA\HGG\_HYDRO_GEO_GROUNDWATER\Tools\GIS\Pro_DNR_CrossSection_Tool\db20-pg-mgs_cwi-cwiro.sde\mgs_cwi.cwi.loc_wells_c5c1'

    #join statewide construction table and wwpt
    const_temp1 = arcpy.management.AddJoin(state_droppipe_tbl, "relateid", wwpt, "relateid",'KEEP_COMMON')

    printit("Exporting joined table to geodatabase table.")

    temp_table_view3 = "temp_table_view3"
    arcpy.management.MakeTableView(const_temp1, temp_table_view3)
    cons_table1 = os.path.join(output_gdb, "dpl")
    try:
        #TableToTable is apparently depricated, but the newer version (ExportTable)
        #isn't working? This way, one of them should work.
        arcpy.conversion.ExportTable(temp_table_view3, cons_table1)
    except:
        arcpy.conversion.TableToTable(temp_table_view3, output_gdb, "dpl")

    #Add source
    cons1_cwi_TableSelect_1_ = arcpy.management.AddField(cons_table1, "Data_Source", "TEXT", 12,"", "","","")
    cons1_cwi_TableSelect_2_ = arcpy.management.CalculateField(cons1_cwi_TableSelect_1_, "Data_Source", "'Verified'","","","","")

#%%
# 11 Delete temporary files
printit("Deleting temporary files.")
try: arcpy.management.Delete(wwpt_temp)
except: printit("Unable to delete {0}.".format(wwpt_temp))

if strat_boolean == True:
    try: arcpy.management.Delete(strat_points_temp)
    except: printit("Unable to delete {0}.".format(strat_points_temp))

    try: arcpy.management.Delete(strat_points_temp2)
    except: printit("Unable to delete {0}.".format(strat_points_temp2))

try: arcpy.management.Delete(swl_points_temp)
except: printit("Unable to delete {0}.".format(swl_points_temp))


# %%
# 12 Record and print tool end time
toolend = datetime.datetime.now()
toolelapsed = toolend - toolstart
printit('Tool completed at {0}. Elapsed time: {1}. You did it!'.format(toolend, toolelapsed))
# %%
