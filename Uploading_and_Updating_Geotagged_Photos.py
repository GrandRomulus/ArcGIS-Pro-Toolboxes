import os
import shutil
from datetime import datetime
from pathlib import Path
from PIL import Image
from PIL.ExifTags import TAGS
import re
import arcpy
import stat
import time
from arcgis.gis import GIS

def generate_date():
    # Get today's date without the time component
    return datetime.now().date().strftime("%Y%m%d")

datetimecreated = generate_date()

# --- HELPERS ---
def is_date_folder(folder_name):
    return re.fullmatch(r"\d{4}-\d{2}-\d{2}", folder_name) is not None

def get_exif_date(image_path):
    try:
        with Image.open(image_path) as img:
            exif_data = img._getexif()
            if exif_data:
                for tag_id, val in exif_data.items():
                    tag = TAGS.get(tag_id, tag_id)
                    if tag == 'DateTimeOriginal':
                        return datetime.strptime(val, "%Y:%m:%d %H:%M:%S")
    except Exception as e:
        print(f"Error reading EXIF for {image_path.name}: {e}")
    return None

def get_photo_date(image_path):
    exif_date = get_exif_date(image_path)
    if exif_date:
        return exif_date
    return datetime.fromtimestamp(image_path.stat().st_mtime)

def time_of_day(photo_datetime):
    if not photo_datetime:
        return None
    # Extract the hour from the photo's timestamp
    hour = photo_datetime.hour
    if 18 <= hour or hour < 6:  # Between 6 PM and 6 AM
        return 'Night'
    else:
        return 'Day'

def handle_remove_readonly(func, path, exc):
    os.chmod(path, stat.S_IWRITE)
    func(path)

