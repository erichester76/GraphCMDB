# feature_packs/data_center_pack/views.py

from django.shortcuts import render
from neomodel import db
from cmdb.models import DynamicNode

def rack_elevation_tab(request, label, element_id):
    context = {
        'label': label,
        'element_id': element_id,
        'node': None,
        'rack_units': [],
        'error': None,
    }

    try:
        node_class = DynamicNode.get_or_create_label(label)
        query = f"""
            MATCH (n:`{label}`)
            WHERE elementId(n) = $eid
            RETURN n
        """
        result, _ = db.cypher_query(query, {'eid': element_id})
        if not result:
            context['error'] = f"Rack node not found: {element_id}"
            return context  # ← return dict, not render

        raw_node = result[0][0]
        node = node_class.inflate(raw_node)
        context['node'] = node

        # Get height_units
        height = node.custom_properties.get('height_units', 0)
        if not height:
            context['error'] = "No height_units defined for this rack"
            return context

        height = int(height)

        # Fetch units and devices
        units_query = f"""
            MATCH (n:`{label}`) WHERE elementId(n) = $eid
            OPTIONAL MATCH (n)-[:HAS_UNIT]->(u:Rack_Unit)
            OPTIONAL MATCH (u)-[:OCCUPIED_BY]->(d:Device)
            RETURN 
                u.unit_number AS unit_number,
                u.status AS unit_status,
                d.elementId AS device_id,
                d.custom_properties.name AS device_name,
                labels(d)[0] AS device_label
            ORDER BY u.unit_number DESC
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

        context['rack_units'] = rack_units

    except Exception as e:
        context['error'] = str(e)

    return context  # ← return dict only

def row_racks_tab(request, label, element_id):
    """
    Custom view for Row Racks tab.
    Fetches all racks in the row.
    """
    context = {
        'label': label,
        'element_id': element_id,
        'node': None,
        'row_racks': [],
        'error': None,
    }

    try:
        node_class = DynamicNode.get_or_create_label(label)
        query = f"""
            MATCH (n:`{label}`)
            WHERE elementId(n) = $eid
            RETURN n
        """
        result, _ = db.cypher_query(query, {'eid': element_id})
        if not result:
            context['error'] = f"Row node not found: {element_id}"
            return render(request, 'drow_racks_tab.html', context)

        raw_node = result[0][0]
        node = node_class.inflate(raw_node)
        context['node'] = node

        # Fetch all racks in this row (HAS_RACK rels)
        racks_query = f"""
            MATCH (n:`{label}`) WHERE elementId(n) = $eid
            MATCH (n)-[:HAS_RACK]->(rack:Rack)
            RETURN 
                elementId(rack) AS rack_id,
                labels(rack)[0] AS rack_label,
                rack.custom_properties.name AS rack_name,
                rack.custom_properties.height_units AS height_units
        """
        racks_result, _ = db.cypher_query(racks_query, {'eid': element_id})

        row_racks = []
        for row in racks_result:
            row_racks.append({
                'id': row[0],
                'label': row[1],
                'name': row[2] or row[0][:12] + '...',
                'height_units': row[3] or 0,
            })

        context['row_racks'] = row_racks

    except Exception as e:
        context['error'] = str(e)

    return render(request, 'row_racks_tab.html', context)


def room_racks_tab(request, label, element_id):
    """
    Custom view for Room Overview tab.
    Fetches rows and racks in the room.
    """
    context = {
        'label': label,
        'element_id': element_id,
        'node': None,
        'room_rows': [],
        'error': None,
    }

    try:
        node_class = DynamicNode.get_or_create_label(label)
        query = f"""
            MATCH (n:`{label}`)
            WHERE elementId(n) = $eid
            RETURN n
        """
        result, _ = db.cypher_query(query, {'eid': element_id})
        if not result:
            context['error'] = f"Room node not found: {element_id}"
            return render(request, 'room_racks_tab.html', context)

        raw_node = result[0][0]
        node = node_class.inflate(raw_node)
        context['node'] = node

        # Fetch all rows in this room (HAS_ROW rels)
        rows_query = f"""
            MATCH (n:`{label}`) WHERE elementId(n) = $eid
            MATCH (n)-[:HAS_ROW]->(row:Row)
            RETURN 
                elementId(row) AS row_id,
                labels(row)[0] AS row_label,
                row.custom_properties.name AS row_name
        """
        rows_result, _ = db.cypher_query(rows_query, {'eid': element_id})

        room_rows = []
        for row in rows_result:
            room_rows.append({
                'id': row[0],
                'label': row[1],
                'name': row[2] or row[0][:12] + '...',
            })

        context['room_rows'] = room_rows

    except Exception as e:
        context['error'] = str(e)

    return render(request, 'room_racks_tab.html', context)