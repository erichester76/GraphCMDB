# cmdb/views.py
from django.shortcuts import render
from .models import DynamicNode
from .registry import TypeRegistry
from django.http import HttpResponse, JsonResponse
from django.template.loader import render_to_string
from django.middleware.csrf import get_token
import json
from django.views.decorators.http import require_http_methods
from neomodel import db, RelationshipTo
from django.template import Context, Template
from django.conf import settings
import importlib

@require_http_methods(["GET", "POST"])
def type_register(request):
    if request.method == 'GET':
            types_data = []
            for label in TypeRegistry.known_labels():
                meta = TypeRegistry.get_metadata(label)
                types_data.append({
                    'label': label,
                    'display_name': meta.get('display_name', '-'),
                    'required': ', '.join(meta.get('required', [])) or '-',
                    'properties': ', '.join(meta.get('properties', [])) or '-',
                    'description': meta.get('description', '-'),
                })

            return render(request, 'cmdb/type_register.html', {
                'types_data': types_data,
                'existing_labels': TypeRegistry.known_labels(),
            })

    success_message = None
    error_message = None

    if request.method == 'POST':
        try:
            label = request.POST.get('label', '').strip()
            display_name = request.POST.get('display_name', '').strip()
            description = request.POST.get('description', '').strip()
            required_str = request.POST.get('required', '')
            properties_str = request.POST.get('properties', '')
            category = request.POST.get('category', '').strip()
            
            if not label or not display_name:
                error_message = 'Label and display name are required'
            elif label in TypeRegistry.known_labels():
                error_message = f'Type with label "{label}" already exists'
            elif not category:
                error_message = 'Category is required'
            else:
                required = [p.strip() for p in required_str.split(',') if p.strip()]
                properties = [p.strip() for p in properties_str.split(',') if p.strip()]

                relationships = {}
                i = 0
                while True:
                    rel_type_key = f'rel_type_{i}'
                    target_key = f'rel_target_{i}'
                    if rel_type_key not in request.POST:
                        break
                    rel_type = request.POST.get(rel_type_key, '').strip().upper()
                    target_label = request.POST.get(target_key, '').strip()
                    if rel_type and target_label:
                        relationships[rel_type] = {
                            'target': target_label,
                            'direction': 'out'
                        }
                    i += 1

                    TypeRegistry.register(label, {
                        'display_name': display_name,
                        'description': description,
                        'properties': properties,
                        'required': required,
                        'relationships': relationships,
                        'category': category,
})

                success_message = f'Type "{label}" registered successfully!'
        except Exception as e:
            error_message = str(e)

    types_data = []
    for label in TypeRegistry.known_labels():
        meta = TypeRegistry.get_metadata(label)
        types_data.append({
            'label': label,
            'display_name': meta.get('display_name', '-'),
            'required': ', '.join(meta.get('required', [])) or '-',
            'properties': ', '.join(meta.get('properties', [])) or '-',
            'description': meta.get('description', '-'),
        })

    return render(request, 'cmdb/type_register.html', {
        'types_data': types_data,
        'success': success_message,
        'error': error_message,
    })
    
def dashboard(request):
    labels = TypeRegistry.known_labels()
    counts = {}
    for label in labels:
        try:
            # Raw Cypher count - always accurate, no neomodel quirks
            result, _ = db.cypher_query(f"""
                MATCH (n:`{label}`)
                RETURN count(n) AS cnt
            """)
            count = result[0][0] if result else 0
            counts[label] = count
            print(f"Dashboard Cypher count for {label}: {count}")
        except Exception as e:
            print(f"Error counting {label}: {e}")
            counts[label] = 0

    context = {
        'labels': labels,
        'counts': counts,
        'all_labels': labels,
    }
    return render(request, 'cmdb/dashboard.html', context)

