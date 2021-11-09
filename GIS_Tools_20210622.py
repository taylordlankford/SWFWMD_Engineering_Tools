import arcpy
import time

############ Version 2 of GIS tools ############
# Create Script tool and allow user to select modules to run
# Update the geodatabase directly, assume it has write capabilities
# move tool and Geodatabase to local drive, ensure geodatabase is compatible with the tool 

arcpy.env.overwriteOutput = True
arcpy.CheckOutExtension("3D")
t0 = time.time()

# Get parameters from user
args = []

for i in range(0,3):
    args.append(arcpy.GetParameter(i))
for i in args:
    arcpy.AddMessage(i)
    # arcpy.AddMessage(type(i))

# root = r'C:\GISDATA\Chass\Chassohowitzka.gdb'  ### USER DEFINED VARIABLE, assume this database has write access
# DEM = r'C:\GISDATA\Chass\DEM_Mosaic\willistonno\N873ChasDEM'   ### USER DEFINED VARIABLE
# ModuleList = ["Landuse Distribution"]

root = arcpy.GetParameterAsText(0)
DEM = arcpy.GetParameterAsText(1)
ModuleList = arcpy.GetParameter(2)


# define feature datasets
HydroNetwork = root + "\\HydroNetwork\\"
Model = root + "\\Model\\"
Watershed = root + "\\Watershed\\"

# Key features from HydroNetwork Feature Dataset
hydroedge = HydroNetwork + "\\HYDROEDGE"
hydrojunction = HydroNetwork + "\\HYDROJUNCTION"
# key features from Model Feature Dataset
basin = Model + "\\ICPR_BASIN"
node = Model + "\\ICPR_NODE"
link = Model + "\\ICPR_LINK"
# key features from Watershed Feature Dataset
landuse = Watershed + "\\GWIS_LANDUSE"
soils = Watershed + "\\GWIS_SOIL"
hep = Watershed + "\\HYDRAULIC_ELEMENT_POINT"
# key features from root directory, support tables
pipe = root + "\\PIPE_BARREL"
weir = root + "\\WEIR"
storage = root + "\\ICPR_NODE_STORAGE"

# Capture spatial reference using feature from geodatabase (state plane west)
spatialprj = arcpy.Describe(node).spatialReference


# stores features that will be deleted at the end and features to add to MXD after tool execution
delList = []
final = []

