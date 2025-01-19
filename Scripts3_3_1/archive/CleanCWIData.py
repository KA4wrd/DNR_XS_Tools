#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Clean CWI Data (verified location wells)
# For use with DNR Cross Section Tools.atbx
# Coded by Kelsey Forward, MN DNR
# Created Date: January 2024


'''
This script cleans up construction and drop pipe CWI data for entry into tools such as Create Conspy and Create 2D points.
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
dpl_x_field = arcpy.GetParameterAsText(3) #UTM x coordinate field in dpl table
dpl_y_field = arcpy.GetParameterAsText(4) #UTM y coordinates field in dpl table
spatial_ref = arcpy.SpatialReference(26915) #NAD 1983 UTM Zone 15N
printit("Variables set with tool parameter inputs.")

# To allow overwriting outputs change overwriteOutput option to True.
arcpy.env.overwriteOutput = True

#%% 4 Clean Construction table

printit("Begin cleaning construction table.")

# Copy construction table
printit("Copying construction table.")
cons_copy = os.path.join(workspace, "cons_copy")
arcpy.management.Copy(cons_table, cons_copy)

#Delete extra Fields
printit("Deleting extra fields from construction table copy.")
cons_copy_1 = arcpy.management.DeleteField(cons_copy, ["diameter", "slot", "length", "material", "amount",
                                                        "units", "OBJECTID", "Join_Count", "TARGET_FID", "JOIN_FID",
                                                        "relateid_1", "unique_no", "wellname", "township", "range", "range_dir",
                                                        "section", "subsection", "mgsquad_c", "elev_mc", "status_c", "use_c",
                                                        "loc_mc", "loc_src", "data_src", "depth_drll", "depth_comp", "date_drll",
                                                        "case_diam", "case_depth", "grout", "pollut_dst", "pollut_dir", "pollut_typ",
                                                        "strat_date", "strat_upd", "strat_src", "strat_geol", "strat_mc", "depth2bdrk",
                                                        "first_bdrk", "last_strat", "ohtopunit", "ohbotunit", "aquifer", "cuttings", "core",
                                                        "bhgeophys", "geochem", "waterchem", "obwell", "swl", "dh_video", "input_src", "unused",
                                                        "entry_date", "updt_date", "geoc_type", "gcm_code", "geoc_src", "geoc_prg", "utme", "utmn",
                                                        "geoc_entry", "geoc_date", "geocupd_entry", "geocupd_date", "rcvd_date", "well_label",
                                                        "wellid_1", "swlcount", "swldate", "swlavgmeas", "swlavgelev", "bdrkelev", "ohtopelev",
                                                        "ohbotelev", "botholelev", "logurl", "straturl", "BUFF_DIST", "ORIG_FID"])[0]

#Table Select (Table Select) (analysis)
printit("Removing non screen or casing records from construction table copy.")
cons_cwi_clean = os.path.join(workspace, "cons_cwi_clean")
arcpy.analysis.TableSelect(cons_copy_1, cons_cwi_clean, "constype = 'C' Or constype = 'S'")

#Add Fields
printit("Adding required fields to construction table copy.")
cons_cwi_TableSelect_4_ = arcpy.management.AddFields(cons_cwi_clean,[["elev_top", "FLOAT", "", "", "", ""], ["elev_bot", "FLOAT", "", "", "", ""]])[0]

#Calculate Null depth_from fields for Casing
printit("Setting null 'depth_from' field values for casing records to zero.")
cons_cwi_TableSelect_3_ = arcpy.management.CalculateField(cons_cwi_TableSelect_4_, "from_depth", "0 if !constype! is 'C' and !from_depth! is None else !from_depth!")[0]

# Calculate new Fields
printit("Calculating elev_top and elev_bot field values.")
cons_cwi_TableSelect_5_ = arcpy.management.CalculateFields(cons_cwi_TableSelect_3_,"PYTHON3",[["elev_top", "!elevation! - !from_depth!", ""], ["elev_bot", "!elevation! - !to_depth!", ""]])[0]


#%% 5 Clean drop pipe data

printit("Begin cleaning drop pipe data.")

# Copy dpl table
printit("Copying drop pipe table.")
dpl_copy = os.path.join(workspace, "dpl_copy")
arcpy.management.Copy(dpl_table, dpl_copy)

# XY Table To Point
printit("Creating dpl_cwi mapview points for input to 2D point tool.")
dpl_cwi_pt = os.path.join(workspace, "dpl_cwi")
arcpy.management.XYTableToPoint(dpl_copy, dpl_cwi_pt, dpl_x_field, dpl_y_field, "",spatial_ref)

#Delete extra Fields
printit("Deleting extra fields from dpl table copy.")
dpl_copy_1 = arcpy.management.DeleteField(dpl_cwi_pt, ["drill_meth", "drill_flud", "hydrofrac", "hffrom", "hfto", "case_mat", "case_joint",
                                                     "case_top", "drive_shoe", "case_type", "screen", "ohtopfeet", "ohbotfeet", "screen_mfg",
                                                     "screen_typ", "ptlss_mfg", "ptlss_mdl", "bsmt_offst", "csg_top_ok","csg_at_grd", "plstc_prot",
                                                     "disinfectd", "pump_inst", "pump_date", "pump_mfg","pump_model", "pump_hp", "pump_volts", "dropp_mat",
                                                     "pump_cpcty","pump_type", "variance", "drllr_name", "entry_date", "updt_date","utme", "utmn",
                                                     "diameter", "slot", "length", "material", "amount", "units",
                                                     "objectid", "Join_Count", "TARGET_FID", "JOIN_FID", "relateid_1", "unique_no", "wellname",
                                                     "township", "range", "range_dir", "section", "subsection", "mgsquad_c", "elev_mc", "status_c",
                                                     "use_c", "loc_mc", "loc_src", "data_src", "depth_drll", "depth_comp", "date_drll", "case_diam",
                                                     "case_depth", "grout", "pollut_dst", "pollut_dir", "pollut_typ", "strat_date", "strat_upd",
                                                     "strat_src", "strat_geol", "strat_mc", "depth2bdrk", "first_bdrk", "last_strat", "ohtopunit",
                                                     "ohbotunit", "aquifer", "cuttings", "core", "bhgeophys", "geochem", "waterchem", "obwell", "swl",
                                                     "dh_video", "input_src", "unused", "entry_date_1", "updt_date_1", "geoc_type", "gcm_code", "geoc_src",
                                                     "geoc_prg", "geoc_entry", "geoc_date", "geocupd_entry", "geocupd_date", "rcvd_date",
                                                     "well_label", "wellid_1", "swlcount", "swldate", "swlavgmeas", "swlavgelev", "bdrkelev", "ohtopelev",
                                                     "ohbotelev", "botholelev", "logurl", "straturl", "BUFF_DIST", "ORIG_FID"])[0]



#%% 6 Delete temporary files/fields

printit("Deleting temporary files from output geodatabase.")
try:
    arcpy.management.Delete(cons_copy)
    arcpy.management.Delete(dpl_copy)

except:
    printit("Warning: unable to delete all temporary files.")
##
#%% 7 Record and print tool end time
toolend = datetime.datetime.now()
toolelapsed = toolend - toolstart
printit('Clean CWI tool completed at {0}. Elapsed time: {1}. You did it!'.format(toolend, toolelapsed))