def nodes_list(request, label):
    """
    List view for nodes of a specific label
    Supports HTMX partial updates
    """
    try:
        node_class = DynamicNode.get_or_create_label(label)
        nodes = node_class.nodes.all()[:50]  # limit for MVP
    except Exception as e:
        print(f"Error fetching {label}: {e}")
        nodes = []
    
    # Collect all unique property keys across all nodes
    all_property_keys = set()
    for node in nodes:
        props = node.custom_properties or {}
        all_property_keys.update(props.keys())
        
        # Add a computed .name attribute to each node for template use
        if 'name' in props:
            node.display_name = props['name']
        elif props:
            # Get first property value (sorted by key)
            first_key = sorted(props.keys())[0]
            node.display_name = str(props[first_key])
        else:
            node.display_name = f"Unnamed {label}"
    
    # Sort property keys for consistent display
    sorted_property_keys = sorted(all_property_keys)
    
    # Prioritize 'name' if it exists
    if 'name' in sorted_property_keys:
        sorted_property_keys.remove('name')
        sorted_property_keys.insert(0, 'name')
            
    context = {
        'label': label,
        'nodes': nodes,
        'all_labels': TypeRegistry.known_labels(),
        'property_keys': sorted_property_keys,
        'property_keys_json': json.dumps(sorted_property_keys),
    }

    # If request is from HTMX (partial refresh), return only the table
    if request.htmx:
        return render(request, 'cmdb/partials/nodes_table.html', context)

    return render(request, 'cmdb/nodes_list.html', context)

@require_http_methods(["GET"])
def node_add_relationship_form(request, label, element_id):
    try:
        # Load node just for context (optional)
        node_class = DynamicNode.get_or_create_label(label)
        meta = TypeRegistry.get_metadata(label)
        allowed_rels = meta.get('relationships', {})

        context = {
            'label': label,
            'element_id': element_id,
            'csrf_token': get_token(request),
            'allowed_rels': allowed_rels.keys(),  # for dropdown
            'all_labels': TypeRegistry.known_labels(),
        }
        return render(request, 'cmdb/partials/add_relationship_form.html', context)
    except Exception as e:
        return HttpResponse(f'<div class="p-4 bg-red-100 text-red-800 rounded">Error loading form: {str(e)}</div>')
    