############ PIPE_BARREL INFO ############
if "Pipe Barrel" in ModuleList:
    arcpy.AddMessage("Running Pipe Barrel Review...")
    xxPipeFlds = ["Slope_Pct", "US_Shape", "DS_Shape", "Mannings"]

    flds = []
    fields = arcpy.ListFields(pipe)
    for i in fields:
        flds.append(i.name)
    # print flds

    # Add new xxPipeFlds to pipe table, check if fields already exist
    for i in xxPipeFlds:
        if i not in flds:
            flds.append(i)
            if i == xxPipeFlds[0]:
                arcpy.AddField_management(pipe, xxPipeFlds[0], field_type="DOUBLE")
            elif i == xxPipeFlds[1]:
                arcpy.AddField_management(pipe, xxPipeFlds[1], field_type="TEXT", field_length="50")
            elif i == xxPipeFlds[2]:
                arcpy.AddField_management(pipe, xxPipeFlds[2], field_type="TEXT", field_length="50")
            elif i == xxPipeFlds[3]:
                arcpy.AddField_management(pipe, xxPipeFlds[3], field_type="TEXT", field_length="50")

    with arcpy.da.UpdateCursor(pipe, flds) as uc:
        for row in uc:
            # Review of pipe slope, upstream and downstream inverts, pipe length
            if row[flds.index("UPSTREAM_INVERT_ELEVATION_MS")] and row[flds.index("DOWNSTREAM_INVERT_ELEVATION_MS")]:
                slope = round(float(((row[flds.index("UPSTREAM_INVERT_ELEVATION_MS")]) - float(row[flds.index("DOWNSTREAM_INVERT_ELEVATION_MS")]))/row[flds.index("PIPE_BARREL_LENGTH_MS")]),4)
                row[flds.index("Slope_Pct")] = round(slope * 100,2)
            # Review pipe shape description, compare against corresponding upstream/downstream rise/span
            if row[flds.index("UPSTREAM_SHAPE_DESC")] == 0:
                if row[flds.index("UPSTREAM_RISE_MS")] == row[flds.index("UPSTREAM_SPAN_MS")]:
                    row[flds.index("US_Shape")] = "Cir, u/s Dim Eql"
                else:
                    row[flds.index("US_Shape")] = "Error UpShape"
            elif row[flds.index("UPSTREAM_SHAPE_DESC")] == 1:
                if row[flds.index("UPSTREAM_RISE_MS")] != row[flds.index("UPSTREAM_SPAN_MS")]:
                    row[flds.index("US_Shape")] = "Hor Ellip, u/s Dim Not Equal"
                else:
                    row[flds.index("US_Shape")] = "Error UpShape"
            # Now for the downstream condition
            if row[flds.index("DOWNSTREAM_SHAPE_DESC")] == 0:
                if row[flds.index("DOWNSTREAM_RISE_MS")] == row[flds.index("DOWNSTREAM_SPAN_MS")]:
                    row[flds.index("DS_Shape")] = "Cir, d/s Dim Eql"
                else:
                    row[flds.index("DS_Shape")] = "Error DownShape"
            elif row[flds.index("DOWNSTREAM_SHAPE_DESC")] == 1:
                if row[flds.index("DOWNSTREAM_RISE_MS")] != row[flds.index("DOWNSTREAM_SPAN_MS")]:
                    row[flds.index("DS_Shape")] = "Hor Ellip, d/s Dim Not Equal"
                else:
                    row[flds.index("DS_Shape")] = "Error DownShape"

            # Continue to add additional shapes, distinguish between horizontal and vertical, etc.
            
            # Manning's Roughness Investigation
            if row[flds.index("MATERIAL_TYPE_DESC")] == "CMP":
                if row[flds.index("UPSTREAM_MANNINGSN_VAL")] == row[flds.index("DOWNSTREAM_MANNINGSN_VAL")]:
                    n = row[flds.index("UPSTREAM_MANNINGSN_VAL")]
                    if n == None:
                        row[flds.index("Mannings")] = "Error, not populated"
                    elif n < 0.022 + 0.02 or n >= 0.022 - 0.02:
                        row[flds.index("Mannings")] = "CMP, Manning's Ok"
                else:
                    row[flds.index("Mannings")] = "Error, Manning's out of Range"
            elif row[flds.index("MATERIAL_TYPE_DESC")] == "RCP":
                if row[flds.index("UPSTREAM_MANNINGSN_VAL")] == row[flds.index("DOWNSTREAM_MANNINGSN_VAL")]:
                    n = row[flds.index("UPSTREAM_MANNINGSN_VAL")]
                    if n == None:
                        row[flds.index("Mannings")] = "Error, not populated"
                    elif n < 0.013 + 0.02 or n >= 0.013 - 0.02:
                        row[flds.index("Mannings")] = "RCP, Manning's Ok"
                else:
                    row[flds.index("Mannings")] = "Error, Manning's out of Range"
            elif row[flds.index("MATERIAL_TYPE_DESC")] == "ABS":
                if row[flds.index("UPSTREAM_MANNINGSN_VAL")] == row[flds.index("DOWNSTREAM_MANNINGSN_VAL")]:
                    n = row[flds.index("UPSTREAM_MANNINGSN_VAL")]
                    if n == None:
                        row[flds.index("Mannings")] = "Error, not populated"
                    elif n < 0.012 + 0.02 or n >= 0.012 - 0.02:
                        row[flds.index("Mannings")] = "ABS, Manning's Ok"
                else:
                    row[flds.index("Mannings")] = "Error, Manning's out of Range"
            elif row[flds.index("MATERIAL_TYPE_DESC")] == "PVC":
                if row[flds.index("UPSTREAM_MANNINGSN_VAL")] == row[flds.index("DOWNSTREAM_MANNINGSN_VAL")]:
                    n = row[flds.index("UPSTREAM_MANNINGSN_VAL")]
                    if n == None:
                        row[flds.index("Mannings")] = "Error, not populated"
                    elif n < 0.012 + 0.02 or n >= 0.012 - 0.02:
                        row[flds.index("Mannings")] = "PVC, Manning's Ok"
                else:
                    row[flds.index("Mannings")] = "Error, Manning's out of Range"
            elif row[flds.index("MATERIAL_TYPE_DESC")] == "STEEL":
                if row[flds.index("UPSTREAM_MANNINGSN_VAL")] == row[flds.index("DOWNSTREAM_MANNINGSN_VAL")]:
                    n = row[flds.index("UPSTREAM_MANNINGSN_VAL")]
                    if n == None:
                        row[flds.index("Mannings")] = "Error, not populated"
                    elif n < 0.012 + 0.02 or n >= 0.012 - 0.02:
                        row[flds.index("Mannings")] = "STEEL, Manning's Ok"
                else:
                    row[flds.index("Mannings")] = "Error, Manning's out of Range"
            elif row[flds.index("MATERIAL_TYPE_DESC")] == "HDPE":
                if row[flds.index("UPSTREAM_MANNINGSN_VAL")] == row[flds.index("DOWNSTREAM_MANNINGSN_VAL")]:
                    n = row[flds.index("UPSTREAM_MANNINGSN_VAL")]
                    if n == None:
                        row[flds.index("Mannings")] = "Error, not populated"
                    elif n < 0.013 + 0.02 or n >= 0.013 - 0.02:
                        row[flds.index("Mannings")] = "HDPE, Manning's Ok"
                else:
                    row[flds.index("Mannings")] = "Error, Manning's out of Range"
            elif row[flds.index("MATERIAL_TYPE_DESC")] == "CLAY":
                if row[flds.index("UPSTREAM_MANNINGSN_VAL")] == row[flds.index("DOWNSTREAM_MANNINGSN_VAL")]:
                    n = row[flds.index("UPSTREAM_MANNINGSN_VAL")]
                    if n == None:
                        row[flds.index("Mannings")] = "Error, not populated"
                    elif n < 0.013 + 0.02 or n >= 0.013 - 0.02:
                        row[flds.index("Mannings")] = "Clay, Manning's Ok"
                else:
                    row[flds.index("Mannings")] = "Error, Manning's out of Range"
            uc.updateRow(row)
    final.append(pipe)

