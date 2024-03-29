import arcpy
import pandas as pd
import pyproj
import time
import os

def lon_lat_to_utm(lon_array, lat_array):
    """
    Convert longitude and latitude coordinates to UTM coordinates.

    Parameters:
        lon_array (numpy.ndarray): Array of longitude values.
        lat_array (numpy.ndarray): Array of latitude values.

    Returns:
        tuple: Tuple containing arrays of UTM x-coordinates and y-coordinates.
    """
    # Define the projection from WGS84 (EPSG:4326) to UTM Zone 33N (EPSG:32633)
    wgs84 = pyproj.Proj(init='epsg:4326')
    utm33n = pyproj.Proj(init='epsg:32633')

    try:
        # Perform the transformation
        x_array, y_array = pyproj.transform(wgs84, utm33n, lon_array, lat_array)
        return x_array, y_array
    except Exception as e:
        arcpy.Addmessage(f"Error occurred during coordinate transformation: {e}")
        return None, None

def identify_countries(point_features):
    """
    Identify the countries based on point features using a predefined feature service URL.

    Parameters:
        point_features (str): Path to the point features.

    Returns:
        str: Path to the modified point features shapefile.
    """
    feature_layer_url = "https://services.arcgis.com/P3ePLMYs2RVChkJx/ArcGIS/rest/services/World_Countries_(Generalized)/FeatureServer/0"
    
    # UTM Zone
    utm_wkid = 32633  # UTM Zone 33N
    
    try:
        # Create feature layer from URL
        countries_layer = arcpy.management.MakeFeatureLayer(feature_layer_url, "countries_layer").getOutput(0)
        
        # Convert the feature layer to a polygon feature layer
        arcpy.management.CopyFeatures(countries_layer, "in_memory\\countries_polygon")

        # Project the feature layer to the specified UTM Zone
        arcpy.management.Project("in_memory\\countries_polygon", "in_memory\\countries_projected", utm_wkid)

        # Perform the first spatial join between the point features and the projected country polygons using "WITHIN" criteria
        arcpy.analysis.SpatialJoin(point_features, "in_memory\\countries_projected", "in_memory\\point_country_join",
                                    join_type="KEEP_ALL", match_option="WITHIN")
        
        # Perform the second spatial join between the points with null country values and country polygons within a certain distance using "CLOSEST" criteria
        arcpy.analysis.SpatialJoin(point_features, "in_memory\\countries_projected", "in_memory\\point_country_join_distance_close",
                                    join_type="KEEP_ALL", match_option="CLOSEST", search_radius="150 Kilometers")
        
        # Add the Country and ISO fields to the original point features
        arcpy.management.AddField(point_features, "Country", "TEXT")
        arcpy.management.AddField(point_features, "ISO", "TEXT")
        
        # Update the "Country" and "ISO" fields from the first spatial join
        with arcpy.da.UpdateCursor(point_features, ["Country", "ISO"]) as update_cursor:
            with arcpy.da.SearchCursor("in_memory\\point_country_join", ["COUNTRY", "ISO"]) as search_cursor:
                for update_row, (country_value, iso_cc_value) in zip(update_cursor, search_cursor):
                        update_row[0] = country_value if country_value else "Unknown"
                        update_row[1] = iso_cc_value if iso_cc_value else "Unknown"
                        update_cursor.updateRow(update_row)

        # Update the "Country" and "ISO" fields from the second spatial join
        with arcpy.da.UpdateCursor(point_features, ["Country", "ISO"]) as update_cursor:
            with arcpy.da.SearchCursor("in_memory\\point_country_join_distance_close", ["COUNTRY", "ISO"]) as search_cursor:
                for update_row, (country_value, iso_cc_value) in zip(update_cursor, search_cursor):
                    if update_row[0] == "Unknown" or update_row[1] == "Unknown":  # Check if Country or ISO is Unknown
                        update_row[0] = str(country_value) if country_value else "Unknown"
                        update_row[1] = str(iso_cc_value) if iso_cc_value else "Unknown"
                        update_cursor.updateRow(update_row)

        return point_features

    except Exception as e:
        import traceback
        arcpy.AddMessage("An error occurred:")
        arcpy.AddMessage(traceback.format_exc())
        return None

