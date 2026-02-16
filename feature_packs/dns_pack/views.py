# feature_packs/dns_pack/views.py

from django.shortcuts import render
from django.middleware.csrf import get_token
from neomodel import db
from cmdb.models import DynamicNode
from cmdb.registry import TypeRegistry

try:
    from audit_log_pack.views import create_audit_entry
except Exception:
    def create_audit_entry(*args, **kwargs):
        pass


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


def dns_record_edit_modal(request, label, element_id):
    """
    Custom edit modal for DNS_Record with zone and IP/CNAME relationship selection.
    """
    node_class = DynamicNode.get_or_create_label(label)
    node = node_class.get_by_element_id(element_id)
    if not node:
        return render(request, 'dns_record_edit_modal.html', {
            'label': label,
            'element_id': element_id,
            'error': 'DNS Record not found.'
        })

    meta = TypeRegistry.get_metadata(label)
    required_props = meta.get('required', [])
    props = meta.get('properties', [])

    rr_types = ['A', 'AAAA', 'CNAME', 'TXT', 'MX', 'NS', 'SRV', 'PTR', 'CAA']

    current_props = node.custom_properties or {}
    form_fields = []
    for prop_def in props:
        prop_name = prop_def if isinstance(prop_def, str) else prop_def.get('name', '')
        choices = prop_def.get('choices') if isinstance(prop_def, dict) else None
        if not prop_name:
            continue

        field_data = {
            'key': prop_name,
            'value': current_props.get(prop_name, ''),
            'type': 'select' if choices else 'text',
            'input_name': f'prop_{prop_name}',
            'required': prop_name in required_props,
        }
        if choices:
            field_data['choices'] = choices
        form_fields.append(field_data)

    name_field = next((field for field in form_fields if field['key'] == 'name'), None)
    other_fields = [field for field in form_fields if field['key'] not in ['name', 'type']]

    out_rels = node.get_outgoing_relationships()
    current_zone = (out_rels.get('PART_OF') or [None])[0]
    current_resolve = (out_rels.get('RESOLVES_TO') or [None])[0]

    context = {
        'label': label,
        'element_id': element_id,
        'csrf_token': get_token(request),
        'form_fields': form_fields,
        'name_field': name_field,
        'other_fields': other_fields,
        'rr_types': rr_types,
        'current_zone': current_zone,
        'current_resolve': current_resolve,
        'current_type': (current_props.get('type') or '').upper(),
    }

    if request.method == 'GET':
        return render(request, 'dns_record_edit_modal.html', context)

    try:
        new_props_from_fields = {}
        for key, value in request.POST.items():
            if key.startswith('prop_'):
                prop_key = key[5:]
                if value.lower() in ('true', 'false'):
                    new_props_from_fields[prop_key] = value.lower() == 'true'
                elif value.replace('.', '', 1).replace('-', '', 1).isdigit():
                    if '.' in value:
                        new_props_from_fields[prop_key] = float(value)
                    else:
                        new_props_from_fields[prop_key] = int(value)
                else:
                    new_props_from_fields[prop_key] = value

        record_type = new_props_from_fields.get('type', '').strip().upper()
        if record_type and record_type not in rr_types:
            context['error'] = f"Invalid DNS record type: {record_type}"
            return render(request, 'dns_record_edit_modal.html', context)

        missing = [r for r in required_props if r not in new_props_from_fields or new_props_from_fields[r] == '']
        if missing:
            context['error'] = f"Missing required properties: {', '.join(missing)}"
            return render(request, 'dns_record_edit_modal.html', context)

        zone_id = request.POST.get('zone_id', '').strip()
        ip_id = request.POST.get('ip_id', '').strip()
        record_id = request.POST.get('record_id', '').strip()
        if not zone_id:
            context['error'] = 'DNS Zone is required.'
            return render(request, 'dns_record_edit_modal.html', context)

        if record_type in ['A', 'AAAA']:
            if not ip_id:
                context['error'] = 'IP Address is required for A/AAAA records.'
                return render(request, 'dns_record_edit_modal.html', context)
        elif record_type == 'CNAME':
            if not record_id:
                context['error'] = 'Target DNS Record is required for CNAME records.'
                return render(request, 'dns_record_edit_modal.html', context)

        node.custom_properties = new_props_from_fields
        node.save()

        # Reset relationships
        for target in out_rels.get('PART_OF', []):
            node_class.disconnect_nodes(element_id, label, 'PART_OF', target['target_id'], target['target_label'])
        for target in out_rels.get('RESOLVES_TO', []):
            node_class.disconnect_nodes(element_id, label, 'RESOLVES_TO', target['target_id'], target['target_label'])

        node_class.connect_nodes(element_id, label, 'PART_OF', zone_id, 'DNS_Zone')
        if record_type in ['A', 'AAAA'] and ip_id:
            node_class.connect_nodes(element_id, label, 'RESOLVES_TO', ip_id, 'IP_Address')
        elif record_type == 'CNAME' and record_id:
            node_class.connect_nodes(element_id, label, 'RESOLVES_TO', record_id, 'DNS_Record')

        node_name = new_props_from_fields.get('name', '')
        create_audit_entry(
            action='update',
            node_label=label,
            node_id=element_id,
            node_name=node_name,
            user=request.user.username if request.user.is_authenticated else 'System',
            changes=f"Updated properties: {', '.join(new_props_from_fields.keys())}"
        )

        return render(request, 'cmdb/partials/edit_success.html', {
            'message': 'Node updated successfully'
        })
    except Exception as e:
        context['error'] = str(e)
        return render(request, 'dns_record_edit_modal.html', context)


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