def node_detail(request, label, element_id):
    try:
        node_class = DynamicNode.get_or_create_label(label)
        query = f"""
            MATCH (n:`{label}`)
            WHERE elementId(n) = $eid
            RETURN n
        """
        result, _ = db.cypher_query(query, {'eid': element_id})
        if not result:
            raise node_class.DoesNotExist

        raw_node = result[0][0]
        node = node_class.inflate(raw_node)

        props_list = []
        for key, value in (node.custom_properties or {}).items():
            props_list.append({
                'key': key,
                'value': value,
                'value_type': type(value).__name__,
            })

        out_rels_query = f"""
            MATCH (n:`{label}`) WHERE elementId(n) = $eid
            MATCH (n)-[r]->(m)
            WITH 
                type(r) AS rel_type,
                elementId(m) AS target_id,
                labels(m)[0] AS target_label,
                apoc.convert.fromJsonMap(m.custom_properties) AS props_map
            RETURN 
                rel_type,
                target_id,
                target_label,
                COALESCE(
                    props_map.name,
                    props_map[head(keys(props_map))]
                ) AS target_name
        """

        out_rels_result, _ = db.cypher_query(out_rels_query, {'eid': element_id})

        out_rels = {}
        for row in out_rels_result:
            rel_type = row[0]
            if rel_type not in out_rels:
                out_rels[rel_type] = []
            out_rels[rel_type].append({
                'target_id': row[1],
                'target_label': row[2],
                'target_name': row[3] or row[1][:50] + '...',
            })
            
        # Fetch incoming relationships with Cypher
        in_rels_query = f"""
            MATCH (n:`{label}`) WHERE elementId(n) = $eid
            MATCH (m)-[r]->(n)
            WITH 
                type(r) AS rel_type,
                elementId(m) AS source_id,
                labels(m)[0] AS source_label,
                apoc.convert.fromJsonMap(m.custom_properties) AS props_map
            RETURN 
                rel_type,
                source_id,
                source_label,
                COALESCE(
                    props_map.name,
                    props_map[head(keys(props_map))]
                ) AS source_name
        """
        in_rels_result, _ = db.cypher_query(in_rels_query, {'eid': element_id})

        in_rels = {}
        for row in in_rels_result:
            rel_type = row[0]
            if rel_type not in in_rels:
                in_rels[rel_type] = []
            in_rels[rel_type].append({
                'source_id': row[1],
                'source_label': row[2],
                'source_name': row[3] or row[1][:50] + '...',
            })

        feature_pack_tabs = []
        for tab in getattr(settings, 'FEATURE_PACK_TABS', []):
            if label in tab.get('for_labels', []):
                tab_copy = tab.copy()
                if tab.get('custom_view'):
                    # Call the pack's custom view function
                    pack_view = importlib.import_module(tab['custom_view'].rsplit('.', 1)[0])
                    custom_view_func = getattr(pack_view, tab['custom_view'].rsplit('.', 1)[1])
                    tab_copy['context'] = custom_view_func(request, label, element_id)
                feature_pack_tabs.append(tab_copy)

        context = {
            'label': label,
            'element_id': element_id,
            'node': node,
            'properties_list': props_list,
            'outbound_relationships': out_rels,
            'inbound_relationships': in_rels,
            'all_labels': TypeRegistry.known_labels(),
            'feature_pack_tabs': feature_pack_tabs
        }
        return render(request, 'cmdb/node_detail.html', context)

    except node_class.DoesNotExist as e:
        return render(request, 'cmdb/node_detail.html', {'error': str(e)})
    except Exception as e:
        return render(request, 'cmdb/node_detail.html', {'error': f"Error: {str(e)}"})
    
@require_http_methods(["GET", "POST"])
def node_edit(request, label, element_id):
    
    try:
        node_class = DynamicNode.get_or_create_label(label)
        query = f"""
            MATCH (n:`{label}`)
            WHERE elementId(n) = $eid
            RETURN n
        """
        result, _ = db.cypher_query(query, {'eid': element_id})
        if not result:
            raise node_class.DoesNotExist

        raw_node = result[0][0]
        node = node_class.inflate(raw_node)

    except node_class.DoesNotExist:
        return JsonResponse({'error': 'Node not found'}, status=404)

    context = {
        'label': label,
        'element_id': element_id,
        'csrf_token': get_token(request),
    }

    if request.method == 'GET':
        current_props = node.custom_properties or {}
        
        # Build list of form fields
        form_fields = []
        for key, value in current_props.items():
            field_type = 'text'
            if isinstance(value, bool):
                field_type = 'checkbox'
            elif isinstance(value, (int, float)):
                field_type = 'number'
            elif isinstance(value, list):
                field_type = 'textarea'  # comma-separated
            form_fields.append({
                'key': key,
                'value': value,
                'type': field_type,
                'input_name': f'prop_{key}',  # for POST collection
            })

        context['form_fields'] = form_fields
        context['current_json'] = json.dumps(current_props, indent=2)  # fallback raw
        context['original_json'] = json.dumps(current_props)

        return render(request, 'cmdb/partials/node_edit_form.html', context)

    # POST update
    try:
        raw_json = request.POST.get('properties', '').strip()
        original_json = request.POST.get('original_json', '').strip()

        # Always collect field values first
        new_props_from_fields = {}
        for key, value in request.POST.items():
            if key.startswith('prop_'):
                prop_key = key[5:]
                # Type coercion (same as before)
                if value.lower() in ('true', 'false'):
                    new_props_from_fields[prop_key] = value.lower() == 'true'
                elif value.replace('.', '', 1).replace('-', '', 1).isdigit():
                    if '.' in value:
                        new_props_from_fields[prop_key] = float(value)
                    else:
                        new_props_from_fields[prop_key] = int(value)
                else:
                    new_props_from_fields[prop_key] = value

        new_props = new_props_from_fields  # Default to fields

        # If raw JSON is provided and changed, override with it
        if raw_json:
            try:
                raw_props = json.loads(raw_json)
                # Compare without whitespace/formatting (normalize)
                normalized_raw = json.dumps(raw_props, sort_keys=True)
                normalized_original = json.dumps(json.loads(original_json or '{}'), sort_keys=True)
                if normalized_raw != normalized_original:
                    new_props = raw_props  # Override with raw JSON
            except json.JSONDecodeError:
                # Invalid raw → ignore, use fields
                pass

        # Merge with existing
        current = node.custom_properties or {}
        current.update(new_props)
        node.custom_properties = current
        node.save()

        return render(request, 'cmdb/partials/edit_success.html', {
            'message': 'Node updated successfully'
        })


    except Exception as e:
        context = {
            'label': label,
            'element_id': element_id,
            'csrf_token': get_token(request),
            'current_properties': request.POST.get('properties', '{}'),
            'error': str(e)
        }
        return render(request, 'cmdb/partials/node_edit_form.html', context)
    
    
