#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Clean Unlocated CWI Data (unverified location wells)
# For use with DNR Cross Section Tools3_3.atbx
# Coded by Kelsey Forward, MN DNR
# Created Date: January 2024
# Date last updated: 9/23/2024


'''
This script cleans up and reformats unlocated well stratigraphy, construction, static water level, and drop pipe CWI data for entry into subsequent tools.
'''

# %% 1 Import modules

import arcpy
import os
import sys
import datetime
from sys import argv

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

# %% 3 Set parameters

# input parameters for geoprocessing tool
workspace = arcpy.GetParameterAsText(0)  #output gdb
cons_table = arcpy.GetParameterAsText(1)  #gdb table with construction info. Multiple records per well.
dpl_table = arcpy.GetParameterAsText(2)  #gdb table with drop pipe length info.
dpl_x_field = "UTME" #arcpy.GetParameterAsText(3) #UTM x coordinate field in dpl table
dpl_y_field = "UTMN" #arcpy.GetParameterAsText(4) #UTM y coordinates field in dpl table
spatial_ref = arcpy.SpatialReference(26915) #NAD 1983 UTM Zone 15N
swl_table = arcpy.GetParameterAsText(3)  #gdb table with static water level info.
swl_x_field = "UTME" #arcpy.GetParameterAsText(6) #UTM x coordinate field in swl table
swl_y_field = "UTMN"#arcpy.GetParameterAsText(7) #UTM y coordinates field in swl table
strat_table = arcpy.GetParameterAsText(4) #gdb table with strat/lith info
printit("Variables set with tool parameter inputs.")

# To allow overwriting outputs change overwriteOutput option to True.
arcpy.env.overwriteOutput = True

#%% 4 Clean Construction table

printit("Begin cleaning construction table.")

# Copy construction table
printit("Copying construction table.")
cons_copy = os.path.join(workspace, "cons_unloc_copy")
arcpy.management.Copy(cons_table, cons_copy)

#Delete extra Fields
printit("Deleting extra fields from construction table copy.")
cons_copy_1 = arcpy.management.DeleteField(cons_copy, ["diameter", "slot", "length", "material", "amount",
                                                        "units", "OBJECTID_1", "Join_Count", "TARGET_FID", "JOIN_FID",
                                                        "RELATEID_1", "UNIQUE_NO", "WELLNAME", "TOWNSHIP", "RANGE", "RANGE_DIR",
                                                        "SECTION", "SUBSECTION", "MGSQUAD_C", "ELEV_MC", "STATUS_C", "USE_C",
                                                        "LOC_MC", "LOC_SRC", "DATA_SRC", "DEPTH_DRLL", "DEPTH_COMP", "DATE_DRLL",
                                                        "CASE_DIAM", "CASE_DEPTH", "GROUT", "POLLUT_DST", "POLLUT_DIR", "POLLUT_TYP",
                                                        "STRAT_DATE", "STRAT_UPD", "STRAT_SRC", "STRAT_GEOL", "STRAT_MC", "DEPTH2BDRK",
                                                        "FIRST_BDRK", "LAST_STRAT", "OHTOPUNIT", "OHBOTUNIT", "AQUIFER", "CUTTINGS", "CORE",
                                                        "BHGEOPHYS", "GEOCHEM", "WATERCHEM", "OBWELL", "SWL", "DH_VIDEO", "INPUT_SRC", "UNUSED",
                                                        "ENTRY_DATE", "UPDT_DATE", "GEOC_TYPE", "GCM_CODE", "GEOC_SRC", "GEOC_PRG", "UTME", "UTMN",
                                                        "GEOC_ENTRY", "GEOC_DATE", "GEOCUPD_ENTRY", "GEOCUPD_DATE", "RCVD_DATE", "WELL_LABEL",
                                                        "WELLID_1", "SWLCOUNT", "SWLDATE", "SWLAVGMEAS", "SWLAVGELEV", "BDRKELEV", "OHTOPELEV",
                                                        "OHBOTELEV", "BOTHOLELEV", "LOGURL", "STRATURL", "ORIG_FID"])[0]

