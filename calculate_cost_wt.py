import arcpy
import os

def present_value(equip_cost, inst_cost, ope_cost_yearly, deco_cost):
    """
    Calculate the total present value of cable cost.

    Parameters:
        equip_cost (float): Equipment cost.
        inst_cost (float): Installation cost.
        ope_cost_yearly (float): Yearly operational cost.
        deco_cost (float): Decommissioning cost.

    Returns:
        float: Total present value of cost.
    """
    # Define years for installation, operational, and decommissioning
    inst_year = 0  # First year (installation year)
    ope_year = inst_year + 5  # Operational costs start year
    dec_year = ope_year + 25  # Decommissioning year
    end_year = dec_year + 2  # End year

    # Discount rate
    discount_rate = 0.05

    # Initialize total operational cost
    total_ope_cost = 0

    # Adjust cost for each year
    for year in range(inst_year, end_year + 1):
        discount_factor = (1 + discount_rate) ** -year  # Calculate the discount factor for the year
        if year == inst_year:
            equip_cost *= discount_factor  # Discount equipment cost for the installation year
            inst_cost *= discount_factor  # Discount installation cost for the installation year
        elif ope_year <= year < dec_year:
            total_ope_cost += ope_cost_yearly * discount_factor  # Accumulate discounted operational cost for each year
        elif year == dec_year:
            deco_cost *= discount_factor  # Discount decommissioning cost for the decommissioning year

    # Calculate total present value of cost
    total_cost = equip_cost + inst_cost + total_ope_cost + deco_cost

    return total_cost

def supp_struct_cond(water_depth):
    """
    Determines the support structure type based on water depth.

    Parameters:
        water_depth (float): Water depth at the turbine location.

    Returns:
        str: Support structure type ('monopile', 'jacket', 'floating').
    """
    if water_depth < 25:
        return "monopile"
    elif 25 <= water_depth < 55:
        return "jacket"
    elif 55 <= water_depth:
        return "floating"

def calc_equip_cost(water_depth, support_structure, ice_cover, turbine_capacity):
    """
    Calculates the equipment cost based on water depth, support structure, ice cover, and turbine capacity.

    Parameters:
        water_depth (float): Water depth at the turbine location.
        support_structure (str): Type of support structure.
        ice_cover (int): Indicator if the area is ice-covered (1 for Yes, 0 for No).
        turbine_capacity (float): Capacity of the turbine.

    Returns:
        tuple: Calculated support structure cost and turbine cost.
    """
    support_structure_coeff = {
        'monopile': (181, 552, 370),
        'jacket': (103, -2043, 478),
        'floating': (0, 697, 1223)
    }

    turbine_coeff = 1200 * 1e3  # Coefficient for turbine cost (eu/MW)

    c1, c2, c3 = support_structure_coeff[support_structure]  # Get coefficients for the support structure
    supp_cost = turbine_capacity * (c1 * (water_depth ** 2) + c2 * water_depth + c3 * 1000)
    
    if ice_cover == 1:
        supp_cost *= 1.10  # Increase cost by 10% if ice cover is present

    turbine_cost = turbine_capacity * turbine_coeff

    return supp_cost, turbine_cost

def calc_inst_deco_cost(water_depth, port_distance, turbine_capacity, operation):
    """
    Calculate installation or decommissioning cost based on the water depth, port distance,
    and rated power of the wind turbines.

    Parameters:
        water_depth (float): Water depth at the turbine location.
        port_distance (float): Distance to the port.
        turbine_capacity (float): Capacity of the turbine.
        operation (str): Type of operation ('installation' or 'decommissioning').

    Returns:
        float: Calculated cost in Euros.
    """
    inst_coeff = {
        'PSIV': (40 / turbine_capacity, 18.5, 24, 144, 200),
        'Tug': (0.3, 7.5, 5, 0, 2.5),
        'AHV': (7, 18.5, 30, 90, 40)
    }

    deco_coeff = {
        'PSIV': (40 / turbine_capacity, 18.5, 24, 144, 200),
        'Tug': (0.3, 7.5, 5, 0, 2.5),
        'AHV': (7, 18.5, 30, 30, 40)
    }

    coeff = inst_coeff if operation == 'installation' else deco_coeff  # Choose coefficients based on operation type

    support_structure = supp_struct_cond(water_depth)

    if support_structure in ['monopile', 'jacket']:
        c1, c2, c3, c4, c5 = coeff['PSIV']
        total_cost = ((1 / c1) * ((2 * port_distance) / c2 + c3) + c4) * ((c5 * 1e3) / 24)
    elif support_structure == 'floating':
        total_cost = 0
        for vessel_type in ['Tug', 'AHV']:
            c1, c2, c3, c4, c5 = coeff[vessel_type]
            vessel_cost = ((1 / c1) * ((2 * port_distance) / c2 + c3) + c4) * ((c5 * 1e3) / 24)
            total_cost += vessel_cost

    return total_cost