############ GWIS LANDUSE BREAKDOWN ############
if "Landuse Distribution" in ModuleList:
    arcpy.AddMessage("Running Landuse Distribution...")
    # LanduseCollect = [["FLUCCS","Description", "Percent Area"]]
    TotalArea = 0

    # Clip landuse and ICPR_BASIN feature classes
    xxLandClip = root + "\\xxLandClip"
    arcpy.Clip_analysis(in_features=landuse, clip_features=basin, out_feature_class=xxLandClip, cluster_tolerance="")
    delList.append(xxLandClip)

    # Summarize this output based on the FLUCCS Code description
    xxLandTable = root + "\\xxLandTable"
    arcpy.Statistics_analysis(in_table=xxLandClip, out_table=xxLandTable, statistics_fields=[["SHAPE_Area", "SUM"], ["FLUCSDESC", "FIRST"]], case_field=["FLUCCSCODE"])

    # Add field for percent area breakdown
    arcpy.AddField_management(xxLandTable, field_name="Pct_Area", field_type="DOUBLE")

    landflds = []
    fields = arcpy.ListFields(xxLandTable)
    for i in fields:
        landflds.append(i.name)

    # calculate total area of all landuse features
    if "SUM_Shape_Area" in landflds:
        with arcpy.da.SearchCursor(xxLandTable, landflds) as sc:
            for row in sc:
                TotalArea = TotalArea + row[landflds.index("SUM_Shape_Area")]
        # update table with percent area claculations for landuse
        with arcpy.da.UpdateCursor(xxLandTable, landflds) as uc:
            for row in uc:
                row[landflds.index("Pct_Area")] = round(row[landflds.index("SUM_Shape_Area")]/TotalArea*100,2)
                uc.updateRow(row)
    elif "SUM_SHAPE_Area" in landflds:
        with arcpy.da.SearchCursor(xxLandTable, landflds) as sc:
            for row in sc:
                TotalArea = TotalArea + row[landflds.index("SUM_SHAPE_Area")]
        # update table with percent area claculations for landuse
        with arcpy.da.UpdateCursor(xxLandTable, landflds) as uc:
            for row in uc:
                row[landflds.index("Pct_Area")] = round(row[landflds.index("SUM_SHAPE_Area")]/TotalArea*100,2)
                uc.updateRow(row)
    final.append(xxLandTable)

