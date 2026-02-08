# feature_packs/dhcp_pack/views.py

from django.shortcuts import render
from neomodel import db
from cmdb.models import DynamicNode


def dhcp_scope_details_tab(request, label, element_id):
    """
    Custom view for DHCP Scope Details tab.
    Shows DHCP leases assigned from this scope.
    """
    context = {
        'label': label,
        'element_id': element_id,
        'node': None,
        'custom_data': {
            'leases': [],
            'network': None
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
            context['error'] = f"DHCP Scope node not found: {element_id}"
            return context

        raw_node = result[0][0]
        node = node_class.inflate(raw_node)
        context['node'] = node

        # Fetch DHCP leases assigned from this scope
        leases_query = """
            MATCH (scope:DHCP_Scope) WHERE elementId(scope) = $eid
            MATCH (lease:DHCP_Lease)-[:ASSIGNED_FROM]->(scope)
            OPTIONAL MATCH (lease)-[:ASSIGNED_TO]->(ip:IP_Address)
            OPTIONAL MATCH (lease)-[:ASSIGNED_FOR]->(mac:Mac_Address)
            WITH lease, ip, mac,
                apoc.convert.fromJsonMap(lease.custom_properties) AS lease_props,
                apoc.convert.fromJsonMap(ip.custom_properties) AS ip_props,
                apoc.convert.fromJsonMap(mac.custom_properties) AS mac_props
            RETURN 
                elementId(lease) AS lease_id,
                labels(lease)[0] AS lease_label,
                COALESCE(lease_props['client-id'], 'Unknown') AS client_id,
                COALESCE(lease_props.status, 'Unknown') AS status,
                COALESCE(lease_props.lease_start, 'Unknown') AS lease_start,
                COALESCE(lease_props.lease_end, 'Unknown') AS lease_end,
                elementId(ip) AS ip_id,
                COALESCE(ip_props.address, 'Unknown') AS ip_address,
                elementId(mac) AS mac_id,
                COALESCE(mac_props.address, 'Unknown') AS mac_address
            ORDER BY lease_props.lease_start DESC
        """
        leases_result, _ = db.cypher_query(leases_query, {'eid': element_id})
        for row in leases_result:
            context['custom_data']['leases'].append({
                'id': row[0],
                'label': row[1],
                'client_id': row[2],
                'status': row[3],
                'lease_start': row[4],
                'lease_end': row[5],
                'ip_id': row[6],
                'ip_address': row[7],
                'mac_id': row[8],
                'mac_address': row[9]
            })

        # Fetch the network this scope is part of
        network_query = """
            MATCH (scope:DHCP_Scope) WHERE elementId(scope) = $eid
            MATCH (scope)-[:PART_OF]->(network:Network)
            WITH network, apoc.convert.fromJsonMap(network.custom_properties) AS net_props
            RETURN 
                elementId(network) AS network_id,
                labels(network)[0] AS network_label,
                COALESCE(net_props.name, 'Unnamed') AS network_name,
                COALESCE(net_props.cidr, 'Unknown') AS cidr
        """
        network_result, _ = db.cypher_query(network_query, {'eid': element_id})
        if network_result:
            row = network_result[0]
            context['custom_data']['network'] = {
                'id': row[0],
                'label': row[1],
                'name': row[2],
                'cidr': row[3]
            }

    except Exception as e:
        context['error'] = str(e)

    return context


def dhcp_lease_details_tab(request, label, element_id):
    """
    Custom view for DHCP Lease Details tab.
    Shows the scope, assigned IP, and assigned MAC address.
    """
    context = {
        'label': label,
        'element_id': element_id,
        'node': None,
        'custom_data': {
            'scope': None,
            'ip_address': None,
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
            context['error'] = f"DHCP Lease node not found: {element_id}"
            return context

        raw_node = result[0][0]
        node = node_class.inflate(raw_node)
        context['node'] = node

        # Fetch the DHCP scope this lease is assigned from
        scope_query = """
            MATCH (lease:DHCP_Lease) WHERE elementId(lease) = $eid
            MATCH (lease)-[:ASSIGNED_FROM]->(scope:DHCP_Scope)
            WITH scope, apoc.convert.fromJsonMap(scope.custom_properties) AS scope_props
            RETURN 
                elementId(scope) AS scope_id,
                labels(scope)[0] AS scope_label,
                COALESCE(scope_props.name, 'Unnamed') AS name,
                COALESCE(scope_props.range_start, 'Unknown') AS range_start,
                COALESCE(scope_props.range_end, 'Unknown') AS range_end
        """
        scope_result, _ = db.cypher_query(scope_query, {'eid': element_id})
        if scope_result:
            row = scope_result[0]
            context['custom_data']['scope'] = {
                'id': row[0],
                'label': row[1],
                'name': row[2],
                'range_start': row[3],
                'range_end': row[4]
            }

        # Fetch the IP address assigned to this lease
        ip_query = """
            MATCH (lease:DHCP_Lease) WHERE elementId(lease) = $eid
            MATCH (lease)-[:ASSIGNED_TO]->(ip:IP_Address)
            WITH ip, apoc.convert.fromJsonMap(ip.custom_properties) AS ip_props
            RETURN 
                elementId(ip) AS ip_id,
                labels(ip)[0] AS ip_label,
                COALESCE(ip_props.address, 'Unknown') AS address,
                COALESCE(ip_props.type, 'Unknown') AS type,
                COALESCE(ip_props.status, 'Unknown') AS status
        """
        ip_result, _ = db.cypher_query(ip_query, {'eid': element_id})
        if ip_result:
            row = ip_result[0]
            context['custom_data']['ip_address'] = {
                'id': row[0],
                'label': row[1],
                'address': row[2],
                'type': row[3],
                'status': row[4]
            }

        # Fetch the MAC address assigned for this lease
        mac_query = """
            MATCH (lease:DHCP_Lease) WHERE elementId(lease) = $eid
            MATCH (lease)-[:ASSIGNED_FOR]->(mac:Mac_Address)
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
