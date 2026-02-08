# feature_packs/dns_pack/views.py

from django.shortcuts import render
from neomodel import db
from cmdb.models import DynamicNode


def dns_zone_details_tab(request, label, element_id):
    """
    Custom view for DNS Zone Details tab.
    Shows DNS records in this zone.
    """
    context = {
        'label': label,
        'element_id': element_id,
        'node': None,
        'custom_data': {
            'records': [],
            'views': []
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
            context['error'] = f"DNS Zone node not found: {element_id}"
            return context

        raw_node = result[0][0]
        node = node_class.inflate(raw_node)
        context['node'] = node

        # Fetch DNS records in this zone
        records_query = """
            MATCH (zone:DNS_Zone) WHERE elementId(zone) = $eid
            MATCH (zone)-[:HAS_RECORD]->(record:DNS_Record)
            OPTIONAL MATCH (record)-[:RESOLVES_TO]->(ip:IP_Address)
            WITH record, ip,
                apoc.convert.fromJsonMap(record.custom_properties) AS rec_props,
                apoc.convert.fromJsonMap(ip.custom_properties) AS ip_props
            RETURN 
                elementId(record) AS record_id,
                labels(record)[0] AS record_label,
                COALESCE(rec_props.name, 'Unknown') AS name,
                COALESCE(rec_props.type, 'Unknown') AS type,
                COALESCE(rec_props.value, 'Unknown') AS value,
                COALESCE(rec_props.ttl, 'Default') AS ttl,
                elementId(ip) AS ip_id,
                COALESCE(ip_props.address, NULL) AS ip_address
            ORDER BY rec_props.type, rec_props.name
        """
        records_result, _ = db.cypher_query(records_query, {'eid': element_id})
        for row in records_result:
            context['custom_data']['records'].append({
                'id': row[0],
                'label': row[1],
                'name': row[2],
                'type': row[3],
                'value': row[4],
                'ttl': row[5],
                'ip_id': row[6],
                'ip_address': row[7]
            })

        # Fetch DNS views containing this zone
        views_query = """
            MATCH (zone:DNS_Zone) WHERE elementId(zone) = $eid
            MATCH (view:DNS_View)-[:CONTAINS]->(zone)
            WITH view, apoc.convert.fromJsonMap(view.custom_properties) AS view_props
            RETURN 
                elementId(view) AS view_id,
                labels(view)[0] AS view_label,
                COALESCE(view_props.name, 'Unnamed') AS name,
                COALESCE(view_props.description, '') AS description
        """
        views_result, _ = db.cypher_query(views_query, {'eid': element_id})
        for row in views_result:
            context['custom_data']['views'].append({
                'id': row[0],
                'label': row[1],
                'name': row[2],
                'description': row[3]
            })

    except Exception as e:
        context['error'] = str(e)

    return context


def dns_record_details_tab(request, label, element_id):
    """
    Custom view for DNS Record Details tab.
    Shows the parent zone and resolved IP address.
    """
    context = {
        'label': label,
        'element_id': element_id,
        'node': None,
        'custom_data': {
            'zone': None,
            'ip_address': None
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
            context['error'] = f"DNS Record node not found: {element_id}"
            return context

        raw_node = result[0][0]
        node = node_class.inflate(raw_node)
        context['node'] = node

        # Fetch the parent zone
        zone_query = """
            MATCH (record:DNS_Record) WHERE elementId(record) = $eid
            MATCH (record)-[:PART_OF]->(zone:DNS_Zone)
            WITH zone, apoc.convert.fromJsonMap(zone.custom_properties) AS zone_props
            RETURN 
                elementId(zone) AS zone_id,
                labels(zone)[0] AS zone_label,
                COALESCE(zone_props.name, 'Unnamed') AS name,
                COALESCE(zone_props.primary_ns, 'Unknown') AS primary_ns
        """
        zone_result, _ = db.cypher_query(zone_query, {'eid': element_id})
        if zone_result:
            row = zone_result[0]
            context['custom_data']['zone'] = {
                'id': row[0],
                'label': row[1],
                'name': row[2],
                'primary_ns': row[3]
            }

        # Fetch resolved IP address
        ip_query = """
            MATCH (record:DNS_Record) WHERE elementId(record) = $eid
            MATCH (record)-[:RESOLVES_TO]->(ip:IP_Address)
            WITH ip, apoc.convert.fromJsonMap(ip.custom_properties) AS ip_props
            RETURN 
                elementId(ip) AS ip_id,
                labels(ip)[0] AS ip_label,
                COALESCE(ip_props.address, 'Unknown') AS address,
                COALESCE(ip_props.status, 'Unknown') AS status
        """
        ip_result, _ = db.cypher_query(ip_query, {'eid': element_id})
        if ip_result:
            row = ip_result[0]
            context['custom_data']['ip_address'] = {
                'id': row[0],
                'label': row[1],
                'address': row[2],
                'status': row[3]
            }

    except Exception as e:
        context['error'] = str(e)

    return context


def dns_view_details_tab(request, label, element_id):
    """
    Custom view for DNS View Details tab.
    Shows all zones contained in this view.
    """
    context = {
        'label': label,
        'element_id': element_id,
        'node': None,
        'custom_data': {
            'zones': []
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
            context['error'] = f"DNS View node not found: {element_id}"
            return context

        raw_node = result[0][0]
        node = node_class.inflate(raw_node)
        context['node'] = node

        # Fetch zones in this view
        zones_query = """
            MATCH (view:DNS_View) WHERE elementId(view) = $eid
            MATCH (view)-[:CONTAINS]->(zone:DNS_Zone)
            WITH zone, apoc.convert.fromJsonMap(zone.custom_properties) AS zone_props
            RETURN 
                elementId(zone) AS zone_id,
                labels(zone)[0] AS zone_label,
                COALESCE(zone_props.name, 'Unnamed') AS name,
                COALESCE(zone_props.primary_ns, 'Unknown') AS primary_ns,
                COALESCE(zone_props.ttl, 'Default') AS ttl
            ORDER BY zone_props.name
        """
        zones_result, _ = db.cypher_query(zones_query, {'eid': element_id})
        for row in zones_result:
            context['custom_data']['zones'].append({
                'id': row[0],
                'label': row[1],
                'name': row[2],
                'primary_ns': row[3],
                'ttl': row[4]
            })

    except Exception as e:
        context['error'] = str(e)

    return context
