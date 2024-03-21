import arcpy
import pandas as pd
import pyproj
import time
import numpy as np

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
        print(f"Error occurred during coordinate transformation: {e}")
        return None, None

def excel_to_shapefile(excel_file: str, highvoltage_vertices_folder: str) -> None:
    """
    Convert data from an Excel file to a shapefile.

    Parameters:
        excel_file (str): Path to the Excel file.
        highvoltage_vertices_folder (str): Path to the output folder for the shapefile.
    """
    start_time = time.time()
    try:
        # Read Excel data using pandas
        read_excel_start = time.time()
        df = pd.read_excel(excel_file)
        read_excel_end = time.time()
        arcpy.AddMessage(f"Reading Excel file took {read_excel_end - read_excel_start} seconds")

        # Extract attribute data
        attributes = df[['lon', 'lat', 'voltage', 'frequency', 'typ']]
    except Exception as e:
        arcpy.AddMessage(f"Error occurred while reading Excel file: {e}")
        return

    # Define the output shapefile path
    output_shapefile = highvoltage_vertices_folder + "\\highvoltage_vertices.shp"
    
    # Define the spatial reference for EPSG:32633
    spatial_ref = arcpy.SpatialReference(32633)

    # Create a new shapefile to store the point features with EPSG:32633 spatial reference
    arcpy.CreateFeatureclass_management(highvoltage_vertices_folder, "highvoltage_vertices.shp", "POINT", spatial_reference=spatial_ref)

    # Define fields to store attributes
    fields = [
        ("Type", "TEXT"),
        ("Xcoord", "DOUBLE"),
        ("Ycoord", "DOUBLE"),
        ("Voltage", "TEXT"),
        ("Frequency", "TEXT")
    ]

    # Add fields to the shapefile
    add_fields_start = time.time()
    for field_name, field_type in fields:
        arcpy.AddField_management(output_shapefile, field_name, field_type)
    add_fields_end = time.time()
    arcpy.AddMessage(f"Adding fields took {add_fields_end - add_fields_start} seconds")

    # Convert lon and lat to UTM (WKID 32633)
    lon_array = df['lon'].values
    lat_array = df['lat'].values
    lon_lat_to_utm_start = time.time()
    x_array, y_array = lon_lat_to_utm(lon_array, lat_array)
    lon_lat_to_utm_end = time.time()
    arcpy.AddMessage(f"Lon-lat to UTM conversion took {lon_lat_to_utm_end - lon_lat_to_utm_start} seconds")

    # Create a list to store the features
    features = []

    # Loop through data to create features
    for i, row in attributes.iterrows():
        voltage, frequency, typ = row['voltage'], row['frequency'], row['typ']
        x, y = x_array[i], y_array[i]

        # Check if voltage is null
        if pd.isnull(voltage):
            # Replace null voltage with a default value (e.g., "Unknown")
            voltage = ""

        # Check if frequency is null
        if pd.isnull(frequency):
            # Replace null frequency with a default value (e.g., "Unknown")
            frequency = ""

        # Create a point geometry
        point = arcpy.Point(x, y)
        point_geometry = arcpy.PointGeometry(point)
        # # Add a message to display point coordinates for diagnostic purposes
        # arcpy.AddMessage(f"Point geometry coordinates: {point_geometry.centroid.X}, {point_geometry.centroid.Y}")

        # Create a feature
        feature = (x, y, voltage, frequency, typ)
        features.append(feature)

    # Insert all features into the shapefile in a single operation
    insert_features_start = time.time()
    with arcpy.da.InsertCursor(output_shapefile, ["SHAPE@XY", "Xcoord", "Ycoord", "Voltage", "Frequency", "Type"]) as cursor:
        for feature in features:
            # Extract coordinate data
            x_coord = float(feature[0])
            y_coord = float(feature[1])

            # Create a point object
            point = arcpy.Point(x_coord, y_coord)

            # Create a point geometry object
            point_geometry = arcpy.PointGeometry(point)

            # Insert the row with the geometry and attributes
            cursor.insertRow([feature[:2]] + list(feature))
    insert_features_end = time.time()
    arcpy.AddMessage(f"Inserting features took {insert_features_end - insert_features_start} seconds")

    # Use arcpy.mp to add the layer to the map
    aprx = arcpy.mp.ArcGISProject("CURRENT")
    map_object = aprx.activeMap

    # Add the layer to the map
    add_layer_start = time.time()
    map_object.addDataFromPath(output_shapefile)
    add_layer_end = time.time()
    arcpy.AddMessage(f"Adding layer to map took {add_layer_end - add_layer_start} seconds")

    end_time = time.time()
    arcpy.AddMessage(f"Total processing time: {end_time - start_time} seconds")

if __name__ == "__main__":
    # Get user parameters
    highvoltage_vertices = arcpy.GetParameterAsText(0)
    highvoltage_vertices_folder = arcpy.GetParameterAsText(1)

    # Call the function to convert Excel to shapefile
    excel_to_shapefile(highvoltage_vertices, highvoltage_vertices_folder)