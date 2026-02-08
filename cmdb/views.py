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

# Import audit log utility if available
try:
    import sys
    import os
    # Add feature_packs to sys.path if not already there
    feature_packs_path = os.path.join(settings.BASE_DIR, 'feature_packs')
    if feature_packs_path not in sys.path:
        sys.path.insert(0, feature_packs_path)
    from audit_log_pack.views import create_audit_entry
except ImportError:
    # If audit log pack is not available, use a no-op function
    def create_audit_entry(*args, **kwargs):
        pass

def build_properties_list_with_relationships(node):
    """
    Helper function to build a properties list that includes both regular properties
    and relationships formatted as properties.
    
    Args:
        node: A DynamicNode instance
        
    Returns:
        list: A list of property dictionaries with keys: key, value, value_type, 
              is_relationship, and optionally relationship_direction and relationship_data
    """
    custom_props = node.custom_properties or {}
    props_list = []
    
    # Add regular properties
    for key, value in custom_props.items():
        props_list.append({
            'key': key,
            'value': value,
            'value_type': type(value).__name__,
            'is_relationship': False,
        })
    
    # Get relationships
    out_rels = node.get_outgoing_relationships()
    in_rels = node.get_incoming_relationships()
    
    # Add outbound relationships as properties
    for rel_type, targets in out_rels.items():
        target_values = [f"{t['target_label']}:{t['target_name']}" for t in targets]
        props_list.append({
            'key': rel_type,
            'value': ', '.join(target_values),
            'value_type': 'relationship',
            'is_relationship': True,
            'relationship_direction': 'outbound',
            'relationship_data': targets,
        })
    
    # Add inbound relationships as properties
    for rel_type, sources in in_rels.items():
        source_values = [f"{s['source_label']}:{s['source_name']}" for s in sources]
        props_list.append({
            'key': f"{rel_type} (incoming)",
            'value': ', '.join(source_values),
            'value_type': 'relationship',
            'is_relationship': True,
            'relationship_direction': 'inbound',
            'relationship_data': sources,
        })
    
    return props_list

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
            # Use Neomodel's count method instead of raw Cypher
            node_class = DynamicNode.get_or_create_label(label)
            count = node_class.nodes.count()
            counts[label] = count
            print(f"Dashboard Neomodel count for {label}: {count}")
        except Exception as e:
            print(f"Error counting {label}: {e}")
            counts[label] = 0

    context = {
        'labels': labels,
        'counts': counts,
        'all_labels': labels,
    }
    
    # If HTMX request, include header partial for out-of-band swap
    if request.htmx:
        content_html = render_to_string('cmdb/partials/dashboard_content.html', context, request=request)
        header_html = render_to_string('cmdb/partials/dashboard_header.html', context, request=request)
        return HttpResponse(content_html + header_html)
    
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
    
    # Get column configuration from type registry
    metadata = TypeRegistry.get_metadata(label)
    default_columns = metadata.get('columns', [])
    all_properties = metadata.get('properties', [])
    
    # Collect all relationship types found across all nodes
    all_relationship_types = set()
    
    # Extract property values for each node - FOR ALL PROPERTIES, not just default columns
    nodes_data = []
    for node in nodes:
        props = node.custom_properties or {}
        node_data = {
            'element_id': node.element_id,
            'node': node,
            'columns': {}
        }
        
        # Extract values for ALL properties (so DOM elements exist for column toggle)
        for prop in all_properties:
            node_data['columns'][prop] = props.get(prop, '')
        
        # Fetch relationships for this node
        out_rels = node.get_outgoing_relationships()
        in_rels = node.get_incoming_relationships()
        
        # Add outbound relationships as columns
        for rel_type, targets in out_rels.items():
            all_relationship_types.add(rel_type)
            target_values = [f"{t['target_label']}:{t['target_name']}" for t in targets]
            node_data['columns'][rel_type] = ', '.join(target_values)
        
        # Add inbound relationships as columns
        for rel_type, sources in in_rels.items():
            rel_key = f"{rel_type} (incoming)"
            all_relationship_types.add(rel_key)
            source_values = [f"{s['source_label']}:{s['source_name']}" for s in sources]
            node_data['columns'][rel_key] = ', '.join(source_values)
        
        # Also compute display_name for backwards compatibility
        if 'name' in props:
            node_data['display_name'] = props['name']
        elif props:
            first_key = sorted(props.keys())[0]
            node_data['display_name'] = str(props[first_key])
        else:
            node_data['display_name'] = f"Unnamed {label}"
            
        nodes_data.append(node_data)
    
    # Combine properties and relationships for all_properties list
    all_properties_with_rels = list(all_properties) + sorted(all_relationship_types)
            
    context = {
        'label': label,
        'nodes': nodes_data,
        'columns': default_columns,
        'columns_json': json.dumps(default_columns),
        'all_properties': all_properties_with_rels,
        'all_properties_json': json.dumps(all_properties_with_rels),
        'all_labels': TypeRegistry.known_labels(),
    }

    # If request is from HTMX, return content + header for OOB swap
    if request.htmx:
        # Check if this is a table-only refresh (from refresh button)
        if request.headers.get('HX-Target') == 'nodes-content':
            return render(request, 'cmdb/partials/nodes_table.html', context)
        # Otherwise it's a full navigation, include header
        content_html = render_to_string('cmdb/partials/nodes_list_content.html', context, request=request)
        header_html = render_to_string('cmdb/partials/nodes_list_header.html', context, request=request)
        return HttpResponse(content_html + header_html)

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
        # Use helper method instead of raw Cypher
        node = node_class.get_by_element_id(element_id)
        if not node:
            raise node_class.DoesNotExist

        # Extract display name first
        custom_props = node.custom_properties or {}
        display_name = custom_props.get('name')
        if not display_name:
            display_name = f"{element_id[:8]}..."
        
        # Build properties list with relationships using helper function
        props_list = build_properties_list_with_relationships(node)
        
        # Get relationships for backwards compatibility with templates
        out_rels = node.get_outgoing_relationships()
        in_rels = node.get_incoming_relationships()

        feature_pack_tabs = []
        for tab in getattr(settings, 'FEATURE_PACK_TABS', []):
            # Check if tab applies to this label
            # Empty for_labels means apply to all labels
            tab_for_labels = tab.get('for_labels', [])
            if not tab_for_labels or label in tab_for_labels:
                tab_copy = tab.copy()
                # Set default tab_order if not specified
                # Tab ordering: 0 = first (before Core Details), 1 = Core Details, 2+ = after Core Details
                # Valid range: 0-100 (sorted left to right)
                if 'tab_order' not in tab_copy:
                    tab_copy['tab_order'] = 2  # Default feature pack tabs come after core details (1)
                if tab.get('custom_view'):
                    # Call the pack's custom view function
                    pack_view = importlib.import_module(tab['custom_view'].rsplit('.', 1)[0])
                    custom_view_func = getattr(pack_view, tab['custom_view'].rsplit('.', 1)[1])
                    tab_copy['context'] = custom_view_func(request, label, element_id)
                feature_pack_tabs.append(tab_copy)
        
        # Sort tabs by tab_order (0-100 range, left to right)
        feature_pack_tabs.sort(key=lambda x: x.get('tab_order', 2))
        
        # Determine initial active tab: first tab with order 0, otherwise 'core'
        initial_active_tab = 'core'
        if feature_pack_tabs and feature_pack_tabs[0].get('tab_order') == 0:
            initial_active_tab = feature_pack_tabs[0]['id']

        context = {
            'label': label,
            'element_id': element_id,
            'node': node,
            'display_name': display_name,
            'properties_list': props_list,
            'outbound_relationships': out_rels,
            'inbound_relationships': in_rels,
            'all_labels': TypeRegistry.known_labels(),
            'feature_pack_tabs': feature_pack_tabs,
            'initial_active_tab': initial_active_tab,
        }
        
        # If HTMX request, include header partial for out-of-band swap
        if request.htmx:
            content_html = render_to_string('cmdb/partials/node_detail_content.html', context, request=request)
            header_html = render_to_string('cmdb/partials/node_detail_header.html', context, request=request)
            return HttpResponse(content_html + header_html)
        
        return render(request, 'cmdb/node_detail.html', context)

    except node_class.DoesNotExist as e:
        return render(request, 'cmdb/node_detail.html', {'error': str(e)})
    except Exception as e:
        return render(request, 'cmdb/node_detail.html', {'error': f"Error: {str(e)}"})
    
