import re
from arcgis.gis import GIS
from datetime import datetime
import pandas as pd
import numpy as np
import os
import glob
import arcpy
import sys
import time
import shutil
from collections import defaultdict
import traceback

# ---------------------------
# User-configurable constants
# ---------------------------
DEST_FOLDER = r""
MAP_NAME = "Update Chainage"
LAYER_NAME = "Construction_Chainage_Points_25m_Updated_202506011"

# Columns used for date version (you provided this list)
COLUMNS_DATE = [
    "Type", "Referenced CH", "Activity", "Chainage", "Time of Day",
    "Start", "Finish", "Project", "District",
    "Active Status - Month & Year (Start)",
    "Active Status - Month & Year (End)"
]

# Columns used for chainage/construction updates
COLUMNS_CHAINAGE = ["Chainage", "District", "Project", "Construction Status", "Crew"]

# Whether to write available maps/layers to a small log file when lookups fail
WRITE_MAPS_LAYERS_LOG_ON_ERROR = True
MAPS_LAYERS_LOG_PATH = os.path.join(DEST_FOLDER, "maps_layers_log.txt")

# ---------------------------
# Setup & small niceties
# ---------------------------
# Access Geoportal login through ArcGIS Pro
gis = GIS("pro")

# Pandas display settings (helpful for debugging)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
pd.set_option('display.max_colwidth', None)


# ---------------------------
# Utility functions
# ---------------------------
def generate_date():
    return datetime.now().date().strftime("%Y%m%d")


def duplicate_excel_file(src_path, dest_folder=DEST_FOLDER):
    """
    Duplicate an Excel file to a new folder with a date suffix.
    Returns the path to the copied file or None on failure.
    """
    if not os.path.exists(src_path):
        print(f"[duplicate_excel_file] Source file does not exist: {src_path}")
        return None

    date = generate_date()
    file_ext = os.path.splitext(src_path)[1]
    file_name = os.path.basename(src_path)
    file_name_without_ext = os.path.splitext(file_name)[0]
    new_name = f"{file_name_without_ext}_{date}{file_ext}"

    os.makedirs(dest_folder, exist_ok=True)
    dest_path = os.path.join(dest_folder, new_name)

    try:
        copied = shutil.copy(src_path, dest_path)
        print(f"[duplicate_excel_file] File copied successfully to: {copied}")
        return copied
    except Exception as e:
        print(f"[duplicate_excel_file] Error copying file: {e}")
        traceback.print_exc()
        return None


def read_last_three_sheets(excel_file, Sheet_Number):
    """Read the sheets from Sheet_Number: to the end into a dict of DataFrames"""
    xls = pd.ExcelFile(excel_file)
    sheet_names = xls.sheet_names[Sheet_Number:]
    dfs = {sheet: pd.read_excel(xls, sheet_name=sheet) for sheet in sheet_names}
    return dfs


def filtered_excel_spreadsheet(excel_file, Sheet_Number):
    """Alias for reading sheets (keeps parity with your previous naming)"""
    return read_last_three_sheets(excel_file, Sheet_Number)


def merge_sheets_by_keywords(dfs):
    """Merge DataFrames based on keywords in sheet names."""
    keyword_map = {
        "Elizabeth": "Elizabeth",
        "RW": "RW Stage 2",
        "Andrews_Road": "Andrews Road"
    }

    if not dfs or not keyword_map:
        raise ValueError("Both 'dfs' and 'keyword_map' must be provided and not None.")

    merged_dfs = {key: pd.DataFrame() for key in keyword_map.keys()}
    remaining_dfs = {}

    for sheet, df in dfs.items():
        matched = False
        for key, keyword in keyword_map.items():
            if keyword in sheet:
                merged_dfs[key] = pd.concat([merged_dfs[key], df], ignore_index=True)
                matched = True
                break
        if not matched:
            remaining_dfs[sheet] = df

    for key, merged_df in merged_dfs.items():
        if not merged_df.empty:
            remaining_dfs[f"{key}_Merged"] = merged_df

    return remaining_dfs