@require_http_methods(["POST"])
def node_delete(request, label, element_id):
    try:
        node_class = DynamicNode.get_or_create_label(label)
        # Cypher lookup
        query = f"""
            MATCH (n:`{label}`)
            WHERE elementId(n) = $eid
            RETURN n
        """
        result, _ = db.cypher_query(query, {'eid': element_id})
        if not result:
            return JsonResponse({'error': 'Node not found'}, status=404)

        raw_node = result[0][0]
        node = node_class.inflate(raw_node)
        node.delete()

        # Return refreshed table body (same as nodes_list partial)
        nodes = node_class.nodes.all()[:50]
        return render(request, 'cmdb/partials/nodes_table.html', {
            'nodes': nodes,
            'label': label,
        })

    except Exception as e:
        return render(request, 'cmdb/partials/nodes_table.html', {
            'nodes': [],
            'label': label,
            'error': str(e)
        })
        
@require_http_methods(["GET", "POST"])
def node_create(request, label):
    try:
        meta = TypeRegistry.get_metadata(label)
        if not meta:
            raise ValueError(f"No metadata for label '{label}'")

        required_props = meta.get('required_properties', [])
        optional_props = meta.get('optional_properties', [])

        context = {
            'label': label,
            'csrf_token': get_token(request),
            'required_props': required_props,
            'optional_props': optional_props,
            'all_props': required_props + optional_props,
        }

        if request.method == 'GET':
            # Build dynamic fields from registry
            required_props = meta.get('required', [])
            props = meta.get('properties', [])

            form_fields = []
            
            for key in props:
                form_fields.append({
                    'key': key,
                    'value': '',
                    'type': 'text',
                    'input_name': f'prop_{key}',
                    'required': key in required_props,
                })
            
            context = {
                'label': label,
                'csrf_token': get_token(request),
                'form_fields': form_fields,
            }
            return render(request, 'cmdb/partials/node_create_form.html', context)

        # POST handling
        try:
            properties_str = request.POST.get('properties', '').strip()

            # Parse raw JSON if provided
            raw_json_dict = {}
            if properties_str:
                try:
                    raw_json_dict = json.loads(properties_str)
                    if not isinstance(raw_json_dict, dict):
                        raise ValueError("Raw JSON must be a dict/map")
                except json.JSONDecodeError as e:
                    return render(request, 'cmdb/partials/node_create_form.html', {
                        'label': label,
                        'error': f'Invalid raw JSON: {str(e)}',
                        'form_fields': form_fields,
                    })

            # Collect field values (prop_*)
            new_props_from_fields = {}
            for key, value in request.POST.items():
                if key.startswith('prop_'):
                    prop_key = key[5:]
                    # Type coercion
                    if value.lower() in ('true', 'false'):
                        new_props_from_fields[prop_key] = value.lower() == 'true'
                    elif value.replace('.', '', 1).replace('-', '', 1).isdigit():
                        if '.' in value:
                            new_props_from_fields[prop_key] = float(value)
                        else:
                            new_props_from_fields[prop_key] = int(value)
                    else:
                        new_props_from_fields[prop_key] = value

            # Merge raw JSON (base) + fields (override)
            new_props = raw_json_dict
            new_props.update(new_props_from_fields)

            # Validate required
            meta = TypeRegistry.get_metadata(label)
            required = meta.get('required_properties', [])
            missing = [r for r in required if r not in new_props]
            if missing:
                return render(request, 'cmdb/partials/node_create_form.html', {
                    'label': label,
                    'error': f"Missing required properties: {', '.join(missing)}",
                    'form_fields': form_fields,
                })
            
            # Save as dict (not string)
            node_class = DynamicNode.get_or_create_label(label)
            node = node_class(custom_properties=new_props).save()  

            # Success
            return render(request, 'cmdb/partials/create_success.html', {
                'message': f"{label} created with ID {node.element_id}"
            })

        except Exception as e:
            return render(request, 'cmdb/partials/node_create_form.html', {
                'label': label,
                'error': str(e),
                'form_fields': form_fields,
            })
            
            
    except Exception as e:
        context['error'] = str(e)
        return render(request, 'cmdb/partials/node_create_form.html', context)