@require_http_methods(["GET", "POST"])
def node_edit(request, label, element_id):
    
    try:
        node_class = DynamicNode.get_or_create_label(label)
        # Use helper method instead of raw Cypher
        node = node_class.get_by_element_id(element_id)
        if not node:
            raise node_class.DoesNotExist

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
        old_props = current.copy()
        current.update(new_props)
        node.custom_properties = current
        node.save()

        # Create audit log entry
        node_name = current.get('name', '')
        changed_keys = [k for k in new_props.keys() if old_props.get(k) != new_props.get(k)]
        create_audit_entry(
            action='update',
            node_label=label,
            node_id=element_id,
            node_name=node_name,
            user=request.user.username if request.user.is_authenticated else 'System',
            changes=f"Updated properties: {', '.join(changed_keys)}" if changed_keys else "Properties updated"
        )

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
        # Use helper method instead of raw Cypher
        node = node_class.get_by_element_id(element_id)
        if not node:
            return JsonResponse({'error': 'Node not found'}, status=404)

        # Store node info before deleting for audit log
        node_name = (node.custom_properties or {}).get('name', '')
        
        # Create audit log entry before deletion
        create_audit_entry(
            action='delete',
            node_label=label,
            node_id=element_id,
            node_name=node_name,
            user=request.user.username if request.user.is_authenticated else 'System',
            changes='Node deleted'
        )

        node.delete()

        # Return refreshed table body (same as nodes_list partial)
        nodes = node_class.nodes.all()[:50]
        
        # Get column configuration from type registry
        metadata = TypeRegistry.get_metadata(label)
        default_columns = metadata.get('columns', [])
        all_properties = metadata.get('properties', [])
        
        # Collect all relationship types found across all nodes
        all_relationship_types = set()
        
        # Extract property values for each node - FOR ALL PROPERTIES
        nodes_data = []
        for node in nodes:
            props = node.custom_properties or {}
            node_data = {
                'element_id': node.element_id,
                'node': node,
                'columns': {}
            }
            
            # Extract values for ALL properties (so DOM elements exist for column toggle)
            for prop in all_properties:
                node_data['columns'][prop] = props.get(prop, '')
            
            # Fetch relationships for this node
            out_rels = node.get_outgoing_relationships()
            in_rels = node.get_incoming_relationships()
            
            # Add outbound relationships as columns
            for rel_type, targets in out_rels.items():
                all_relationship_types.add(rel_type)
                target_values = [f"{t['target_label']}:{t['target_name']}" for t in targets]
                node_data['columns'][rel_type] = ', '.join(target_values)
            
            # Add inbound relationships as columns
            for rel_type, sources in in_rels.items():
                rel_key = f"{rel_type} (incoming)"
                all_relationship_types.add(rel_key)
                source_values = [f"{s['source_label']}:{s['source_name']}" for s in sources]
                node_data['columns'][rel_key] = ', '.join(source_values)
            
            nodes_data.append(node_data)
        
        # Combine properties and relationships for all_properties list
        all_properties_with_rels = list(all_properties) + sorted(all_relationship_types)
        
        return render(request, 'cmdb/partials/nodes_table.html', {
            'nodes': nodes_data,
            'columns': default_columns,
            'all_properties': all_properties_with_rels,
            'label': label,
        })

    except Exception as e:
        return render(request, 'cmdb/partials/nodes_table.html', {
            'nodes': [],
            'columns': [],
            'all_properties': [],
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

            # Create audit log entry
            node_name = new_props.get('name', '')
            create_audit_entry(
                action='create',
                node_label=label,
                node_id=node.element_id,
                node_name=node_name,
                user=request.user.username if request.user.is_authenticated else 'System',
                changes=f"Created with properties: {', '.join(new_props.keys())}"
            )

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

        # Use helper method to create relationship
        node_class = DynamicNode.get_or_create_label(label)
        success = node_class.connect_nodes(element_id, label, rel_type, target_id, target_label)
        if not success:
            raise ValueError("Failed to create relationship")

        # Get updated node and rebuild properties list with relationships
        node = node_class.get_by_element_id(element_id)
        if not node:
            raise ValueError("Source node not found")
        
        # Create audit log entry
        node_name = (node.custom_properties or {}).get('name', '')
        create_audit_entry(
            action='connect',
            node_label=label,
            node_id=element_id,
            node_name=node_name,
            user=request.user.username if request.user.is_authenticated else 'System',
            relationship_type=rel_type,
            target_label=target_label,
            target_id=target_id
        )
            
        out_rels = node.get_outgoing_relationships()
        in_rels = node.get_incoming_relationships()
        # Build properties list using helper function
        props_list = build_properties_list_with_relationships(node)

        return render(request, 'cmdb/partials/properties_section.html', {
            'properties_list': props_list,
            'element_id': element_id,
            'label': label,
            'success_message': f"Relationship '{rel_type}' created successfully"
        })
    except Exception as e:
        # Return error in the properties section
        return render(request, 'cmdb/partials/properties_section.html', {
            'properties_list': [],
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

        # Use helper method to delete relationship
        node_class = DynamicNode.get_or_create_label(label)
        deleted = node_class.disconnect_nodes(element_id, label, rel_type, target_id, target_label)
        if deleted == 0:
            raise ValueError("Relationship not found")

        # Get updated node and rebuild properties list with relationships
        node = node_class.get_by_element_id(element_id)
        if not node:
            raise ValueError("Source node not found")
        
        # Create audit log entry
        node_name = (node.custom_properties or {}).get('name', '')
        create_audit_entry(
            action='disconnect',
            node_label=label,
            node_id=element_id,
            node_name=node_name,
            user=request.user.username if request.user.is_authenticated else 'System',
            relationship_type=rel_type,
            target_label=target_label,
            target_id=target_id
        )
            
        out_rels = node.get_outgoing_relationships()
        in_rels = node.get_incoming_relationships()
        # Build properties list using helper function
        props_list = build_properties_list_with_relationships(node)

        return render(request, 'cmdb/partials/properties_section.html', {
            'properties_list': props_list,
            'element_id': element_id,
            'label': label,
            'success_message': f"Relationship '{rel_type}' removed successfully"
        })

    except Exception as e:
        # Return error in the properties section
        return render(request, 'cmdb/partials/properties_section.html', {
            'properties_list': [],
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

        sorted_nodes = sorted(nodes, key=lambda n: n.get_property('name', n.element_id))

        # Load the partial template manually as string
        template = Template(open('cmdb/templates/cmdb/partials/target_node_options.html').read())
        html = template.render(Context({
            'nodes': sorted_nodes,
            'target_label': target_label,
        }))

        return HttpResponse(html)

    except Exception as e:
        return HttpResponse(f'<option disabled>Error loading nodes for {target_label}: {str(e)}</option>')


@require_http_methods(["GET"])
def audit_log_list(request):
    """
    Global audit log view showing all audit log entries across all nodes.
    Supports HTMX partial updates
    """
    try:
        # Fetch all audit log entries
        audit_node_class = DynamicNode.get_or_create_label('AuditLogEntry')
        audit_nodes = audit_node_class.nodes.all()[:200]  # Limit to latest 200 entries
        
        # Extract and sort by timestamp
        audit_entries = []
        for node in audit_nodes:
            props = node.custom_properties or {}
            audit_entries.append({
                'element_id': node.element_id,
                'timestamp': props.get('timestamp', ''),
                'action': props.get('action', ''),
                'node_label': props.get('node_label', ''),
                'node_id': props.get('node_id', ''),
                'node_name': props.get('node_name', 'Unknown'),
                'user': props.get('user', 'System'),
                'changes': props.get('changes', ''),
                'relationship_type': props.get('relationship_type', ''),
                'target_label': props.get('target_label', ''),
                'target_id': props.get('target_id', '')
            })
        
        # Sort by timestamp descending (most recent first)
        audit_entries.sort(key=lambda x: x['timestamp'], reverse=True)
        
    except Exception as e:
        print(f"Error fetching audit log: {e}")
        audit_entries = []
    
    context = {
        'audit_entries': audit_entries,
        'all_labels': TypeRegistry.known_labels(),
    }
    
    # If HTMX request, return content + header for OOB swap
    if request.htmx:
        content_html = render_to_string('cmdb/partials/audit_log_content.html', context, request=request)
        header_html = render_to_string('cmdb/partials/audit_log_header.html', context, request=request)
        return HttpResponse(content_html + header_html)
    
    return render(request, 'cmdb/audit_log_list.html', context)