############ GWIS SOILS BREAKDOWN ############
if "Soils Distribution" in ModuleList:
    arcpy.AddMessage("Running Soils Distribution...")
    # SoilsCollect = [["HYDGRP", "Percent Area"]]
    TotalArea = 0

    # Clip landuse and ICPR_BASIN feature classes
    xxSoilsClip = root + "\\xxSoilsClip"
    arcpy.Clip_analysis(in_features=soils, clip_features=basin, out_feature_class=xxSoilsClip, cluster_tolerance="")
    delList.append(xxSoilsClip)

    # Summarize this output based on the FLUCCS Code description
    xxSoilsTable = root + "\\xxSoilsTable"
    arcpy.Statistics_analysis(in_table=xxSoilsClip, out_table=xxSoilsTable, statistics_fields=[["SHAPE_Area", "SUM"], ["HYDGRP", "FIRST"]], case_field=["HYDGRP"])

    # Add field for percent area breakdown
    arcpy.AddField_management(xxSoilsTable, field_name="Pct_Area", field_type="DOUBLE")

    soilflds = []
    fields = arcpy.ListFields(xxSoilsTable)
    for i in fields:
        soilflds.append(i.name)

    if "SUM_Shape_Area" in soilflds:
        # calculate total area of all features
        with arcpy.da.SearchCursor(xxSoilsTable, soilflds) as sc:
            for row in sc:
                TotalArea = TotalArea + row[soilflds.index("SUM_Shape_Area")]
        # update table with percent area claculations
        with arcpy.da.UpdateCursor(xxSoilsTable, soilflds) as uc:
            for row in uc:
                if row[soilflds.index("HYDGRP")] is None or row[soilflds.index("HYDGRP")] == " ":
                    row[soilflds.index("HYDGRP")] = "Oth"
                row[soilflds.index("Pct_Area")] = round(row[soilflds.index("SUM_Shape_Area")]/TotalArea*100,2)
                uc.updateRow(row)
    elif "SUM_SHAPE_Area" in soilflds:
        # calculate total area of all features
        with arcpy.da.SearchCursor(xxSoilsTable, soilflds) as sc:
            for row in sc:
                TotalArea = TotalArea + row[soilflds.index("SUM_SHAPE_Area")]
        # update table with percent area claculations
        with arcpy.da.UpdateCursor(xxSoilsTable, soilflds) as uc:
            for row in uc:
                if row[soilflds.index("HYDGRP")] is None or row[soilflds.index("HYDGRP")] == " ":
                    row[soilflds.index("HYDGRP")] = "Oth"
                row[soilflds.index("Pct_Area")] = round(row[soilflds.index("SUM_SHAPE_Area")]/TotalArea*100,2)
                uc.updateRow(row)
    final.append(xxSoilsTable)

