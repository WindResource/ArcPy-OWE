"""
Calculate installation or decommissioning costs of offshore substations based on the water depth, and port distance.

Parameters:
- water_depth (float): Water depth at the installation site, in meters.
- port_distance (float): Distance from the installation site to the nearest port, in kilometers.
- oss_capacity (float): Capacity of the offshore substation, in units.
- HVC_type (str, optional): Type of high-voltage converter ('AC' or 'DC'). Defaults to 'AC'.
- operation (str, optional): Type of operation ('inst' for installation or 'deco' for decommissioning). Defaults to 'inst'.

Returns:
- float: Calculated installation or decommissioning costs in Euros.

Coefficients:
- Capacity (u/lift): Capacity of the vessel in units per lift.
- Speed (km/h): Speed of the vessel in kilometers per hour.
- Load time (h/lift): Load time per lift in hours per lift.
- Inst. time (h/u): Installation time per unit in hours per unit.
- Dayrate (keu/d): Dayrate of the vessel in thousands of euros per day.

Vessels:
- SUBV (Self-Unloading Bulk Vessels)
- SPIV (Self-Propelled Installation Vessel)
- HLCV (Heavy-Lift Cargo Vessels)
- AHV (Anchor Handling Vessel)

Notes:
- The function supports both installation and decommissioning operations.
- Costs are calculated based on predefined coefficients for different support structures and vessels.
- If the support structure is unrecognized, the function returns None.
"""
"""
Calculate logistics time and costs for major wind turbine repairs (part of OPEX) based on water depth, port distance, and failure rate for major wind turbine repairs.

Coefficients:
    - Speed (km/h): Speed of the vessel in kilometers per hour.
    - Repair time (h): Repair time in hours.
    - Dayrate (keu/d): Dayrate of the vessel in thousands of euros per day.
    - Roundtrips: Number of roundtrips for the logistics operation.

Returns:
- tuple: Logistics time in hours per year and logistics costs in Euros.
"""
"""
Add new fields to the attribute table if they do not exist.

Parameters:
- layer: The layer to which fields will be added.
- fields_to_add: A list of tuples containing field definitions. Each tuple should contain:
    - Field name (str): The name of the field.
    - Field type (str): The data type of the field.
    - Field label (str): The label or description of the field.

Returns:
None
"""

import arcpy
import numpy as np
import os
import matplotlib.pyplot as plt

def determine_support_structure(water_depth):
    """
    Determines the support structure type based on water depth.

    Returns:
    - str: Support structure type ('monopile', 'jacket', 'floating', or 'default').
    """
    # Define depth ranges for different support structures
    if water_depth < 30:
        return "sandisland"
    elif 30 <= water_depth < 150:
        return "jacket"
    elif 150 <= water_depth:
        return "floating"

def calc_equip_costs(water_depth, support_structure, oss_capacity, HVC_type="AC"):
    """
    Calculates the offshore substation equipment costs based on water depth, capacity, and export cable type.

    Returns:
    - float: Calculated equipment costs.
    """
    # Coefficients for equipment cost calculation based on the support structure and year
    support_structure_coeff = {
        'sandisland': (3.26, 804, 0, 0),
        'jacket': (233, 47, 309, 62),
        'floating': (87, 68, 116, 91)
    }

    equip_coeff = {
        'AC': (22.87, 7.06),
        'DC': (102.93, 31.75)
    }
    
    # Define parameters
    c1, c2, c3, c4 = support_structure_coeff[support_structure]
    
    c5, c6 = equip_coeff[HVC_type]
    
    # Define equivalent electrical power
    equiv_capacity = 0.5 * oss_capacity if HVC_type == "AC" else oss_capacity

    if support_structure == 'sandisland':
        # Calculate foundation costs for sand island
        area_island = (equiv_capacity * 5)
        slope = 0.75
        r_hub = np.sqrt(area_island/np.pi)
        r_seabed = r_hub + (water_depth + 3) / slope
        volume_island = (1/3) * slope * np.pi * (r_seabed ** 3 - r_hub ** 3)
        
        supp_costs = c1 * volume_island + c2 * area_island
    else:
        # Calculate foundation costs for jacket/floating
        supp_costs = (c1 * water_depth + c2 * 1000) * equiv_capacity + (c3 * water_depth + c4 * 1000)
    
    # Power converter costs
    conv_costs = c5 * oss_capacity * int(1e3) + c6 * int(1e6) #* int(1e3)
    equip_costs = supp_costs + conv_costs
    
    return supp_costs, conv_costs, equip_costs