#Table Select (Table Select) (analysis)
printit("Removing non screen or casing records from construction table copy.")
cons_cwi_clean = os.path.join(workspace, "cons_unloc_clean")
arcpy.analysis.TableSelect(cons_copy_1, cons_cwi_clean, "constype = 'C' Or constype = 'S' Or constype = 'H'")

#Add Fields
printit("Adding required fields to construction table copy.")
cons_cwi_TableSelect_3_ = arcpy.management.AddFields(cons_cwi_clean,[["elev_top", "FLOAT", "", "", "", ""], ["elev_bot", "FLOAT", "", "", "", ""]])[0]

#Calculate Null depth_from fields for Casing
printit("Setting null 'depth_from' field values for casing records to zero.")
cons_cwi_TableSelect_4_ = arcpy.management.CalculateField(cons_cwi_TableSelect_3_, "from_depth", "0 if !constype! is 'C' and !from_depth! is None else !from_depth!")[0]

# Calculate new Fields
printit("Calculating elev_top and elev_bot field values.")
cons_cwi_TableSelect_5_ = arcpy.management.CalculateFields(cons_cwi_TableSelect_4_,"PYTHON3",[["elev_top", "!dem! - !from_depth!", ""], ["elev_bot", "!dem! - !to_depth!", ""]])[0]


#%% 5 Clean drop pipe data

printit("Begin cleaning drop pipe data.")

# Copy dpl table
printit("Copying drop pipe table.")
dpl_copy = os.path.join(workspace, "dpl_unloc_copy")
arcpy.management.Copy(dpl_table, dpl_copy)

# XY Table To Point
printit("Creating dpl_cwi mapview points for input to 2D point tool.")
dpl_cwi_pt = os.path.join(workspace, "dpl_unloc_clean")
arcpy.management.XYTableToPoint(dpl_copy, dpl_cwi_pt, dpl_x_field, dpl_y_field, "",spatial_ref)

#Delete extra Fields
printit("Deleting extra fields from dpl table copy.")
dpl_copy_1 = arcpy.management.DeleteField(dpl_cwi_pt, ["drill_meth", "drill_flud", "hydrofrac", "hffrom", "hfto", "case_mat", "case_joint",
                                                     "case_top", "drive_shoe", "case_type", "screen", "ohtopfeet", "ohbotfeet", "screen_mfg",
                                                     "screen_typ", "ptlss_mfg", "ptlss_mdl", "bsmt_offst", "csg_top_ok","csg_at_grd", "plstc_prot",
                                                     "disinfectd", "pump_inst", "pump_date", "pump_mfg","pump_model", "pump_hp", "pump_volts", "dropp_mat",
                                                     "pump_cpcty","pump_type", "variance", "drllr_name", "entry_date", "updt_date","utme", "utmn",
                                                     "diameter", "slot", "length", "material", "amount", "units",
                                                     "objectid_1", "Join_Count", "TARGET_FID", "JOIN_FID", "RELATEID_1", "UNIQUE_NO", "WELLNAME", "TOWNSHIP",
                                                     "RANGE", "RANGE_DIR",
                                                     "SECTION", "SUBSECTION", "MGSQUAD_C", "ELEV_MC", "STATUS_C", "USE_C",
                                                     "LOC_MC", "LOC_SRC", "DATA_SRC", "DEPTH_DRLL", "DEPTH_COMP", "DATE_DRLL",
                                                     "CASE_DIAM", "CASE_DEPTH", "GROUT", "POLLUT_DST", "POLLUT_DIR", "POLLUT_TYP",
                                                     "STRAT_DATE", "STRAT_UPD", "STRAT_SRC", "STRAT_GEOL", "STRAT_MC", "DEPTH2BDRK",
                                                     "FIRST_BDRK", "LAST_STRAT", "OHTOPUNIT", "OHBOTUNIT", "AQUIFER", "CUTTINGS", "CORE",
                                                     "BHGEOPHYS", "GEOCHEM", "WATERCHEM", "OBWELL", "SWL", "DH_VIDEO", "INPUT_SRC", "UNUSED",
                                                     "ENTRY_DATE", "UPDT_DATE", "GEOC_TYPE", "GCM_CODE", "GEOC_SRC", "GEOC_PRG", "UTME", "UTMN",
                                                     "GEOC_ENTRY", "GEOC_DATE", "GEOCUPD_ENTRY", "GEOCUPD_DATE", "RCVD_DATE", "WELL_LABEL",
                                                     "WELLID_1", "SWLCOUNT", "SWLDATE", "SWLAVGMEAS", "SWLAVGELEV", "BDRKELEV", "OHTOPELEV",
                                                     "OHBOTELEV", "BOTHOLELEV", "LOGURL", "STRATURL", "ORIG_FID"])[0]