############ ICPR BASIN TIME OF CONCENTRATION REVIEW ############
if "Basin Time of Concentration" in ModuleList:
    arcpy.AddMessage("Running Time of Concentration Analysis...")

    basinflds = []
    fields = arcpy.ListFields(basin)
    for i in fields:
        basinflds.append(i.name)
    # print basinflds

    # check to see if field is in Basinflds list, if not add the field and calculate the area in acres
    if "AREA_ACRES" not in basinflds:
        arcpy.AddMessage("Adding AREA_ACRES field to ICPR_BASIN feature class...")
        arcpy.AddField_management(basin, field_name="AREA_ACRES", field_type="DOUBLE")
        basinflds.append("AREA_ACRES")
    
    # handle both cases depending on what the name of the area field is
    if "Shape_Area" in basinflds:
        with arcpy.da.UpdateCursor(basin, basinflds) as uc:
            for row in uc:
                row[basinflds.index("AREA_ACRES")] = round(row[basinflds.index("Shape_Area")]/43560,2)
                uc.updateRow(row)
    elif "SHAPE_Area" in basinflds:
        with arcpy.da.UpdateCursor(basin, basinflds) as uc:
            for row in uc:
                row[basinflds.index("AREA_ACRES")] = round(row[basinflds.index("SHAPE_Area")]/43560,2)
                uc.updateRow(row)

    # add new field to xxBasin for TC Ratio calculation
    if "TC_Ratio" not in basinflds:
        arcpy.AddField_management(basin, field_name="TC_Ratio", field_type="DOUBLE")
        basinflds.append("TC_Ratio")

    # Search cursor to evaluate TC vs Area relationship
    with arcpy.da.UpdateCursor(basin, basinflds) as uc:
        for row in uc:
            TC = row[basinflds.index("TC")]
            BasinArea = row[basinflds.index("AREA_ACRES")]
            Ratio = round(TC/BasinArea,2)
            row[basinflds.index("TC_Ratio")] = Ratio
            uc.updateRow(row)
    final.append(basin)

# ############ ICPR BASIN DUPLICATE NAME NODENAME REVIEW ############
# arcpy.AddMessage("Running ICPR Basin and Node Duplication Name Analysis...")
# Duplicates = [["BASIN NAME", "NODE NAME", "COUNT"]]

# # Summarize basin based on NAME and NODENAME, want to make sure there are no duplicates here
# xxBasinName = root + "\\xxBasinNameTable"
# arcpy.Statistics_analysis(basin, xxBasinName, "NAME COUNT", "NAME")
# final.append(xxBasinName)

# xxNodeName = root + "\\xxNodeNameTable"
# arcpy.Statistics_analysis(basin, xxNodeName, "NODENAME COUNT", "NODENAME")
# final.append(xxNodeName)