def calc_costs(water_depth, support_structure, port_distance, oss_capacity, HVC_type = "AC", operation = "inst"):
    """
    Calculate installation or decommissioning costs of offshore substations based on the water depth, and port distance.

    Returns:
    - float: Calculated installation or decommissioning costs.
    """
    # Installation coefficients for different vehicles
    inst_coeff = {
        ('sandisland','SUBV'): (20000, 25, 2000, 6000, 15),
        ('jacket' 'PSIV'): (1, 18.5, 24, 96, 200),
        ('floating','HLCV'): (1, 22.5, 10, 0, 40),
        ('floating','AHV'): (3, 18.5, 30, 90, 40)
    }

    # Decommissioning coefficients for different vehicles
    deco_coeff = {
        ('sandisland','SUBV'): (20000, 25, 2000, 6000, 15),
        ('jacket' 'PSIV'): (1, 18.5, 24, 96, 200),
        ('floating','HLCV'): (1, 22.5, 10, 0, 40),
        ('floating','AHV'): (3, 18.5, 30, 30, 40)
    }

    # Choose the appropriate coefficients based on the operation type
    coeff = inst_coeff if operation == 'inst' else deco_coeff

    if support_structure == 'sandisland':
        c1, c2, c3, c4, c5 = coeff[('sandisland','SUBV')]
        # Define equivalent electrical power
        equiv_capacity = 0.5 * oss_capacity if HVC_type == "AC" else oss_capacity
        
        # Calculate installation costs for sand island
        water_depth = max(0, water_depth)
        area_island = (equiv_capacity * 5)
        slope = 0.75
        r_hub = np.sqrt(area_island/np.pi)
        r_seabed = r_hub + (water_depth + 3) / slope
        volume_island = (1/3) * slope * np.pi * (r_seabed ** 3 - r_hub ** 3)
        
        total_costs = ((volume_island / c1) * ((2 * port_distance) / c2) + (volume_island / c3) + (volume_island / c4)) * (c5 * 1000) / 24
        
    elif support_structure == 'jacket':
        c1, c2, c3, c4, c5 = coeff[('jacket' 'PSIV')]
        # Calculate installation costs for jacket
        total_costs = ((1 / c1) * ((2 * port_distance) / c2 + c3) + c4) * (c5 * 1000) / 24
    elif support_structure == 'floating':
        total_costs = 0
        
        # Iterate over the coefficients for floating (HLCV and AHV)
        for vessel_type in [('floating', 'HLCV'), ('floating', 'AHV')]:
            c1, c2, c3, c4, c5 = coeff[vessel_type]
            
            # Calculate installation costs for the current vessel type
            vessel_costs = ((1 / c1) * ((2 * port_distance) / c2 + c3) + c4) * (c5 * 1000) / 24
            
            # Add the costs for the current vessel type to the total costs
            total_costs += vessel_costs
    else:
        total_costs = None
        
    return total_costs