#%% 6 Clean swl data

printit("Begin cleaning swl data.")

# Copy swl table
printit("Copying swl table.")
swl_copy = os.path.join(workspace, "swl_unloc_copy")
arcpy.management.Copy(swl_table, swl_copy)

# XY Table To Point
printit("Creating swl_cwi mapview points for input to 2D point tool.")
swl_cwi_pt = os.path.join(workspace, "swl_unloc_clean")
arcpy.management.XYTableToPoint(swl_copy, swl_cwi_pt, swl_x_field, swl_y_field, "",spatial_ref)

#Delete extra Fields
printit("Deleting extra fields from swl table copy.")
swl_copy_1 = arcpy.management.DeleteField(swl_cwi_pt, ["OBJECTID_1", "Join_Count", "TARGET_FID", "JOIN_FID", "RELATEID_1", "UNIQUE_NO", "WELLNAME", "TOWNSHIP",
                                                     "RANGE", "RANGE_DIR",
                                                     "SECTION", "SUBSECTION", "MGSQUAD_C", "ELEV_MC", "STATUS_C", "USE_C",
                                                     "LOC_MC", "LOC_SRC", "DATA_SRC", "DEPTH_DRLL", "DEPTH_COMP", "DATE_DRLL",
                                                     "CASE_DIAM", "CASE_DEPTH", "GROUT", "POLLUT_DST", "POLLUT_DIR", "POLLUT_TYP",
                                                     "STRAT_DATE", "STRAT_UPD", "STRAT_SRC", "STRAT_GEOL", "STRAT_MC", "DEPTH2BDRK",
                                                     "FIRST_BDRK", "LAST_STRAT", "OHTOPUNIT", "OHBOTUNIT", "CUTTINGS", "CORE",
                                                     "BHGEOPHYS", "GEOCHEM", "WATERCHEM", "OBWELL", "SWL", "DH_VIDEO", "INPUT_SRC", "UNUSED",
                                                     "ENTRY_DATE", "UPDT_DATE", "GEOC_TYPE", "GCM_CODE", "GEOC_SRC", "GEOC_PRG", "UTME", "UTMN",
                                                     "GEOC_ENTRY", "GEOC_DATE", "GEOCUPD_ENTRY", "GEOCUPD_DATE", "RCVD_DATE", "WELL_LABEL",
                                                     "WELLID_1", "SWLCOUNT", "SWLDATE", "SWLAVGMEAS", "SWLAVGELEV", "BDRKELEV", "OHTOPELEV",
                                                     "OHBOTELEV", "BOTHOLELEV", "LOGURL", "STRATURL", "ORIG_FID"])[0]