def calculate_costs(water_depth, ice_cover, port_distance, turbine_capacity):
    """
    Calculate various costs for a given set of parameters.

    Parameters:
        water_depth (float): Water depth at the turbine location.
        ice_cover (int): Indicator if the area is ice-covered (1 for Yes, 0 for No).
        port_distance (float): Distance to the port.
        turbine_capacity (float): Capacity of the turbine.

    Returns:
        tuple: Total cost, equipment cost, installation cost, total operational cost, decommissioning cost in millions of Euros.
    """
    support_structure = supp_struct_cond(water_depth)  # Determine support structure

    supp_cost, turbine_cost = calc_equip_cost(water_depth, support_structure, ice_cover, turbine_capacity)  # Calculate equipment cost

    equip_cost = supp_cost + turbine_cost
    
    inst_cost = calc_inst_deco_cost(water_depth, port_distance, turbine_capacity, "installation")  # Calculate installation cost
    deco_cost = calc_inst_deco_cost(water_depth, port_distance, turbine_capacity, "decommissioning")  # Calculate decommissioning cost

    ope_cost_yearly = 0.025 * turbine_cost  # Calculate yearly operational cost

    total_cost = present_value(equip_cost, inst_cost, ope_cost_yearly, deco_cost)  # Calculate present value of cost

    total_cost *= 1e-6  # Convert cost to millions of Euros

    return total_cost

def update_fields():
    """
    Function to update the fields in the wind turbine layer with calculated total cost.
    """
    # Get the current map
    aprx = arcpy.mp.ArcGISProject("CURRENT")
    map = aprx.activeMap
    
    # Find the wind turbine layer in the map
    turbine_layer = next((layer for layer in map.listLayers() if layer.name.startswith('WTC')), None)
    
    # Check if the turbine layer exists
    if not turbine_layer:
        arcpy.AddError("No layer starting with 'WTC' found in the current map.")
        return

    # Deselect all currently selected features
    arcpy.SelectLayerByAttribute_management(turbine_layer, "CLEAR_SELECTION")
    
    arcpy.AddMessage(f"Processing layer: {turbine_layer.name}")

    # Check if required fields exist in the attribute table using a search cursor
    required_fields = ['WaterDepth', 'Capacity', 'Distance', 'IceCover']
    existing_fields = []
    
    with arcpy.da.SearchCursor(turbine_layer, ["*"]) as cursor:
        existing_fields = cursor.fields
    
    for field in required_fields:
        if field not in existing_fields:
            arcpy.AddError(f"Required field '{field}' is missing in the attribute table.")
            return

    # Check if TotalCost field exists, create it if it doesn't
    total_cost_field = 'TotalCost'
    if total_cost_field not in existing_fields:
        arcpy.AddField_management(turbine_layer, total_cost_field, "DOUBLE")
        arcpy.AddMessage(f"Field '{total_cost_field}' added to the attribute table.")

    # Calculate the total cost for each feature and update the attribute table
    with arcpy.da.UpdateCursor(turbine_layer, ['WaterDepth', 'Capacity', 'Distance', 'IceCover', total_cost_field]) as cursor:
        for row in cursor:
            water_depth = row[0]
            turbine_capacity = row[1]
            port_distance = row[2] * 1e-3 # port distance in km
            ice_cover = 1 if row[3] == 'Yes' else 0

            total_cost = calculate_costs(water_depth, ice_cover, port_distance, turbine_capacity)
            row[4] = round(total_cost, 3)

            cursor.updateRow(row)

if __name__ == "__main__":
    update_fields()