############ HEP and DEM Interpretation Review ############
if "HEP vs DEM" in ModuleList:
    arcpy.AddMessage("Processing HEP info, Comparing to DEM values...")
    # assume the HEP fc is part of a geometric network, create a new table xxHEPReviewTbl
    
    HEPReviewList = ["ID", "DEM", "ElementZ", "Difference"]
    HEPCollect = []
    # Pull DEM surface information at HEP locations
    arcpy.AddSurfaceInformation_3d(hep, DEM, out_property="Z", method="BILINEAR", sample_distance="", z_factor="1", pyramid_level_resolution="0", noise_filtering="")

    hepflds = []
    fields = arcpy.ListFields(hep)
    for i in fields:
        hepflds.append(i.name)
    # print hepflds

    # create new table to then relate back to the Node FC through the NodeName field
    xxHEPReviewTbl = root + "\\xxHEPReviewTbl"
    arcpy.CreateTable_management(root + "\\", "xxHEPReviewTbl")
    
    # Add new node fields to HEP review table, check if fields already exist
    for i in HEPReviewList:
        if i == HEPReviewList[0]:
            # ID, this will be joined with OBJECTID at the end
            arcpy.AddField_management(xxHEPReviewTbl, HEPReviewList[0], field_type="LONG", field_is_nullable="NULLABLE")
        elif i == HEPReviewList[1]:
            # DEM
            arcpy.AddField_management(xxHEPReviewTbl, HEPReviewList[1], field_type="DOUBLE", field_is_nullable="NULLABLE")
            # ElementZ
        elif i == HEPReviewList[2]:
            arcpy.AddField_management(xxHEPReviewTbl, HEPReviewList[2], field_type="DOUBLE", field_is_nullable="NULLABLE")
            # Difference
        elif i == HEPReviewList[3]:
             arcpy.AddField_management(xxHEPReviewTbl, HEPReviewList[3], field_type="DOUBLE", field_is_nullable="NULLABLE")          
        
    # use search cursor to walk through each record in hep feature class, store in hepvalues
    with arcpy.da.SearchCursor(hep, hepflds) as sc:
        for row in sc:
            # if str(row[hepflds.index("ELEMENTZ")]):
            if row[hepflds.index("ELEMENTZ")] == None:
                # arcpy.AddMessage(row[hepflds.index("ELEMENTZ")])
                continue
            else:
                ID = row[hepflds.index("OBJECTID")]
                DEM = row[hepflds.index("Z")]
                ElementZ = row[hepflds.index("ELEMENTZ")]
                DiffVal = round(DEM - ElementZ, 2)
            HEPCollect.append([ID, DEM, ElementZ, DiffVal])

    # Populate the created table with the second entry from PipeCollect onward
    for L in HEPCollect:
        # print L
        with arcpy.da.InsertCursor(xxHEPReviewTbl, HEPReviewList) as ic:
            ic.insertRow(L)

    final.append(hep)
    final.append(xxHEPReviewTbl)

    HEPRelate = root + "\\HEPRelate"
    arcpy.CreateRelationshipClass_management(hep, xxHEPReviewTbl, HEPRelate, "SIMPLE",
                                            "HEP has HEPReviewTbl record", "Attributes and Features from HEP",
                                            "NONE", "ONE_TO_ONE", "NONE", "OBJECTID", "ID")