printit("Recalculating elevation and meas_elev fields using DEM.")
swl_TableSelect_1_ = arcpy.management.CalculateFields(swl_copy_1,"PYTHON3",[["ELEVATION", "!dem!", ""], ["meas_elev", "!dem! - !measuremt!", ""]])[0]

#%% 7 Clean Strat table

printit("Begin cleaning strat table.")

# Copy strat table
printit("Copying strat table.")
strat_copy = os.path.join(workspace, "strat_unloc_copy")
arcpy.management.Copy(strat_table, strat_copy)

#Delete extra Fields
printit("Deleting extra fields from strat table copy.")
strat_copy_1 = arcpy.management.DeleteField(strat_copy, ["OBJECTID_1", "Join_Count", "TARGET_FID", "JOIN_FID",
                                                        "RELATEID_1", "COUNTY_C", "UNIQUE_NO", "WELLNAME", "TOWNSHIP", "RANGE", "RANGE_DIR",
                                                        "SECTION", "SUBSECTION", "MGSQUAD_C", "ELEV_MC", "STATUS_C", "USE_C",
                                                        "LOC_MC", "LOC_SRC", "DATA_SRC", "DEPTH_DRLL", "DEPTH_COMP", "DATE_DRLL",
                                                        "CASE_DIAM", "CASE_DEPTH", "GROUT", "POLLUT_DST", "POLLUT_DIR", "POLLUT_TYP",
                                                        "STRAT_DATE", "STRAT_UPD", "STRAT_SRC", "STRAT_GEOL", "STRAT_MC", "DEPTH2BDRK",
                                                        "FIRST_BDRK", "LAST_STRAT", "OHTOPUNIT", "OHBOTUNIT", "CUTTINGS", "CORE",
                                                        "BHGEOPHYS", "GEOCHEM", "WATERCHEM", "OBWELL", "SWL", "DH_VIDEO", "INPUT_SRC", "UNUSED",
                                                        "ENTRY_DATE", "UPDT_DATE", "GEOC_TYPE", "GCM_CODE", "GEOC_SRC", "GEOC_PRG", "UTME", "UTMN",
                                                        "GEOC_ENTRY", "GEOC_DATE", "GEOCUPD_ENTRY", "GEOCUPD_DATE", "RCVD_DATE", "WELL_LABEL",
                                                        "WELLID_1", "SWLCOUNT", "SWLDATE", "SWLAVGMEAS", "SWLAVGELEV", "BDRKELEV", "OHTOPELEV",
                                                        "OHBOTELEV", "BOTHOLELEV", "LOGURL", "STRATURL", "ORIG_FID"])[0]

#Add Fields
printit("Adding required fields to strat table copy.")
strat_cwi_clean = os.path.join(workspace, "strat_unloc_clean")
arcpy.management.Copy(strat_copy_1, strat_cwi_clean)
strat_cwi_TableSelect_4_ = arcpy.management.AddFields(strat_cwi_clean,[["elev_top", "FLOAT", "", "", "", ""], ["elev_bot", "FLOAT", "", "", "", ""]])[0]

# Calculate new Fields
printit("Calculating elev_top and elev_bot field values.")
strat_cwi_TableSelect_5_ = arcpy.management.CalculateFields(strat_cwi_TableSelect_4_,"PYTHON3",[["elev_top", "!dem! - !depth_top!", ""], ["elev_bot", "!dem! - !depth_bot!", ""]])[0]


#%% 8 Delete temporary files/fields

printit("Deleting temporary files from output geodatabase.")
try:
    arcpy.management.Delete(cons_copy)
    arcpy.management.Delete(dpl_copy)
    arcpy.management.Delete(swl_copy)
    arcpy.management.Delete(strat_copy)

except:
    printit("Warning: unable to delete all temporary files.")
##
#%% 9 Record and print tool end time
toolend = datetime.datetime.now()
toolelapsed = toolend - toolstart
printit('Clean CWI tool completed at {0}. Elapsed time: {1}. You did it!'.format(toolend, toolelapsed))