def dns_record_create_modal(request, label):
    """
    Custom create modal for DNS_Record with zone and IP relationship selection.
    """
    meta = TypeRegistry.get_metadata(label)
    required_props = meta.get('required', [])
    props = meta.get('properties', [])

    form_fields = []
    for prop_def in props:
        prop_name = prop_def if isinstance(prop_def, str) else prop_def.get('name', '')
        choices = prop_def.get('choices') if isinstance(prop_def, dict) else None
        if not prop_name:
            continue

        field_data = {
            'key': prop_name,
            'value': '',
            'type': 'select' if choices else 'text',
            'input_name': f'prop_{prop_name}',
            'required': prop_name in required_props,
        }
        if choices:
            field_data['choices'] = choices
        form_fields.append(field_data)

    name_field = next((field for field in form_fields if field['key'] == 'name'), None)
    other_fields = [field for field in form_fields if field['key'] not in ['name', 'type']]

    rr_types = ['A', 'AAAA', 'CNAME', 'TXT', 'MX', 'NS', 'SRV', 'PTR', 'CAA']

    zones = []
    ip_addresses = []
    record_targets = []

    try:
        zone_class = DynamicNode.get_or_create_label('DNS_Zone')
        for zone in zone_class.nodes.all()[:200]:
            props_map = zone.custom_properties or {}
            zones.append({
                'id': zone.element_id,
                'name': props_map.get('name') or props_map.get('primary_ns') or zone.element_id[:8]
            })
    except Exception:
        zones = []

    try:
        ip_class = DynamicNode.get_or_create_label('IP_Address')
        for ip in ip_class.nodes.all()[:200]:
            props_map = ip.custom_properties or {}
            ip_addresses.append({
                'id': ip.element_id,
                'address': props_map.get('address') or props_map.get('name') or ip.element_id[:8]
            })
    except Exception:
        ip_addresses = []

    try:
        record_class = DynamicNode.get_or_create_label('DNS_Record')
        for record in record_class.nodes.all()[:200]:
            props_map = record.custom_properties or {}
            record_targets.append({
                'id': record.element_id,
                'name': props_map.get('name') or record.element_id[:8]
            })
    except Exception:
        record_targets = []

    context = {
        'label': label,
        'csrf_token': get_token(request),
        'form_fields': form_fields,
        'name_field': name_field,
        'other_fields': other_fields,
        'zones': zones,
        'ip_addresses': ip_addresses,
        'record_targets': record_targets,
        'rr_types': rr_types,
    }

    if request.method == 'GET':
        return render(request, 'dns_record_create_modal.html', context)

    try:
        # Collect field values (prop_*)
        new_props_from_fields = {}
        for key, value in request.POST.items():
            if key.startswith('prop_'):
                prop_key = key[5:]
                if value.lower() in ('true', 'false'):
                    new_props_from_fields[prop_key] = value.lower() == 'true'
                elif value.replace('.', '', 1).replace('-', '', 1).isdigit():
                    if '.' in value:
                        new_props_from_fields[prop_key] = float(value)
                    else:
                        new_props_from_fields[prop_key] = int(value)
                else:
                    new_props_from_fields[prop_key] = value

        record_type = new_props_from_fields.get('type', '').strip().upper()
        if record_type and record_type not in rr_types:
            context['error'] = f"Invalid DNS record type: {record_type}"
            return render(request, 'dns_record_create_modal.html', context)

        # Validate required
        missing = [r for r in required_props if r not in new_props_from_fields or new_props_from_fields[r] == '']
        if missing:
            context['error'] = f"Missing required properties: {', '.join(missing)}"
            return render(request, 'dns_record_create_modal.html', context)

        zone_id = request.POST.get('zone_id', '').strip()
        ip_id = request.POST.get('ip_id', '').strip()
        record_id = request.POST.get('record_id', '').strip()
        if not zone_id:
            context['error'] = 'DNS Zone is required.'
            return render(request, 'dns_record_create_modal.html', context)

        # Validate relationship targets based on record type
        if record_type in ['A', 'AAAA']:
            if not ip_id:
                context['error'] = 'IP Address is required for A/AAAA records.'
                return render(request, 'dns_record_create_modal.html', context)
        elif record_type == 'CNAME':
            if not record_id:
                context['error'] = 'Target DNS Record is required for CNAME records.'
                return render(request, 'dns_record_create_modal.html', context)

        node_class = DynamicNode.get_or_create_label(label)
        node = node_class(custom_properties=new_props_from_fields).save()

        node_class.connect_nodes(node.element_id, label, 'PART_OF', zone_id, 'DNS_Zone')
        if record_type in ['A', 'AAAA'] and ip_id:
            node_class.connect_nodes(node.element_id, label, 'RESOLVES_TO', ip_id, 'IP_Address')
        elif record_type == 'CNAME' and record_id:
            node_class.connect_nodes(node.element_id, label, 'RESOLVES_TO', record_id, 'DNS_Record')

        node_name = new_props_from_fields.get('name', '')
        create_audit_entry(
            action='create',
            node_label=label,
            node_id=node.element_id,
            node_name=node_name,
            user=request.user.username if request.user.is_authenticated else 'System',
            changes=f"Created with properties: {', '.join(new_props_from_fields.keys())}"
        )

        return render(request, 'cmdb/partials/create_success.html', {
            'message': f"{label} created with ID {node.element_id}"
        })
    except Exception as e:
        context['error'] = str(e)
        return render(request, 'dns_record_create_modal.html', context)