def excel_to_shapefile(excel_file: str, highvoltage_vertices_folder: str) -> None:
    """
    Convert data from an Excel file to a shapefile.

    Parameters:
        excel_file (str): Path to the Excel file.
        highvoltage_vertices_folder (str): Path to the output folder for the shapefile.
        feature_layer_url (str): URL of the feature layer containing country boundaries.
    """
    start_time = time.time()
    try:
        arcpy.AddMessage("Reading Excel data...")
        # Read Excel data using pandas
        df = pd.read_excel(excel_file)

        arcpy.AddMessage("Creating output shapefile...")
        # Define the output shapefile path
        output_shapefile = os.path.join(highvoltage_vertices_folder, "highvoltage_vertices.shp")

        # Define the spatial reference for EPSG:32633
        spatial_ref = arcpy.SpatialReference(32633)

        # Create a new shapefile to store the point features with EPSG:32633 spatial reference
        arcpy.management.CreateFeatureclass(highvoltage_vertices_folder, "highvoltage_vertices.shp", "POINT", spatial_reference=spatial_ref)

        arcpy.AddMessage("Adding fields to shapefile...")
        # Define fields to store attributes
        fields = [
            ("Xcoord", "DOUBLE"),
            ("Ycoord", "DOUBLE"),
            ("Type", "TEXT"),
            ("Voltage", "TEXT"),
            ("Frequency", "TEXT")
        ]

        # Add fields to the shapefile
        for field_name, field_type in fields:
            arcpy.management.AddField(output_shapefile, field_name, field_type)

        # Convert lon and lat to UTM (WKID 32633)
        arcpy.AddMessage("Converting longitude and latitude to UTM...")
        lon_array = df['lon'].values
        lat_array = df['lat'].values
        x_array, y_array = lon_lat_to_utm(lon_array, lat_array)

        arcpy.AddMessage("Creating point features and adding to feature class...")
        # Open an insert cursor to add features to the output shapefile
        with arcpy.da.InsertCursor(output_shapefile, ["SHAPE@XY", "Xcoord", "Ycoord", "Type", "Voltage", "Frequency"]) as cursor:
            for i, row in enumerate(df.iterrows()):
                voltage, frequency = row[1]['voltage'], row[1]['frequency']
                typ = row[1]['typ'].capitalize()
                x, y = x_array[i], y_array[i]

                # Check if voltage is null
                if pd.isnull(voltage):
                    voltage = ""

                # Check if frequency is null
                if pd.isnull(frequency):
                    frequency = ""

                # Insert the row with the geometry and attributes
                cursor.insertRow([(x, y), x, y, typ, voltage, frequency])

        arcpy.AddMessage("Identifying countries...")
        # Identify countries and add the country field to the point features
        output_shapefile = identify_countries(output_shapefile)

        arcpy.AddMessage("Adding shapefile to the map...")
        # Add the shapefile to the map
        aprx = arcpy.mp.ArcGISProject("CURRENT")
        map_object = aprx.activeMap
        map_object.addDataFromPath(output_shapefile)

        end_time = time.time()
        arcpy.AddMessage(f"Total processing time: {end_time - start_time} seconds")

    except Exception as e:
        arcpy.AddMessage(f"An error occurred: {e}")

if __name__ == "__main__":
    # Get user parameters
    highvoltage_vertices = arcpy.GetParameterAsText(0)
    highvoltage_vertices_folder = arcpy.GetParameterAsText(1)

    # Call the function to convert Excel to shapefile
    excel_to_shapefile(highvoltage_vertices, highvoltage_vertices_folder)