############ Initial Stage and Stage Area Review ############
if "Node Initial Stages" in ModuleList:
    arcpy.AddMessage("Comparing inital stages with Stage/Area info...")
   
    NodeStageList = ["NodeName", "Stage1", "Area1", "Stage2", "Area2","Stage3", "Area3", "InitialStage", "Difference", "Check"]
    NodeCollect = []
    
    # create new table to then relate back to the Node FC through the NodeName field
    xxNodeStageTbl = root + "\\xxNodeStageTbl"
    arcpy.CreateTable_management(root + "\\", "xxNodeStageTbl")

    nodeflds = []
    fields = arcpy.ListFields(node)
    for i in fields:
        nodeflds.append(i.name)
    # print nodeflds

    # Add new node fields to node table, check if fields already exist
    for i in NodeStageList:
        if i == NodeStageList[0]:
            # NodeName
            arcpy.AddField_management(xxNodeStageTbl, NodeStageList[0], field_type="Text", field_length="10", field_is_nullable="NULLABLE")
        elif i == NodeStageList[1]:
            # Stage1
            arcpy.AddField_management(xxNodeStageTbl, NodeStageList[1], field_type="DOUBLE", field_is_nullable="NULLABLE")
        elif i == NodeStageList[2]:
            # Area1
            arcpy.AddField_management(xxNodeStageTbl, NodeStageList[2], field_type="DOUBLE", field_is_nullable="NULLABLE")
        elif i == NodeStageList[3]:
            # Stage2
            arcpy.AddField_management(xxNodeStageTbl, NodeStageList[3], field_type="DOUBLE", field_is_nullable="NULLABLE")
        elif i == NodeStageList[4]:
            # Area 2
            arcpy.AddField_management(xxNodeStageTbl, NodeStageList[4], field_type="DOUBLE", field_is_nullable="NULLABLE")
        elif i == NodeStageList[5]:
            # Stage3
            arcpy.AddField_management(xxNodeStageTbl, NodeStageList[5], field_type="DOUBLE", field_is_nullable="NULLABLE")
        elif i == NodeStageList[6]:
            # Area3
            arcpy.AddField_management(xxNodeStageTbl, NodeStageList[6], field_type="DOUBLE", field_is_nullable="NULLABLE")
        elif i == NodeStageList[7]:
            # initial stage
            arcpy.AddField_management(xxNodeStageTbl, NodeStageList[7], field_type="DOUBLE", field_is_nullable="NULLABLE")
        elif i == NodeStageList[8]:
            # Difference
            arcpy.AddField_management(xxNodeStageTbl, NodeStageList[8], field_type="DOUBLE", field_is_nullable="NULLABLE")
        elif i == NodeStageList[9]:
            # Check
            arcpy.AddField_management(xxNodeStageTbl, NodeStageList[9], field_type="Text", field_length="50", field_is_nullable="NULLABLE")

    storageflds = []
    fields = arcpy.ListFields(storage)
    for i in fields:
        storageflds.append(i.name)
    # print storageflds


    with arcpy.da.SearchCursor(node, nodeflds) as sc:
        for row in sc:
            storagevalues = []
            # Review of node type to isolate stage area nodes
            if str(row[nodeflds.index("TYPE")]) == "0":
                # capture all variables and analysis results at the end, append to DataCollect list
                NodeName = row[nodeflds.index("NAME")]
                InitialStage = round(row[nodeflds.index("INITIAL_STAGE")],2)
                arcpy.AddMessage(NodeName)
                cnt = 1
                whereclause = "{0} = '{1}'".format(storageflds[1], row[nodeflds.index("NAME")])
                with arcpy.da.SearchCursor(storage, storageflds, whereclause) as SC:
                    for rows in SC:
                        storagevalues.append([rows[storageflds.index("STAGE_VAL")], rows[storageflds.index("AREA_MS")]])
                    storagevalues.sort(key = lambda x: x[0], reverse = False)
                # arcpy.AddMessage(storagevalues)
                TopThree = storagevalues[0:3]
                arcpy.AddMessage(TopThree)
                if not TopThree:
                    arcpy.AddMessage("Storage node has no records")
                    Stage1 = 0
                    Area1 = 0
                    Stage2 = 0
                    Area2 = 0
                    Stage3 = 0
                    Area3 = 0
                    Diff = 0
                    Check = "No Stage Area Records for Node"
                else:
                    Stage1 = TopThree[0][0]
                    Area1 = TopThree[0][1]
                    Stage2 = TopThree[1][0]
                    Area2 = TopThree[1][1]
                    if len(TopThree) > 2:
                        Stage3 = TopThree[2][0]
                        Area3 = TopThree[2][1]
                    else:
                        Stage3 = 0
                        Area3 = 0
                    
                    if row[nodeflds.index("INITIAL_STAGE")] != Stage1:
                        Check = "CheckStage"
                    else:
                        Check = "OK"
                    if Check == "CheckStage":
                        Diff = round(row[nodeflds.index("INITIAL_STAGE")] - Stage1, 2)
                    else:
                        Diff = 0
                # capture all variables and analysis results at the end, append to DataCollect list
                NodeCollect.append([NodeName, Stage1, Area1, Stage2, Area2, Stage3, Area3, InitialStage, Diff, Check])            
    
    # Populate the created table with the second entry from PipeCollect onward
    for L in NodeCollect:
        # print L
        with arcpy.da.InsertCursor(xxNodeStageTbl, NodeStageList) as ic:
            ic.insertRow(L)
    final.append(node)
    final.append(xxNodeStageTbl)

    NodeStorageRelate = root + "\\NodeStorageRelate"
    arcpy.CreateRelationshipClass_management(node, xxNodeStageTbl, NodeStorageRelate, "SIMPLE",
                                            "Node has NodeStageTbl record", "Attributes and Features from Edge",
                                            "NONE", "ONE_TO_ONE", "NONE", "NAME", "NodeName")


# add features to mxd
res = ";".join(final)
# arcpy.AddMessage(res)

# aggregate features to load into mxd when tool is complete
arcpy.SetParameterAsText(3, res)
arcpy.SetParameterAsText(4, res)

############ Cleanup Features that can be deleted ############
for i in delList:
    arcpy.Delete_management(i)

t1 = time.time()
total = t1-t0

print (str(round(total/60,2)) + " min")