def _write_maps_layers_log(project, log_path=MAPS_LAYERS_LOG_PATH):
    """Write available maps and layers to a small log file (for debugging)."""
    try:
        lines = []
        lines.append(f"Project: {getattr(project, 'filePath', 'current project')} - {datetime.now().isoformat()}\n")
        for m in project.listMaps():
            lines.append(f"Map: {m.name}\n")
            for lyr in m.listLayers():
                lines.append(f"    Layer: {lyr.name}\n")
        with open(log_path, "a", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n\n")
        print(f"[maps_layers_log] Wrote maps/layers to {log_path}")
    except Exception as e:
        print(f"[maps_layers_log] Failed to write maps/layers log: {e}")


# ---------------------------
# Safe map & layer lookup
# ---------------------------
def get_map_and_layer(map_name=MAP_NAME, layer_name=LAYER_NAME, case_insensitive=True):
    """
    Safely retrieve a map and layer from the current ArcGIS Pro project.
    - case_insensitive: if True, matches names ignoring case
    Returns: (map_obj, layer_obj)
    Raises ValueError if not found.
    """
    p = arcpy.mp.ArcGISProject('current')

    # Prepare comparators
    def match_name(candidate, target):
        if candidate is None:
            return False
        if case_insensitive:
            return candidate.strip().lower() == target.strip().lower()
        else:
            return candidate.strip() == target.strip()

    # Find maps that match exactly (case-insensitive by default)
    maps = [m for m in p.listMaps() if match_name(m.name, map_name)]
    if not maps:
        msg = f"Map '{map_name}' not found. Available maps: {[m.name for m in p.listMaps()]}"
        print(f"[get_map_and_layer] {msg}")
        if WRITE_MAPS_LAYERS_LOG_ON_ERROR:
            _write_maps_layers_log(p)
        raise ValueError(msg)
    if len(maps) > 1:
        print(f"[get_map_and_layer] Warning: Multiple maps named '{map_name}' found. Using the first one.")
    m = maps[0]

    # Find layers within the selected map
    layers = [lyr for lyr in m.listLayers() if match_name(lyr.name, layer_name)]
    if not layers:
        msg = f"Layer '{layer_name}' not found in map '{m.name}'. Available layers: {[lyr.name for lyr in m.listLayers()]}"
        print(f"[get_map_and_layer] {msg}")
        if WRITE_MAPS_LAYERS_LOG_ON_ERROR:
            _write_maps_layers_log(p)
        raise ValueError(msg)
    if len(layers) > 1:
        print(f"[get_map_and_layer] Warning: Multiple layers named '{layer_name}' found. Using the first one.")
    lyr = layers[0]

    print(f"[get_map_and_layer] Found map '{m.name}' and layer '{lyr.name}'.")
    return m, lyr


# ---------------------------
# Column filtering (case-insensitive)
# ---------------------------
def filter_columns(dfs, columns_to_keep):
    """
    Filter DataFrames to keep only specified columns.
    Uses case-insensitive matching to find columns in each sheet.
    Only sheets that contain ALL requested columns are returned.
    """
    print("[filter_columns] Filtering Columns...")
    filtered_dfs = {}

    for sheet, df in dfs.items():
        # build a lowercase -> actual column name map
        cols_lower_map = {col.lower(): col for col in df.columns}
        missing = []
        actual_cols = []
        for wanted in columns_to_keep:
            if wanted.lower() in cols_lower_map:
                actual_cols.append(cols_lower_map[wanted.lower()])
            else:
                missing.append(wanted)

        if missing:
            print(f"[filter_columns] Warning: Sheet '{sheet}' missing columns: {missing}")
            # original behaviour: skip sheets missing any target columns
            continue

        # if we have all columns, select them in the requested order (actual column names)
        filtered_dfs[sheet] = df[actual_cols].copy()

    print(f"[filter_columns] Completed. Sheets kept: {list(filtered_dfs.keys())}")
    return filtered_dfs


# ---------------------------
# GIS memory load & batch updates
# ---------------------------
def load_gis_data_to_memory(feature_layer):
    """
    Load GIS layer data into memory for faster lookups.
    Returns a dictionary mapping (project, chainage) to feature info.
    """
    print("[load_gis_data_to_memory] Loading GIS data to memory for faster processing...")
    gis_data = {}
    # field names used in your earlier code — adjust if your actual fields differ
    fields = ['projectname', 'chainage', 'OBJECTID', 'constructionstatus', 'crew', 'constructionfrontage', 'monthyear']

    try:
        with arcpy.da.SearchCursor(feature_layer, fields) as cursor:
            for row in cursor:
                key = (row[0], row[1])  # (project, chainage)
                gis_data[key] = {
                    'OBJECTID': row[2],
                    'constructionstatus': row[3],
                    'crew': row[4],
                    'constructionfrontage': row[5],
                    'monthyear': row[6]
                }
    except Exception as e:
        print(f"[load_gis_data_to_memory] Error reading feature layer: {e}")
        traceback.print_exc()
        raise

    print(f"[load_gis_data_to_memory] Loaded {len(gis_data)} records to memory.")
    return gis_data


def batch_update_features(feature_layer, updates):
    """
    Perform batch updates to the feature layer for better performance.
    updates: list of dicts with keys depending on type:
      - {'type':'construction', 'object_id':id}
      - {'type':'crew', 'object_id':id, 'crew_value':...}
      - {'type':'active', 'object_id':id, 'active_value':...}
    """
    if not updates:
        print("[batch_update_features] No updates to process.")
        return

    print(f"[batch_update_features] Processing {len(updates)} updates in batch...")

    construction_updates = [u for u in updates if u['type'] == 'construction']
    crew_updates = [u for u in updates if u['type'] == 'crew']
    active_updates = [u for u in updates if u['type'] == 'active']

    if construction_updates:
        update_construction_batch(feature_layer, construction_updates)
    if crew_updates:
        update_crew_batch(feature_layer, crew_updates)
    if active_updates:
        update_active_batch(feature_layer, active_updates)


def update_construction_batch(feature_layer, updates):
    """Batch update construction status to 'Completed' for matching OBJECTIDs (if currently 'Not Completed')."""
    object_ids = {u['object_id'] for u in updates}
    print(f"[update_construction_batch] Updating construction status for OBJECTIDs: {object_ids}")

    try:
        with arcpy.da.UpdateCursor(feature_layer, ['OBJECTID', 'constructionstatus']) as cursor:
            for row in cursor:
                oid = row[0]
                if oid in object_ids and row[1] == "Not Completed":
                    row[1] = "Completed"
                    cursor.updateRow(row)
                    print(f"[update_construction_batch] Updated OBJECTID {oid}: ConstructionStatus -> 'Completed'.")
    except Exception as e:
        print(f"[update_construction_batch] Error updating construction status: {e}")
        traceback.print_exc()


def update_crew_batch(feature_layer, updates):
    """Batch update crew and set constructionfrontage to 'Yes' if crew != 'None' else 'No'."""
    updates_dict = {u['object_id']: u['crew_value'] for u in updates}
    print(f"[update_crew_batch] Updating crew for OBJECTIDs: {list(updates_dict.keys())}")

    try:
        with arcpy.da.UpdateCursor(feature_layer, ['OBJECTID', 'crew', 'constructionfrontage']) as cursor:
            for row in cursor:
                oid = row[0]
                if oid in updates_dict:
                    crew_value = updates_dict[oid]
                    row[1] = crew_value
                    row[2] = "Yes" if crew_value not in (None, "None", "") else "No"
                    cursor.updateRow(row)
                    print(f"[update_crew_batch] Updated OBJECTID {oid}: crew='{row[1]}', constructionfrontage='{row[2]}'.")
    except Exception as e:
        print(f"[update_crew_batch] Error updating crew: {e}")
        traceback.print_exc()


def update_active_batch(feature_layer, updates):
    """Batch update monthyear (active) field for OBJECTIDs."""
    updates_dict = {u['object_id']: u['active_value'] for u in updates}
    print(f"[update_active_batch] Updating active month/year for OBJECTIDs: {list(updates_dict.keys())}")

    try:
        with arcpy.da.UpdateCursor(feature_layer, ['OBJECTID', 'monthyear']) as cursor:
            for row in cursor:
                oid = row[0]
                if oid in updates_dict:
                    row[1] = updates_dict[oid]
                    cursor.updateRow(row)
                    print(f"[update_active_batch] Updated OBJECTID {oid}: monthyear='{row[1]}'.")
    except Exception as e:
        print(f"[update_active_batch] Error updating active values: {e}")
        traceback.print_exc()


# ---------------------------
# Matching functions (optimized)
# ---------------------------
def match_chainage_project_optimized(dfs, feature_layer):
    """
    Match Project & Chainage pairs from DataFrames to features (loaded in memory),
    collect updates, then perform batch updates.
    """
    print("[match_chainage_project_optimized] Starting optimized chainage project matching...")
    gis_data = load_gis_data_to_memory(feature_layer)
    all_updates = []

    for sheet_name, df in dfs.items():
        if "Project" not in df.columns or "Chainage" not in df.columns:
            print(f"[match_chainage_project_optimized] Skipping sheet '{sheet_name}': Missing required columns")
            continue

        print(f"[match_chainage_project_optimized] Processing sheet: {sheet_name}")
        for _, row in df.iterrows():
            project_value = row['Project']
            chainage_value = row['Chainage']
            crew_value = row.get('Crew', None)

            key = (project_value, chainage_value)
            if key in gis_data:
                feature_info = gis_data[key]
                object_id = feature_info['OBJECTID']
                print(f"[match_chainage_project_optimized] Match found: Project: {project_value}, Chainage: {chainage_value}, OBJECTID: {object_id}")

                if feature_info['constructionstatus'] == "Not Completed":
                    all_updates.append({'type': 'construction', 'object_id': object_id})

                if crew_value is not None:
                    all_updates.append({'type': 'crew', 'object_id': object_id, 'crew_value': crew_value})
            else:
                print(f"[match_chainage_project_optimized] No match found for Project: {project_value}, Chainage: {chainage_value}")

    batch_update_features(feature_layer, all_updates)
    print(f"[match_chainage_project_optimized] Completed processing. Total updates: {len(all_updates)}")


def match_chainage_project_date_optimized(dfs, feature_layer):
    """
    Optimized version for date (monthyear) updates.
    """
    print("[match_chainage_project_date_optimized] Starting optimized date matching...")
    gis_data = load_gis_data_to_memory(feature_layer)
    all_updates = []

    for sheet_name, df in dfs.items():
        if "Project" not in df.columns or "Chainage" not in df.columns:
            print(f"[match_chainage_project_date_optimized] Skipping sheet '{sheet_name}': Missing required columns")
            continue

        print(f"[match_chainage_project_date_optimized] Processing sheet: {sheet_name}")
        for _, row in df.iterrows():
            project_value = row['Project']
            chainage_value = row['Chainage']
            active_value = row.get('Active Status - Month & Year (Start)', None)

            key = (project_value, chainage_value)
            if key in gis_data:
                feature_info = gis_data[key]
                object_id = feature_info['OBJECTID']
                print(f"[match_chainage_project_date_optimized] Match found: Project: {project_value}, Chainage: {chainage_value}, OBJECTID: {object_id}")

                if active_value is not None and active_value != feature_info['monthyear']:
                    all_updates.append({'type': 'active', 'object_id': object_id, 'active_value': active_value})
            else:
                print(f"[match_chainage_project_date_optimized] No match found for Project: {project_value}, Chainage: {chainage_value}")

    batch_update_features(feature_layer, all_updates)
    print(f"[match_chainage_project_date_optimized] Completed date processing. Total updates: {len(all_updates)}")


# ---------------------------
# High-level processing wrappers
# ---------------------------
def process_excel_and_select_layer(excel_path, Sheet_Number, Merge_Sheets=False,
                                   dest_folder=DEST_FOLDER, map_name=MAP_NAME, layer_name=LAYER_NAME,
                                   columns_to_keep=COLUMNS_CHAINAGE):
    """
    Duplicates an Excel spreadsheet, processes its data, and selects a layer in ArcGIS Pro.

    Returns: (filtered_dfs, layer_object) or (None, None) on error.
    """
    print("[process_excel_and_select_layer] Starting Excel processing...")
    active_excel = duplicate_excel_file(excel_path, dest_folder)
    if not active_excel:
        return None, None

    print("[process_excel_and_select_layer] Reading Excel sheets...")
    dfs = read_last_three_sheets(active_excel, Sheet_Number)

    if Merge_Sheets:
        print("[process_excel_and_select_layer] Merging sheets by keywords...")
        dfs = merge_sheets_by_keywords(dfs)

    print("[process_excel_and_select_layer] Filtering columns...")
    filtered_dfs = filter_columns(dfs, columns_to_keep)

    print("[process_excel_and_select_layer] Accessing ArcGIS Pro project...")
    try:
        m, lyr = get_map_and_layer(map_name, layer_name)
        # small, forced delay (keeps behaviour matching your previous script)
        print("[process_excel_and_select_layer] 4 second delay before returning layer...")
        time.sleep(4)
        print("[process_excel_and_select_layer] Successfully accessed ArcGIS layer.")
    except Exception as e:
        print(f"[process_excel_and_select_layer] Error accessing ArcGIS layer: {e}")
        return None, None

    return filtered_dfs, lyr


def process_excel_and_select_layer_date(excel_path, Sheet_Number,
                                        dest_folder=DEST_FOLDER, map_name=MAP_NAME, layer_name=LAYER_NAME,
                                        columns_to_keep=COLUMNS_DATE):
    """
    Duplicates an Excel spreadsheet, processes its data, and selects a layer in ArcGIS Pro (date version).
    Returns: (filtered_dfs, layer_object) or (None, None) on error.
    """
    print("[process_excel_and_select_layer_date] Starting date Excel processing...")
    active_excel = duplicate_excel_file(excel_path, dest_folder)
    if not active_excel:
        return None, None

    print("[process_excel_and_select_layer_date] Reading Excel sheets...")
    dfs = filtered_excel_spreadsheet(active_excel, Sheet_Number)

    print("[process_excel_and_select_layer_date] Filtering columns...")
    filtered_dfs = filter_columns(dfs, columns_to_keep)

    print("[process_excel_and_select_layer_date] Accessing ArcGIS Pro project...")
    try:
        m, lyr = get_map_and_layer(map_name, layer_name)
        print("[process_excel_and_select_layer_date] 4 second delay before returning layer...")
        time.sleep(4)
        print("[process_excel_and_select_layer_date] Successfully accessed ArcGIS layer.")
    except Exception as e:
        print(f"[process_excel_and_select_layer_date] Error accessing ArcGIS layer: {e}")
        return None, None

    return filtered_dfs, lyr


# ---------------------------
# Main execution path
# ---------------------------
def run_processing():
    """Main processing function with error handling and timing."""
    # Excel file paths (as you had them)
    excel_paths = {
        'riverlea': r"",
        'roseworthy': r"",
        'angle_vale': r"",
        'munno_para': r"",
        'schedule': r""
    }

    start_time = time.time()

    try:
        print("=" * 60)
        print("STARTING OPTIMIZED PROCESSING")
        print("=" * 60)
        
        # Riverlea processing (currently active)
        print("\n[run_processing] Processing Riverlea...")
        filtered_dfs, lyr = process_excel_and_select_layer(
            excel_paths['riverlea'],
            Sheet_Number=-2,
            Merge_Sheets=True
        )

        if filtered_dfs and lyr:
            match_chainage_project_optimized(filtered_dfs, lyr)
        else:
            print("[run_processing] Failed to process Riverlea data")

          # Angle Vale Stage 1
#         print("\n[run_processing] Processing Angle Vale...")
#         filtered_dfs, lyr = process_excel_and_select_layer(
#             excel_paths['angle_vale'],
#             Sheet_Number=-5,
#             Merge_Sheets=False
#         )
#         if filtered_dfs and lyr:
#             match_chainage_project_optimized(filtered_dfs, lyr)

        # Uncomment/modify other processing as needed (example placeholders)
        # Roseworthy
        # print("\n[run_processing] Processing Roseworthy...")
        # filtered_dfs, lyr = process_excel_and_select_layer(
        #     excel_paths['roseworthy'],
        #     Sheet_Number=-4,
        #     Merge_Sheets=False
        # )
        # if filtered_dfs and lyr:
        #     match_chainage_project_optimized(filtered_dfs, lyr)

        # Munno Para & Roseworthy Stage 2
#         print("\n[run_processing] Processing Munno Para...")
#         filtered_dfs, lyr = process_excel_and_select_layer(
#             excel_paths['munno_para'],
#             Sheet_Number=-9,
#             Merge_Sheets=True
#         )
#         if filtered_dfs and lyr:
#             match_chainage_project_optimized(filtered_dfs, lyr)

        # Date processing (example)
        # print("\n[run_processing] Processing dates...")
        # filtered_dfs, lyr = process_excel_and_select_layer_date(
        #     excel_paths['schedule'],
        #     Sheet_Number=-1
        # )
        # if filtered_dfs and lyr:
        #     match_chainage_project_date_optimized(filtered_dfs, lyr)

        end_time = time.time()
        total_time = end_time - start_time

        print("=" * 60)
        print("PROCESSING COMPLETED SUCCESSFULLY")
        print(f"Total execution time: {total_time:.2f} seconds")
        print("=" * 60)

    except Exception as e:
        print(f"[run_processing] Error during processing: {str(e)}")
        traceback.print_exc()

    finally:
        print("[run_processing] Cleaning up resources...")
        import gc
        gc.collect()


if __name__ == "__main__":
    run_processing()
