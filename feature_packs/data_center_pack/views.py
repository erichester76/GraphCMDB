# feature_packs/data_center_pack/views.py

from django.shortcuts import render
from neomodel import db
from cmdb.models import DynamicNode

def rack_elevation_tab(request, label, element_id):
    context = {
        'label': label,
        'element_id': element_id,
        'node': None,
        'custom_data': {
            'properties': [],
            'location_chain': [],
            'rack_units': [],
            'error': None,
        },
        'error': None,
    }

    try:
        node_class = DynamicNode.get_or_create_label(label)
        # Use helper method instead of raw Cypher
        node = node_class.get_by_element_id(element_id)
        if not node:
            context['error'] = f"Rack node not found: {element_id}"
            context['custom_data']['error'] = context['error']
            return context  # ← return dict, not render

        context['node'] = node

        # Build properties list
        custom_props = node.custom_properties or {}
        props_list = []
        for key, value in custom_props.items():
            props_list.append({
                'key': key,
                'value': value,
                'value_type': type(value).__name__,
            })
        context['custom_data']['properties'] = props_list

        # Follow LOCATED_IN relationships to get location hierarchy
        location_query = f"""
            MATCH (n:`{label}`) WHERE elementId(n) = $eid
            OPTIONAL MATCH path = (n)-[:LOCATED_IN*]->(location)
            WITH n, location, 
                 apoc.convert.fromJsonMap(location.custom_properties) AS loc_props,
                 labels(location)[0] AS loc_label,
                 elementId(location) AS loc_id,
                 length(path) AS depth
            RETURN loc_label, loc_id, 
                   COALESCE(loc_props.name, 'Unnamed') AS loc_name,
                   depth
            ORDER BY depth ASC
        """
        location_result, _ = db.cypher_query(location_query, {'eid': element_id})
        
        location_chain = []
        for row in location_result:
            if row[0]:  # If there's a label
                location_chain.append({
                    'label': row[0],
                    'id': row[1],
                    'name': row[2],
                    'depth': row[3],
                })
        context['custom_data']['location_chain'] = location_chain

        # Get height_units
        height = node.get_property('height', 0)
        if not height:
            context['error'] = "No height defined for this rack"
            context['custom_data']['error'] = context['error']
            return context

        height = int(height)

        # Fetch units and devices
        units_query = f"""
            MATCH (n:`{label}`) WHERE elementId(n) = $eid
            MATCH (n)<-[:LOCATED_IN]-(u:Rack_Unit)
            OPTIONAL MATCH (u)<-[:LOCATED_IN]-(d:Device)

            WITH 
                u,
                apoc.convert.fromJsonMap(u.custom_properties) AS u_props,
                d,
                apoc.convert.fromJsonMap(d.custom_properties) AS d_props

            RETURN 
                COALESCE(u_props.unit_number, 'unknown')    AS unit_number,
                COALESCE(u_props.status, 'unknown')         AS unit_status,
                elementId(d)                                AS device_id,
                COALESCE(d_props.name, 'Unnamed')           AS device_name,
                COALESCE(labels(d)[0], 'Unknown')           AS device_label
            ORDER BY COALESCE(toInteger(u_props.unit_number), 0) DESC
        """
        units_result, _ = db.cypher_query(units_query, {'eid': element_id})  

        unit_map = {}
        for row in units_result:
            unit_num = row[0]
            if unit_num is not None:
                unit_map[unit_num] = {
                    'number': unit_num,
                    'status': row[1],
                    'device': {
                        'target_label': row[4],
                        'target_id': row[2],
                        'target_name': row[3],
                    } if row[2] else None,
                }

        rack_units = []
        for unit_num in range(height, 0, -1):
            unit = unit_map.get(unit_num, {
                'number': unit_num,
                'status': 'empty',
                'device': None,
            })
            rack_units.append(unit)
            
        context['custom_data']['rack_units'] = rack_units

    except Exception as e:
        context['error'] = str(e)
        context['custom_data']['error'] = str(e)

    return context  # ← return dict only

def row_racks_tab(request, label, element_id):
    """
    Custom view for Row Racks tab.
    Fetches all racks located in this row (incoming LOCATED_IN rels).
    """
    context = {
        'label': label,
        'element_id': element_id,
        'node': None,
        'custom_data': [],
        'error': None,
    }

    try:
        node_class = DynamicNode.get_or_create_label(label)
        # Use helper method instead of raw Cypher
        node = node_class.get_by_element_id(element_id)
        if not node:
            context['error'] = f"Row node not found: {element_id}"
            return context

        context['node'] = node

        # Fetch all racks located in this row (incoming LOCATED_IN rels)
        racks_query = f"""
            MATCH (n:`{label}`) WHERE elementId(n) = $eid
                MATCH (rack:Rack)-[:LOCATED_IN]->(n)

                WITH 
                    rack,
                    apoc.convert.fromJsonMap(rack.custom_properties) AS rack_props

                RETURN 
                    elementId(rack) AS rack_id,
                    labels(rack)[0] AS rack_label,
                    COALESCE(
                        rack_props.name,
                        rack_props.Name,                // case-insensitive fallback
                        rack_props.NAME,
                        rack_props[head(keys(rack_props))],
                        'Unnamed'
                    ) AS rack_name,
                    COALESCE(toInteger(rack_props.height), 0) AS height
                ORDER BY COALESCE(rack_props.name, 'Unnamed')
        """
        racks_result, _ = db.cypher_query(racks_query, {'eid': element_id})

        row_racks = []
        for row in racks_result:
            row_racks.append({
                'id': row[0],
                'label': row[1],
                'name': row[2] or row[0][:12] + '...',
                'height': row[3] or 0,
            })

        context['custom_data'] = row_racks

    except Exception as e:
        context['error'] = str(e)

    return context

