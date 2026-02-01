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

@require_http_methods(["GET", "POST"])
def type_register(request):
    if request.method == 'GET':
            # Build list of dicts for template
            types_data = []
            for label in TypeRegistry.known_labels():
                meta = TypeRegistry.get_metadata(label)
                types_data.append({
                    'label': label,
                    'display_name': meta.get('display_name', '-'),
                    'required_properties': ', '.join(meta.get('required_properties', [])) or '-',
                    'optional_properties': ', '.join(meta.get('optional_properties', [])) or '-',
                    'description': meta.get('description', '-'),
                })

            return render(request, 'cmdb/type_register.html', {
                'types_data': types_data,
                'existing_labels': TypeRegistry.known_labels(),  # optional fallback
            })
            
    success_message = None
    error_message = None

    # POST handling
    if request.method == 'POST':
        try:
            label = request.POST.get('label', '').strip()
            display_name = request.POST.get('display_name', '').strip()
            description = request.POST.get('description', '').strip()
            required_str = request.POST.get('required_properties', '')
            optional_str = request.POST.get('optional_properties', '')

            if not label or not display_name:
                error_message = 'Label and display name are required'
            elif label in TypeRegistry.known_labels():
                error_message = f'Type with label "{label}" already exists'
            else:
                required = [p.strip() for p in required_str.split(',') if p.strip()]
                optional = [p.strip() for p in optional_str.split(',') if p.strip()]

                # Process relationships
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
                            'direction': 'out'  # MVP: only outgoing
                        }
                    i += 1

                TypeRegistry.register(label, {
                    'display_name': display_name,
                    'description': description,
                    'required_properties': required,
                    'optional_properties': optional,
                    'relationships': relationships,
                })

                success_message = f'Type "{label}" registered successfully!'
        except Exception as e:
            error_message = str(e)

    # Always compute fresh data for display (GET or after POST)
    types_data = []
    for label in TypeRegistry.known_labels():
        meta = TypeRegistry.get_metadata(label)
        types_data.append({
            'label': label,
            'display_name': meta.get('display_name', '-'),
            'required_properties': ', '.join(meta.get('required_properties', [])) or '-',
            'optional_properties': ', '.join(meta.get('optional_properties', [])) or '-',
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

    context = {
        'label': label,
        'nodes': nodes,
        'all_labels': TypeRegistry.known_labels(),
    }

    # If request is from HTMX (partial refresh), return only the table
    if request.htmx:
        return render(request, 'cmdb/partials/nodes_table.html', context)

    return render(request, 'cmdb/nodes_list.html', context)

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

        # Pre-process properties for display
        props_list = []
        for key, value in (node.custom_properties or {}).items():
            props_list.append({
                'key': key,
                'value': value,
                'value_type': type(value).__name__,
            })

        rels = {}
        for attr in dir(node):
            if attr.isupper() and not attr.startswith('_'):
                rel = getattr(node, attr)
                if hasattr(rel, 'all'):
                    rels[attr] = [
                        {'target_id': t.element_id, 'target_label': t.__label__}
                        for t in rel.all()
                    ]

        context = {
            'label': label,
            'element_id': element_id,
            'node': node,
            'properties_list': props_list,  # ← new
            'relationships': rels,
            'all_labels': TypeRegistry.known_labels(),
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
            # Pre-fill form fields (empty values)
            form_fields = []
            for key in context['all_props']:
                form_fields.append({
                    'key': key,
                    'value': '',  # empty
                    'type': 'text',  # default, can infer later
                    'input_name': f'prop_{key}',
                    'required': key in required_props,
                })
            context['form_fields'] = form_fields
            return render(request, 'cmdb/partials/node_create_form.html', context)

        # POST: process creation
        new_props = {}
        for key, value in request.POST.items():
            if key.startswith('prop_'):
                prop_key = key[5:]
                # Type coercion
                if value.lower() in ('true', 'false'):
                    new_props[prop_key] = value.lower() == 'true'
                elif value.replace('.', '', 1).replace('-', '', 1).isdigit():
                    if '.' in value:
                        new_props[prop_key] = float(value)
                    else:
                        new_props[prop_key] = int(value)
                else:
                    new_props[prop_key] = value

        # Validate required fields
        missing = [r for r in required_props if r not in new_props]
        if missing:
            context['error'] = f"Missing required properties: {', '.join(missing)}"
            return render(request, 'cmdb/partials/node_create_form.html', context)

        # Save
        node_class = DynamicNode.get_or_create_label(label)
        node = node_class(custom_properties=new_props).save()

        return render(request, 'cmdb/partials/create_success.html', {
            'message': f"{label} created with ID {node.element_id}"
        })

    except Exception as e:
        context['error'] = str(e)
        return render(request, 'cmdb/partials/node_create_form.html', context)
    
@require_http_methods(["POST"])
def node_connect(request, label, element_id):
    try:
        node_class = DynamicNode.get_or_create_label(label)

        # Load source node
        query = f"""
            MATCH (n:`{label}`)
            WHERE elementId(n) = $eid
            RETURN n
        """
        result, _ = db.cypher_query(query, {'eid': element_id})
        if not result:
            raise node_class.DoesNotExist("Source node not found")

        raw_node = result[0][0]
        node = node_class.inflate(raw_node)

        rel_type = request.POST.get('rel_type', '').upper()
        target_label = request.POST.get('target_label', '')
        target_id = request.POST.get('target_id', '')

        if not rel_type or not target_label or not target_id:
            raise ValueError("Missing relationship details")

        # Optional validation
        meta = TypeRegistry.get_metadata(label)
        allowed_rels = meta.get('relationships', {})
        if rel_type not in allowed_rels:
            raise ValueError(f"Invalid relationship type {rel_type} for {label}")

        # Define relationship on the class if missing
        if not hasattr(node_class, rel_type):
            from neomodel import RelationshipTo
            setattr(node_class, rel_type, RelationshipTo(target_label, rel_type))

            # Critical: Re-install labels to register the new relationship
            from neomodel import install_labels
            install_labels(node_class)

            # Reload the node instance to reflect the new class attribute
            # (re-inflate from raw)
            node = node_class.inflate(raw_node)  # Re-inflate with updated class

        # Get accessor from reloaded instance
        rel_accessor = getattr(node, rel_type)

        # Load target node
        target_class = DynamicNode.get_or_create_label(target_label)
        target_query = f"""
            MATCH (t:`{target_label}`)
            WHERE elementId(t) = $tid
            RETURN t
        """
        target_result, _ = db.cypher_query(target_query, {'tid': target_id})
        if not target_result:
            raise target_class.DoesNotExist(f"Target node {target_id} not found")

        raw_target = target_result[0][0]
        target = target_class.inflate(raw_target)

        # Connect
        rel_accessor.connect(target)

        # Refresh relationships
        rels = {}
        for attr in dir(node):
            if attr.isupper() and not attr.startswith('_'):
                r = getattr(node, attr)
                if hasattr(r, 'all'):
                    rels[attr] = [
                        {'target_id': t.element_id, 'target_label': t.__label__}
                        for t in r.all()
                    ]

        return render(request, 'cmdb/partials/node_relationships.html', {
            'relationships': rels,
            'element_id': element_id,
            'label': label,
            'success_message': f"Relationship {rel_type} added"
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
        node_class = DynamicNode.get_or_create_label(label)
        query = f"MATCH (n:`{label}`) WHERE elementId(n) = $eid RETURN n"
        result, _ = db.cypher_query(query, {'eid': element_id})
        if not result:
            return JsonResponse({'error': 'Node not found'}, status=404)

        raw_node = result[0][0]
        node = node_class.inflate(raw_node)

        rel_type = request.POST.get('rel_type', '').upper()
        target_id = request.POST.get('target_id', '')

        if not rel_type or not target_id:
            return JsonResponse({'error': 'Missing disconnect details'}, status=400)

        if not hasattr(node, rel_type):
            return JsonResponse({'error': f"No such relationship {rel_type}"}, status=400)

        rel = getattr(node, rel_type)
        target_class = DynamicNode.get_or_create_label(request.POST.get('target_label', ''))
        target = target_class.nodes.get(element_id=target_id)

        rel.disconnect(target)

        # Return refreshed relationships partial
        rels = {}
        for attr in dir(node):
            if attr.isupper() and not attr.startswith('_'):
                r = getattr(node, attr)
                if hasattr(r, 'all'):
                    rels[attr] = [{'target_id': t.element_id, 'target_label': t.__label__} for t in r.all()]

        return render(request, 'cmdb/partials/node_relationships.html', {
            'relationships': rels,
            'element_id': element_id,
            'label': label,
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)
    
@require_http_methods(["GET"])
def get_target_nodes(request):
    target_label = request.GET.get('target_label', '').strip()
    if not target_label:
        return HttpResponse('<option disabled>No label selected</option>')

    try:
        node_class = DynamicNode.get_or_create_label(target_label)
        nodes = node_class.nodes.all()[:50]

        sorted_nodes = sorted(nodes, key=lambda n: n.custom_properties.get('name', n.element_id))

        # Render just the partial as string (no layout)
        html = render_to_string('cmdb/partials/target_node_options.html', {
            'nodes': sorted_nodes,
            'target_label': target_label,
        }, request=request)

        return HttpResponse(html)

    except Exception as e:
        return HttpResponse(
            f'<option disabled>Error loading nodes for {target_label}: {str(e)}</option>'
        )