# --- MAIN FUNCTION ---
def organize_and_geotag(GDB_PATH):
    
    # --- SETTINGS ---
    # Add root folder directory as needed
    root_dir = Path(fr"")
    TEMP_FOLDER = ROOT_DIR / "Temp_Folder"
    gdb_output_path = GDB_PATH

    map_name = "Geotagged_Site_Photos_V1"
    layer_name = "Geotagged_Site_Photos"

    p = arcpy.mp.ArcGISProject('current')
    m = p.listMaps(map_name)[0]
    
    photos_to_process = []
    folder_name_map = {}

    # Create temp folder
    TEMP_FOLDER.mkdir(exist_ok=True)
    print(f"📁 Temp folder created at {TEMP_FOLDER}")

    # Step 1: Recursively find all valid images not in date-named folders
    for dirpath, dirnames, filenames in os.walk(root_dir):
        current_folder = Path(dirpath)
        if is_date_folder(current_folder.name):
            continue

        for filename in filenames:
            if Path(filename).suffix.lower() not in [".jpg", ".jpeg", ".png"]:
                continue

            image_path = current_folder / filename
            if not is_date_folder(image_path.parent.name):
                photos_to_process.append(image_path)
                
                original_folder_name = image_path.parent.name
                modified_folder_name = original_folder_name.replace(" ", "_")
                folder_name_map[modified_folder_name] = original_folder_name

    print(f"📷 Found {len(photos_to_process)} photos to process.")

    # Step 2: Rename, copy to temp folder + move to date folder
    for photo_path in photos_to_process:
        try:
            # Folder name modification (used for renaming and field population)
            original_folder_name = photo_path.parent.name
            modified_folder_name = original_folder_name.replace(" ", "_")  # for file renaming
            new_filename = f"{modified_folder_name}_{photo_path.name}"
            new_temp_path = TEMP_FOLDER / new_filename

            # Copy to temp folder
            shutil.copy2(photo_path, new_temp_path)

            # Determine target folder and move original file (renamed) there
            photo_date = get_photo_date(photo_path)
            target_folder = photo_path.parent / photo_date.strftime("%Y-%m-%d")
            target_folder.mkdir(exist_ok=True)

            renamed_photo_path = target_folder / new_filename
            shutil.move(str(photo_path), renamed_photo_path)

            print(f"📦 Renamed & moved: {photo_path.name} → {renamed_photo_path}")
        except Exception as e:
            print(f"❌ Failed to handle {photo_path.name}: {e}")

    # Step 3: Run GeoTaggedPhotosToPoints on the temp folder
    if any(TEMP_FOLDER.iterdir()):
        try:
            print(f"🧭 Running GeoTaggedPhotosToPoints on temp folder...")
            geotagged_process = arcpy.management.GeoTaggedPhotosToPoints(
                str(TEMP_FOLDER),
                gdb_output_path,
                None,
                "ONLY_GEOTAGGED",
                "ADD_ATTACHMENTS"
            )
            #arcpy.management.Append(geotagged_process, "Geotagged Site Photos", "NO_TEST", r'path "Path" true true false 5000 Text 0 0,First,#,Enter_Folder_Path_Here,Name,0,5000;datetime "DateTime" true true false 29 Date 0 0,First,#,Enter_GDB_Folder_Path_And_Layer_Name_Here,DateTime,-1,-1;direction "Direction" true true false 0 Double 0 0,First,#,Enter_GDB_Folder_Path_And_Layer_Name_Here,Direction,-1,-1;x "X" true true false 0 Double 0 0,First,#,Enter_GDB_Folder_Path_And_Layer_Name_Here,X,-1,-1;y "Y" true true false 0 Double 0 0,First,#,Enter_GDB_Folder_Path_And_Layer_Name_Here,Y,-1,-1;z "Z" true true false 0 Double 0 0,First,#,Enter_GDB_Folder_Path_And_Layer_Name_Here,Z,-1,-1;district "District" true true false 255 Text 0 0,First,#,Enter_GDB_Folder_Path_And_Layer_Name_Here,District,0,255;time "Time of Day" true true false 255 Text 0 0,First,#,Enter_GDB_Folder_Path_And_Layer_Name_Here,Time,0,255', '', '')
            print(f"✅ GeoTagged photos exported to: {gdb_output_path}")
        except Exception as e:
            print(f"❌ GeoTaggedPhotosToPoints failed: {e}")

        # Step 3b: Add 'District' field and populate it from the original (unmodified) folder name
        try:
            fc = gdb_output_path
            existing_fields = [f.name for f in arcpy.ListFields(fc)]
            if 'District' not in existing_fields:
                arcpy.AddField_management(fc, 'District', 'TEXT')
                print("🛠️ Added 'District' field.")

            def update_district_field():
                updated_count = 0
                with arcpy.da.UpdateCursor(fc, ['Name', 'District']) as cursor:
                    for row in cursor:
                        filename = row[0]
                        match = re.match(r"([^_]+)_", filename)
                        if match:
                            sanitized_prefix = match.group(1)
                            original_folder_name = folder_name_map.get(sanitized_prefix, sanitized_prefix)
                            row[1] = original_folder_name
                            cursor.updateRow(row)
                            updated_count += 1
                return updated_count

            try:
                count = update_district_field()
                print(f"✅ Updated {count} records with folder name in 'District' field.")
            except Exception as cursor_error:
                print(f"⚠️ Cursor failed outside edit session: {cursor_error}")
                print("🔄 Trying within arcpy.da.Editor session...")

                workspace = os.path.dirname(gdb_output_path)
                with arcpy.da.Editor(workspace) as edit:
                    count = update_district_field()
                    print(f"✅ Updated {count} records with folder name in 'District' field (in edit session).")

        except Exception as e:
            print(f"❌ Failed to update 'District' field: {e}")

        # Step 4: Add 'Time' field and populate it based on photo time
        try:
            fc = gdb_output_path
            existing_fields = [f.name for f in arcpy.ListFields(fc)]
            if 'Time' not in existing_fields:
                arcpy.AddField_management(fc, 'Time', 'TEXT')
                print("🛠️ Added 'Time' field.")

            def update_time_field():
                updated_count = 0
                with arcpy.da.UpdateCursor(fc, ['Name', 'Time', 'DateTime']) as cursor:
                    for row in cursor:
                        filename = row[0]
                        photo_datetime = row[2]  # Assuming DateTime field is the timestamp
                        time_of_day_result = time_of_day(photo_datetime)
                        row[1] = time_of_day_result  # 'Day' or 'Night'
                        cursor.updateRow(row)
                        updated_count += 1
                return updated_count

            try:
                count = update_time_field()
                print(f"✅ Updated {count} records with 'Time' (Day/Night) field.")
            except Exception as cursor_error:
                print(f"⚠️ Cursor failed: {cursor_error}")
                print("🔄 Trying within arcpy.da.Editor session...")

                workspace = os.path.dirname(gdb_output_path)
                with arcpy.da.Editor(workspace) as edit:
                    count = update_time_field()
                    print(f"✅ Updated {count} records with 'Time' (Day/Night) field (in edit session).")

        except Exception as e:
            print(f"❌ Failed to update 'Time' field: {e}")

    else:
        print("⚠️ No photos in temp folder to geotag.")

    # Step 5: Delete temp folder with retry & permission fix
    for attempt in range(3):
        try:
            shutil.rmtree(TEMP_FOLDER, onerror=handle_remove_readonly)
            print(f"🗑️ Temp folder deleted: {TEMP_FOLDER}")
            break
        except Exception as e:
            print(f"⚠️ Attempt {attempt+1} to delete temp folder failed: {e}")
            time.sleep(1)
    else:
        print(f"❌ Failed to delete temp folder after multiple attempts: {TEMP_FOLDER}")

    print("\n✅ Finished processing all photos.")

GDB_PATH = fr"Enter_GDB_Path_{datetimecreated}"
filename_output = f"Site_Visit_Photos_{datetimecreated}"

# --- RUN ---
organize_and_geotag(GDB_PATH)
overwrite_and_update_webmap(GDB_PATH, filename_output)