def room_racks_tab(request, label, element_id):
    context = {
        'label': label,
        'element_id': element_id,
        'node': None,
        'custom_data': [],  # List of rows, each with racks
        'error': None,
    }

    print(f"DEBUG: Fetching room data for element_id: {element_id} with label: {label}")
    try:
        node_class = DynamicNode.get_or_create_label(label)
        # Use helper method instead of raw Cypher for node retrieval
        node = node_class.get_by_element_id(element_id)
        if not node:
            context['error'] = f"Room node not found: {element_id}"
            return context

        context['node'] = node

        # Get room orientation from custom properties (using helper method)
        room_orientation = node.get_property('orientation', 'LeftToRight')
        context['room_orientation'] = room_orientation
        
        print(f"DEBUG: Room orientation: {room_orientation} for room {element_id}")
        
        # Fetch all rows in this room (incoming LOCATED_IN rels from Row to Room)
        rows_query = f"""
            MATCH (room:`{label}`) WHERE elementId(room) = $eid
            MATCH (row:Row)-[:LOCATED_IN]->(room)

            WITH 
                row,
                apoc.convert.fromJsonMap(row.custom_properties) AS row_props

            RETURN 
                elementId(row) AS row_id,
                labels(row)[0] AS row_label,
                COALESCE(row_props.name, 'Unnamed Row') AS row_name,
                COALESCE(row_props.description, 'No description') AS row_description,
                COALESCE(row_props.row_number, 0) AS row_number,
                COALESCE(row_props.orientation, 'LeftToRight') AS row_orientation
            ORDER BY COALESCE(toInteger(row_props.row_number), 0)
        """
        rows_result, _ = db.cypher_query(rows_query, {'eid': element_id})
                
        room_rows = []
        for row in rows_result:
            row_orientation = row[5]  # row_orientation
            row_racks = []

            # Fetch all racks in this row (incoming LOCATED_IN rels from Rack to Row)
            racks_query = f"""
                MATCH (row:Row) WHERE elementId(row) = $row_id
                MATCH (rack:Rack)-[:LOCATED_IN]->(row)

                WITH 
                    rack,
                    apoc.convert.fromJsonMap(rack.custom_properties) AS rack_props

                RETURN 
                    elementId(rack) AS rack_id,
                    labels(rack)[0] AS rack_label,
                    COALESCE(rack_props.name, 'Unnamed Rack') AS rack_name,
                    COALESCE(toInteger(rack_props.height), 0) AS height,
                    COALESCE(toInteger(rack_props.rack_number), 0) AS rack_number
                ORDER BY 
                    CASE $row_orientation
                        WHEN 'LeftToRight' THEN COALESCE(toInteger(rack_props.rack_number), 0)
                        WHEN 'RightToLeft' THEN -COALESCE(toInteger(rack_props.rack_number), 0)
                        ELSE COALESCE(rack_props.name, 'Unnamed Rack')
                    END
            """
            racks_result, _ = db.cypher_query(racks_query, {
                'row_id': row[0],
                'row_orientation': row_orientation,
            })

            for rack in racks_result:
                row_racks.append({
                    'id': rack[0],
                    'label': rack[1],
                    'name': rack[2],
                    'height': rack[3],
                    'rack_number': rack[4],
                })
                # Sort racks based on row_orientation and rack_number
                if row_orientation == 'LeftToRight':
                    row_racks = sorted(row_racks, key=lambda r: r['rack_number'])
                elif row_orientation == 'RightToLeft':
                    row_racks = sorted(row_racks, key=lambda r: r['rack_number'], reverse=True)
                elif row_orientation == 'TopToBottom':
                    row_racks = sorted(row_racks, key=lambda r: r['rack_number'])
                elif row_orientation == 'BottomToTop':
                    row_racks = sorted(row_racks, key=lambda r: r['rack_number'], reverse=True)
                else:
                    # Fallback to alphabetical by name if orientation is invalid or missing
                    row_racks = sorted(row_racks, key=lambda r: r['name'])

            room_rows.append({
                'id': row[0],
                'label': row[1],
                'name': row[2],
                'description': row[3],
                'row_number': row[4],
                'orientation': row_orientation,
                'racks': row_racks,
            })

        # Sort rows based on room_orientation
        if room_orientation == 'TopToBottom':
            room_rows = sorted(room_rows, key=lambda r: r['row_number'])
        elif room_orientation == 'BottomToTop':
            room_rows = sorted(room_rows, key=lambda r: r['row_number'], reverse=True)
        elif room_orientation == 'LeftToRight':
            room_rows = sorted(room_rows, key=lambda r: r['row_number'])
        elif room_orientation == 'RightToLeft':
            room_rows = sorted(room_rows, key=lambda r: r['row_number'], reverse=True)

        context['custom_data'] = room_rows
        
        print(f'room: {room_rows}')

    except Exception as e:
        context['error'] = str(e)

    return context