@require_http_methods(["POST"]) 
def node_connect(request, label, element_id):
    try:
        rel_type = request.POST.get('rel_type', '').strip().upper()
        target_label = request.POST.get('target_label', '').strip()
        target_id = request.POST.get('target_id', '').strip()

        if not rel_type or not target_label or not target_id:
            raise ValueError("Missing relationship details")

        connect_query = f"""
            MATCH (source:`{label}`) WHERE elementId(source) = $sid
            MATCH (target:`{target_label}`) WHERE elementId(target) = $tid
            MERGE (source)-[:`{rel_type}`]->(target)
            RETURN elementId(source) AS source_id
        """
        result, _ = db.cypher_query(connect_query, {'sid': element_id, 'tid': target_id})
        if not result:
            raise ValueError("Failed to create relationship")

        out_rels_query = f"""
            MATCH (n:`{label}`) WHERE elementId(n) = $eid
            MATCH (n)-[r]->(m)
            RETURN type(r) AS rel_type, elementId(m) AS target_id, labels(m)[0] AS target_label,
                apoc.convert.fromJsonMap(m.custom_properties).name AS target_name
        """
        out_rels_result, _ = db.cypher_query(out_rels_query, {'eid': element_id})

        out_rels = {}
        for row in out_rels_result:
            rel_type = row[0]
            if rel_type not in out_rels:
                out_rels[rel_type] = []
            out_rels[rel_type].append({
                'target_id': row[1],
                'target_label': row[2],
                'target_name': row[3] or row[1][:12] + '...',
            })
            
        # Fetch incoming relationships with Cypher
        in_rels_query = f"""
            MATCH (n:`{label}`) WHERE elementId(n) = $eid
            MATCH (m)-[r]->(n)
            RETURN type(r) AS rel_type, elementId(m) AS target_id, labels(m)[0] AS target_label,
                apoc.convert.fromJsonMap(m.custom_properties).name AS target_name
        """
        in_rels_result, _ = db.cypher_query(in_rels_query, {'eid': element_id})

        in_rels = {}
        for row in in_rels_result:
            rel_type = row[0]
            if rel_type not in in_rels:
                in_rels[rel_type] = []
            in_rels[rel_type].append({
                'source_id': row[1],
                'source_label': row[2],
                'source_name': row[3] or row[1][:12] + '...',
            })

        return render(request, 'cmdb/partials/node_relationships.html', {
            'inbound_relationships': in_rels,
            'outbound_relationships': out_rels,
            'element_id': element_id,
            'label': label,
            'success_message': f"Relationship '{rel_type}' removed"
        })
    except Exception as e:
        rels = {}
        return render(request, 'cmdb/partials/node_relationships.html', {
            'relationships': rels,
            'element_id': element_id,
            'label': label,
            'error_message': str(e)
        })
        