def update_fields():
    """
    Update the attribute table of the Offshore SubStation Coordinates (OSSC) layer.

    Returns:
    - None
    """
    
    # Define the capacities for which fields are to be added
    capacities = [500, 1000, 1500, 2000, 2500]

    # Define the expense categories
    expense_categories = ['Sup', 'Cnv', 'Equ', 'Ins', 'Cap', 'Ope', 'Dec']

    # Define fields to be added if they don't exist
    fields_to_add = [('SuppStruct', 'TEXT')]

    # Generate field definitions for each capacity and expense category for both AC and DC
    for capacity in capacities:
        for category in expense_categories:
            for sub_type in ['AC', 'DC']:
                field_name = f'{category}{capacity}_{sub_type}'
                fields_to_add.append((field_name, 'DOUBLE'))

    # Access the current ArcGIS project
    aprx = arcpy.mp.ArcGISProject("CURRENT")
    map = aprx.activeMap

    # Find the offshore substation layer
    oss_layers = [layer for layer in map.listLayers() if layer.name.startswith('OSSC')]

    # Check if any OSSC layer exists
    if not oss_layers:
        arcpy.AddError("No layer starting with 'OSSC' found in the current map.")
        return

    # Select the first OSSC layer
    oss_layer = oss_layers[0]

    # Deselect all currently selected features
    arcpy.SelectLayerByAttribute_management(oss_layer, "CLEAR_SELECTION")

    arcpy.AddMessage(f"Processing layer: {oss_layer.name}")

    # Check if required fields exist in the attribute table
    fields = arcpy.ListFields(oss_layer)
    field_names = [field.name for field in fields]
    required_fields = ['WaterDepth', 'Distance']
    for field in required_fields:
        if field not in field_names:
            arcpy.AddError(f"Required field '{field}' is missing in the attribute table.")
            return

    # Check if fields to be added already exist
    fields_not_exist = [field_name for field_name, field_type in fields_to_add if field_name not in field_names]

    # Add new fields to the attribute table if they do not exist
    if fields_not_exist:
        arcpy.management.AddFields(oss_layer, fields_to_add)

    # Update each row in the attribute table
    with arcpy.da.UpdateCursor(oss_layer, field_names) as cursor:
        for row in cursor:
            water_depth = row[field_names.index("WaterDepth")]
            port_distance = row[field_names.index("Distance")]

            # Determine and assign Support structure
            support_structure = determine_support_structure(water_depth)
            row[field_names.index('SuppStruct')] = support_structure.capitalize()

            for capacity in capacities:
                for sub_type in ['AC', 'DC']:
                    # Round function
                    def rnd(r):
                        return round(r / int(1e6), 6)

                    # Material Costs
                    supp_costs, conv_costs, equip_costs = calc_equip_costs(water_depth, support_structure, capacity, HVC_type=sub_type)
                    row[field_names.index(f'Sup{capacity}_{sub_type}')] = rnd(supp_costs)
                    row[field_names.index(f'Cnv{capacity}_{sub_type}')] = rnd(conv_costs)
                    row[field_names.index(f'Equ{capacity}_{sub_type}')] = rnd(equip_costs)

                    # Installation and Decommissioning Costs
                    inst_costs = calc_costs(water_depth, support_structure, port_distance, capacity, HVC_type=sub_type, operation="inst")
                    deco_costs = calc_costs(water_depth, support_structure, port_distance, capacity, HVC_type=sub_type, operation="deco")
                    row[field_names.index(f'Ins{capacity}_{sub_type}')] = rnd(inst_costs)
                    row[field_names.index(f'Dec{capacity}_{sub_type}')] = rnd(deco_costs)

                    # Calculate and assign the capital expenses (the sum of the equipment and installation costs)
                    capital_expenses = equip_costs + inst_costs
                    row[field_names.index(f'Cap{capacity}_{sub_type}')] = rnd(capital_expenses)

                    # Calculate and assign operating expenses
                    operating_expenses = 0.03 * conv_costs + 0.015 * supp_costs if support_structure == 'sandisland' else 0.03 * conv_costs
                    row[field_names.index(f'Ope{capacity}_{sub_type}')] = rnd(operating_expenses)

            cursor.updateRow(row)

    arcpy.AddMessage(f"Attribute table of {oss_layer.name} updated successfully.")


if __name__ == "__main__":
    update_fields()







