# feature_packs/network_pack/views.py

from django.shortcuts import render
from neomodel import db
from cmdb.models import DynamicNode


def interface_details_tab(request, label, element_id):
    """
    Context builder for Interface Details tab.
    Shows device it's located on, connected cables, and circuits terminating here.
    Returns context dictionary rather than rendering template directly.
    """
    context = {
        'label': label,
        'element_id': element_id,
        'node': None,
        'custom_data': {
            'device': None,
            'cables': [],
            'circuits': []
        },
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
            context['error'] = f"Interface node not found: {element_id}"
            return context

        raw_node = result[0][0]
        node = node_class.inflate(raw_node)
        context['node'] = node

        # Fetch device (outgoing LOCATED_ON relationship)
        device_query = """
            MATCH (interface:Interface) WHERE elementId(interface) = $eid
            MATCH (interface)-[:LOCATED_ON]->(device:Device)
            WITH device, apoc.convert.fromJsonMap(device.custom_properties) AS device_props
            RETURN 
                elementId(device) AS device_id,
                labels(device)[0] AS device_label,
                COALESCE(device_props.name, 'Unnamed') AS name,
                COALESCE(device_props.type, 'Unknown') AS type,
                COALESCE(device_props.status, 'Unknown') AS status
        """
        device_result, _ = db.cypher_query(device_query, {'eid': element_id})
        if device_result:
            row = device_result[0]
            context['custom_data']['device'] = {
                'id': row[0],
                'label': row[1],
                'name': row[2],
                'type': row[3],
                'status': row[4]
            }

        # Fetch connected cables (incoming CONNECTS relationships)
        cables_query = """
            MATCH (interface:Interface) WHERE elementId(interface) = $eid
            MATCH (cable:Cable)-[:CONNECTS]->(interface)
            WITH cable, apoc.convert.fromJsonMap(cable.custom_properties) AS cable_props
            RETURN 
                elementId(cable) AS cable_id,
                labels(cable)[0] AS cable_label,
                COALESCE(cable_props.type, 'Unknown') AS type,
                COALESCE(cable_props.length_meters, 0) AS length_meters,
                COALESCE(cable_props.color, 'Unknown') AS color,
                COALESCE(cable_props.status, 'Unknown') AS status
            ORDER BY cable_props.type
        """
        cables_result, _ = db.cypher_query(cables_query, {'eid': element_id})
        for row in cables_result:
            context['custom_data']['cables'].append({
                'id': row[0],
                'label': row[1],
                'type': row[2],
                'length_meters': row[3],
                'color': row[4],
                'status': row[5]
            })

        # Fetch circuits terminating here (incoming TERMINATES_AT relationships)
        circuits_query = """
            MATCH (interface:Interface) WHERE elementId(interface) = $eid
            MATCH (circuit:Circuit)-[:TERMINATES_AT]->(interface)
            WITH circuit, apoc.convert.fromJsonMap(circuit.custom_properties) AS circuit_props
            RETURN 
                elementId(circuit) AS circuit_id,
                labels(circuit)[0] AS circuit_label,
                COALESCE(circuit_props.name, 'Unnamed') AS name,
                COALESCE(circuit_props.circuit_id, 'Unknown') AS circuit_id_value,
                COALESCE(circuit_props.bandwidth_mbps, 0) AS bandwidth_mbps,
                COALESCE(circuit_props.status, 'Unknown') AS status
            ORDER BY circuit_props.name
        """
        circuits_result, _ = db.cypher_query(circuits_query, {'eid': element_id})
        for row in circuits_result:
            context['custom_data']['circuits'].append({
                'id': row[0],
                'label': row[1],
                'name': row[2],
                'circuit_id': row[3],
                'bandwidth_mbps': row[4],
                'status': row[5]
            })

    except Exception as e:
        context['error'] = str(e)

    return context


def cable_details_tab(request, label, element_id):
    """
    Context builder for Cable Details tab.
    Shows both connected interfaces (typically 2 ends).
    Returns context dictionary rather than rendering template directly.
    """
    context = {
        'label': label,
        'element_id': element_id,
        'node': None,
        'custom_data': {
            'interfaces': []
        },
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
            context['error'] = f"Cable node not found: {element_id}"
            return context

        raw_node = result[0][0]
        node = node_class.inflate(raw_node)
        context['node'] = node

        # Fetch connected interfaces (outgoing CONNECTS relationships)
        interfaces_query = """
            MATCH (cable:Cable) WHERE elementId(cable) = $eid
            MATCH (cable)-[:CONNECTS]->(interface:Interface)
            WITH interface, apoc.convert.fromJsonMap(interface.custom_properties) AS int_props
            OPTIONAL MATCH (interface)-[:LOCATED_ON]->(device:Device)
            WITH interface, int_props, device, apoc.convert.fromJsonMap(device.custom_properties) AS device_props
            RETURN 
                elementId(interface) AS interface_id,
                labels(interface)[0] AS interface_label,
                COALESCE(int_props.name, 'Unnamed') AS name,
                COALESCE(int_props.status, 'Unknown') AS status,
                COALESCE(int_props.speed_mbps, 0) AS speed_mbps,
                elementId(device) AS device_id,
                labels(device)[0] AS device_label,
                COALESCE(device_props.name, 'Unknown') AS device_name
            ORDER BY int_props.name
        """
        interfaces_result, _ = db.cypher_query(interfaces_query, {'eid': element_id})
        for row in interfaces_result:
            interface_data = {
                'id': row[0],
                'label': row[1],
                'name': row[2],
                'status': row[3],
                'speed_mbps': row[4],
                'device': None
            }
            if row[5]:  # device_id exists
                interface_data['device'] = {
                    'id': row[5],
                    'label': row[6],
                    'name': row[7]
                }
            context['custom_data']['interfaces'].append(interface_data)

    except Exception as e:
        context['error'] = str(e)

    return context


def circuit_details_tab(request, label, element_id):
    """
    Context builder for Circuit Details tab.
    Shows terminating interfaces and providing vendor.
    Returns context dictionary rather than rendering template directly.
    """
    context = {
        'label': label,
        'element_id': element_id,
        'node': None,
        'custom_data': {
            'interfaces': [],
            'vendor': None
        },
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
            context['error'] = f"Circuit node not found: {element_id}"
            return context

        raw_node = result[0][0]
        node = node_class.inflate(raw_node)
        context['node'] = node

        # Fetch terminating interfaces (outgoing TERMINATES_AT relationships)
        interfaces_query = """
            MATCH (circuit:Circuit) WHERE elementId(circuit) = $eid
            MATCH (circuit)-[:TERMINATES_AT]->(interface:Interface)
            WITH interface, apoc.convert.fromJsonMap(interface.custom_properties) AS int_props
            OPTIONAL MATCH (interface)-[:LOCATED_ON]->(device:Device)
            WITH interface, int_props, device, apoc.convert.fromJsonMap(device.custom_properties) AS device_props
            RETURN 
                elementId(interface) AS interface_id,
                labels(interface)[0] AS interface_label,
                COALESCE(int_props.name, 'Unnamed') AS name,
                COALESCE(int_props.status, 'Unknown') AS status,
                COALESCE(int_props.speed_mbps, 0) AS speed_mbps,
                elementId(device) AS device_id,
                labels(device)[0] AS device_label,
                COALESCE(device_props.name, 'Unknown') AS device_name
            ORDER BY int_props.name
        """
        interfaces_result, _ = db.cypher_query(interfaces_query, {'eid': element_id})
        for row in interfaces_result:
            interface_data = {
                'id': row[0],
                'label': row[1],
                'name': row[2],
                'status': row[3],
                'speed_mbps': row[4],
                'device': None
            }
            if row[5]:  # device_id exists
                interface_data['device'] = {
                    'id': row[5],
                    'label': row[6],
                    'name': row[7]
                }
            context['custom_data']['interfaces'].append(interface_data)

        # Fetch providing vendor (outgoing PROVIDED_BY relationship)
        vendor_query = """
            MATCH (circuit:Circuit) WHERE elementId(circuit) = $eid
            MATCH (circuit)-[:PROVIDED_BY]->(vendor:Vendor)
            WITH vendor, apoc.convert.fromJsonMap(vendor.custom_properties) AS vendor_props
            RETURN 
                elementId(vendor) AS vendor_id,
                labels(vendor)[0] AS vendor_label,
                COALESCE(vendor_props.name, 'Unnamed') AS name,
                COALESCE(vendor_props.contact_email, '') AS contact_email,
                COALESCE(vendor_props.contact_phone, '') AS contact_phone
        """
        vendor_result, _ = db.cypher_query(vendor_query, {'eid': element_id})
        if vendor_result:
            row = vendor_result[0]
            context['custom_data']['vendor'] = {
                'id': row[0],
                'label': row[1],
                'name': row[2],
                'contact_email': row[3],
                'contact_phone': row[4]
            }

    except Exception as e:
        context['error'] = str(e)

    return context


def vlan_details_tab(request, label, element_id):
    """
    Context builder for VLAN Details tab.
    Shows assigned networks (ASSIGNED_TO incoming from Network nodes).
    Returns context dictionary rather than rendering template directly.
    """
    context = {
        'label': label,
        'element_id': element_id,
        'node': None,
        'custom_data': {
            'networks': []
        },
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
            context['error'] = f"VLAN node not found: {element_id}"
            return context

        raw_node = result[0][0]
        node = node_class.inflate(raw_node)
        context['node'] = node

        # Fetch assigned networks (incoming ASSIGNED_TO relationships)
        networks_query = """
            MATCH (vlan:VLAN) WHERE elementId(vlan) = $eid
            MATCH (network:Network)-[:ASSIGNED_TO]->(vlan)
            WITH network, apoc.convert.fromJsonMap(network.custom_properties) AS net_props
            RETURN 
                elementId(network) AS network_id,
                labels(network)[0] AS network_label,
                COALESCE(net_props.name, 'Unnamed') AS name,
                COALESCE(net_props.cidr, 'Unknown') AS cidr,
                COALESCE(net_props.description, '') AS description,
                COALESCE(net_props.status, 'Unknown') AS status
            ORDER BY net_props.name
        """
        networks_result, _ = db.cypher_query(networks_query, {'eid': element_id})
        for row in networks_result:
            context['custom_data']['networks'].append({
                'id': row[0],
                'label': row[1],
                'name': row[2],
                'cidr': row[3],
                'description': row[4],
                'status': row[5]
            })

    except Exception as e:
        context['error'] = str(e)

    return context