@require_http_methods(["POST"])
def node_disconnect(request, label, element_id):
    try:
        rel_type = request.POST.get('rel_type', '').strip().upper()
        target_id = request.POST.get('target_id', '').strip()
        target_label = request.POST.get('target_label', '').strip()

        if not rel_type or not target_id or not target_label:
            raise ValueError("Missing disconnect details")

        disconnect_query = f"""
            MATCH (source:`{label}`)-[r:`{rel_type}`]->(target:`{target_label}`)
            WHERE elementId(source) = $sid AND elementId(target) = $tid
            DELETE r
            RETURN count(r) AS deleted
        """
        result, _ = db.cypher_query(disconnect_query, {'sid': element_id, 'tid': target_id})

        deleted = result[0][0] if result else 0
        if deleted == 0:
            raise ValueError("Relationship not found")

        out_rels_query = f"""
            MATCH (n:`{label}`) WHERE elementId(n) = $eid
            MATCH (n)-[r]->(m)
            RETURN type(r) AS rel_type, elementId(m) AS target_id, labels(m)[0] AS target_label,
                apoc.convert.fromJsonMap(m.custom_properties).name AS target_name
        """
        out_rels_result, _ = db.cypher_query(out_rels_query, {'eid': element_id})

        out_rels = {}
        for row in out_rels_result:
            rel_type = row[0]
            if rel_type not in out_rels:
                out_rels[rel_type] = []
            out_rels[rel_type].append({
                'target_id': row[1],
                'target_label': row[2],
                'target_name': row[3] or row[1][:12] + '...',
            })
            
        # Fetch incoming relationships with Cypher
        in_rels_query = f"""
            MATCH (n:`{label}`) WHERE elementId(n) = $eid
            MATCH (m)-[r]->(n)
            RETURN type(r) AS rel_type, elementId(m) AS target_id, labels(m)[0] AS target_label,
                apoc.convert.fromJsonMap(m.custom_properties).name AS target_name
        """
        in_rels_result, _ = db.cypher_query(in_rels_query, {'eid': element_id})

        in_rels = {}
        for row in in_rels_result:
            rel_type = row[0]
            if rel_type not in in_rels:
                in_rels[rel_type] = []
            in_rels[rel_type].append({
                'source_id': row[1],
                'source_label': row[2],
                'source_name': row[3] or row[1][:12] + '...',
            })

        return render(request, 'cmdb/partials/node_relationships.html', {
            'inbound_relationships': in_rels,
            'outbound_relationships': out_rels,
            'element_id': element_id,
            'label': label,
            'success_message': f"Relationship '{rel_type}' removed"
        })

    except Exception as e:
        rels = {}
        return render(request, 'cmdb/partials/node_relationships.html', {
            'relationships': rels,
            'element_id': element_id,
            'label': label,
            'error_message': str(e)
        })
        
@require_http_methods(["GET"])
def get_target_nodes(request):
    target_label = request.GET.get('target_label', '').strip()
    if not target_label:
        return HttpResponse('<option disabled>No label selected</option>')

    try:
        node_class = DynamicNode.get_or_create_label(target_label)
        nodes = node_class.nodes.all()[:50]

        sorted_nodes = sorted(nodes, key=lambda n: n.custom_properties.get('name', n.element_id))

        # Load the partial template manually as string
        template = Template(open('cmdb/templates/cmdb/partials/target_node_options.html').read())
        html = template.render(Context({
            'nodes': sorted_nodes,
            'target_label': target_label,
        }))

        return HttpResponse(html)

    except Exception as e:
        return HttpResponse(f'<option disabled>Error loading nodes for {target_label}: {str(e)}</option>')