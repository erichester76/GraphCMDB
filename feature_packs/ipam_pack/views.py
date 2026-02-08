# feature_packs/ipam_pack/views.py

from django.shortcuts import render
from neomodel import db
from cmdb.models import DynamicNode


def network_details_tab(request, label, element_id):
    """
    Custom view for Network Details tab.
    Shows child networks, IP addresses, and assigned VLAN.
    """
    context = {
        'label': label,
        'element_id': element_id,
        'node': None,
        'custom_data': {
            'child_networks': [],
            'ip_addresses': [],
            'vlan': None
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
            context['error'] = f"Network node not found: {element_id}"
            return context

        raw_node = result[0][0]
        node = node_class.inflate(raw_node)
        context['node'] = node

        # Fetch child networks (incoming CHILD_OF relationships)
        child_networks_query = """
            MATCH (network:Network) WHERE elementId(network) = $eid
            MATCH (child:Network)-[:CHILD_OF]->(network)
            WITH child, apoc.convert.fromJsonMap(child.custom_properties) AS child_props
            RETURN 
                elementId(child) AS child_id,
                labels(child)[0] AS child_label,
                COALESCE(child_props.name, 'Unnamed') AS name,
                COALESCE(child_props.cidr, 'Unknown') AS cidr,
                COALESCE(child_props.description, '') AS description
            ORDER BY child_props.name
        """
        child_result, _ = db.cypher_query(child_networks_query, {'eid': element_id})
        for row in child_result:
            context['custom_data']['child_networks'].append({
                'id': row[0],
                'label': row[1],
                'name': row[2],
                'cidr': row[3],
                'description': row[4]
            })

        # Fetch IP addresses (incoming PART_OF relationships)
        ip_addresses_query = """
            MATCH (network:Network) WHERE elementId(network) = $eid
            MATCH (ip:IP_Address)-[:PART_OF]->(network)
            WITH ip, apoc.convert.fromJsonMap(ip.custom_properties) AS ip_props
            RETURN 
                elementId(ip) AS ip_id,
                labels(ip)[0] AS ip_label,
                COALESCE(ip_props.address, 'Unknown') AS address,
                COALESCE(ip_props.type, 'Unknown') AS type,
                COALESCE(ip_props.status, 'Unknown') AS status
            ORDER BY ip_props.address
        """
        ip_result, _ = db.cypher_query(ip_addresses_query, {'eid': element_id})
        for row in ip_result:
            context['custom_data']['ip_addresses'].append({
                'id': row[0],
                'label': row[1],
                'address': row[2],
                'type': row[3],
                'status': row[4]
            })

        # Fetch assigned VLAN (outgoing ASSIGNED_TO relationship)
        vlan_query = """
            MATCH (network:Network) WHERE elementId(network) = $eid
            MATCH (network)-[:ASSIGNED_TO]->(vlan:VLAN)
            WITH vlan, apoc.convert.fromJsonMap(vlan.custom_properties) AS vlan_props
            RETURN 
                elementId(vlan) AS vlan_id,
                labels(vlan)[0] AS vlan_label,
                COALESCE(vlan_props.vlan_id, 'Unknown') AS vlan_id_num,
                COALESCE(vlan_props.name, 'Unnamed') AS name
        """
        vlan_result, _ = db.cypher_query(vlan_query, {'eid': element_id})
        if vlan_result:
            row = vlan_result[0]
            context['custom_data']['vlan'] = {
                'id': row[0],
                'label': row[1],
                'vlan_id': row[2],
                'name': row[3]
            }

    except Exception as e:
        context['error'] = str(e)

    return context


def ip_address_details_tab(request, label, element_id):
    """
    Custom view for IP Address Details tab.
    Shows parent network and assigned MAC address.
    """
    context = {
        'label': label,
        'element_id': element_id,
        'node': None,
        'custom_data': {
            'network': None,
            'mac_address': None
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
            context['error'] = f"IP Address node not found: {element_id}"
            return context

        raw_node = result[0][0]
        node = node_class.inflate(raw_node)
        context['node'] = node

        # Fetch parent network (outgoing PART_OF relationship)
        network_query = """
            MATCH (ip:IP_Address) WHERE elementId(ip) = $eid
            MATCH (ip)-[:PART_OF]->(network:Network)
            WITH network, apoc.convert.fromJsonMap(network.custom_properties) AS net_props
            RETURN 
                elementId(network) AS network_id,
                labels(network)[0] AS network_label,
                COALESCE(net_props.name, 'Unnamed') AS name,
                COALESCE(net_props.cidr, 'Unknown') AS cidr,
                COALESCE(net_props.description, '') AS description
        """
        network_result, _ = db.cypher_query(network_query, {'eid': element_id})
        if network_result:
            row = network_result[0]
            context['custom_data']['network'] = {
                'id': row[0],
                'label': row[1],
                'name': row[2],
                'cidr': row[3],
                'description': row[4]
            }

        # Fetch assigned MAC address (outgoing ASSIGNED_TO relationship)
        mac_query = """
            MATCH (ip:IP_Address) WHERE elementId(ip) = $eid
            MATCH (ip)-[:ASSIGNED_TO]->(mac:Mac_Address)
            WITH mac, apoc.convert.fromJsonMap(mac.custom_properties) AS mac_props
            RETURN 
                elementId(mac) AS mac_id,
                labels(mac)[0] AS mac_label,
                COALESCE(mac_props.address, 'Unknown') AS address,
                COALESCE(mac_props.status, 'Unknown') AS status
        """
        mac_result, _ = db.cypher_query(mac_query, {'eid': element_id})
        if mac_result:
            row = mac_result[0]
            context['custom_data']['mac_address'] = {
                'id': row[0],
                'label': row[1],
                'address': row[2],
                'status': row[3]
            }

    except Exception as e:
        context['error'] = str(e)

    return context


def mac_address_details_tab(request, label, element_id):
    """
    Custom view for MAC Address Details tab.
    Shows assigned IP addresses and assigned interface.
    """
    context = {
        'label': label,
        'element_id': element_id,
        'node': None,
        'custom_data': {
            'ip_addresses': [],
            'interface': None
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
            context['error'] = f"MAC Address node not found: {element_id}"
            return context

        raw_node = result[0][0]
        node = node_class.inflate(raw_node)
        context['node'] = node

        # Fetch assigned IP addresses (incoming ASSIGNED_TO relationships)
        ip_addresses_query = """
            MATCH (mac:Mac_Address) WHERE elementId(mac) = $eid
            MATCH (ip:IP_Address)-[:ASSIGNED_TO]->(mac)
            WITH ip, apoc.convert.fromJsonMap(ip.custom_properties) AS ip_props
            RETURN 
                elementId(ip) AS ip_id,
                labels(ip)[0] AS ip_label,
                COALESCE(ip_props.address, 'Unknown') AS address,
                COALESCE(ip_props.type, 'Unknown') AS type,
                COALESCE(ip_props.status, 'Unknown') AS status
            ORDER BY ip_props.address
        """
        ip_result, _ = db.cypher_query(ip_addresses_query, {'eid': element_id})
        for row in ip_result:
            context['custom_data']['ip_addresses'].append({
                'id': row[0],
                'label': row[1],
                'address': row[2],
                'type': row[3],
                'status': row[4]
            })

        # Fetch assigned interface (outgoing ASSIGNED_TO relationship)
        interface_query = """
            MATCH (mac:Mac_Address) WHERE elementId(mac) = $eid
            MATCH (mac)-[:ASSIGNED_TO]->(interface:Interface)
            WITH interface, apoc.convert.fromJsonMap(interface.custom_properties) AS int_props
            RETURN 
                elementId(interface) AS interface_id,
                labels(interface)[0] AS interface_label,
                COALESCE(int_props.name, 'Unnamed') AS name,
                COALESCE(int_props.status, 'Unknown') AS status,
                COALESCE(int_props.type, 'Unknown') AS type
        """
        interface_result, _ = db.cypher_query(interface_query, {'eid': element_id})
        if interface_result:
            row = interface_result[0]
            context['custom_data']['interface'] = {
                'id': row[0],
                'label': row[1],
                'name': row[2],
                'status': row[3],
                'type': row[4]
            }

    except Exception as e:
        context['error'] = str(e)

    return context
