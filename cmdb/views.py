# cmdb/views.py
import importlib
import json
import os
import shutil

import pandas as pd
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse, JsonResponse
from django.middleware.csrf import get_token
from django.shortcuts import render, redirect
from django.template import Context, Template
from django.core.paginator import Paginator
from django.template.loader import render_to_string
from django.views.decorators.http import require_http_methods
from neomodel import db

from .models import DynamicNode
from .registry import TypeRegistry
from cmdb.audit_hooks import emit_audit
from cmdb.feature_pack_models import sync_feature_pack_to_db
from cmdb.feature_pack_views import (
    ensure_store_repo,
    get_feature_pack_store_dir,
    get_feature_packs_dir,
    load_pack_config_from_path,
    load_pack_types_from_path,
    normalize_dependencies,
    get_dependency_status,
)
from core.apps import reload_feature_packs
from users.views import has_node_permission, node_permission_required

# Constants for import functionality
RELATIONSHIP_SUFFIX = '_names'
CSV_ROW_OFFSET = 2  # Offset for error messages: 0-based index + header row

def parse_property_definition(prop_def):
    """
    Parse a property definition which can be either:
    - A string: "property_name"
    - A dict: {"name": "property_name", "choices": ["choice1", "choice2"]}
    
    Returns a dict with keys: name, choices (list or None)
    """
    if isinstance(prop_def, str):
        return {'name': prop_def, 'choices': None}
    elif isinstance(prop_def, dict):
        return {
            'name': prop_def.get('name', ''),
            'choices': prop_def.get('choices', None)
        }
    raise TypeError(f"Property definition must be a string or dict, got {type(prop_def).__name__}")


def is_staff_user(user):
    return user.is_staff


def install_feature_pack(pack_name: str) -> tuple[bool, str]:
    store_dir = get_feature_pack_store_dir()
    packs_dir = get_feature_packs_dir()
    source_path = os.path.join(store_dir, pack_name)
    dest_path = os.path.join(packs_dir, pack_name)

    if os.path.exists(dest_path):
        config_data = load_pack_config_from_path(dest_path, pack_name)
        types_data = load_pack_types_from_path(dest_path)
        sync_feature_pack_to_db(
            pack_name=pack_name,
            pack_path=dest_path,
            config=config_data,
            types_data=types_data,
        )
        reload_feature_packs()
        return True, f'Feature pack "{pack_name}" already installed.'

    if not os.path.exists(source_path):
        store_ready, store_message = ensure_store_repo()
        if not store_ready:
            return False, store_message
        if not os.path.exists(source_path):
            return False, f'Feature pack "{pack_name}" not found in store.'

    config_data = load_pack_config_from_path(source_path, pack_name)
    dependencies = normalize_dependencies(config_data)
    if dependencies:
        dependency_status = get_dependency_status()
        missing = [dep for dep in dependencies if dep not in dependency_status]
        disabled = [dep for dep in dependencies if dep in dependency_status and not dependency_status[dep]]
        if missing or disabled:
            detail_parts = []
            if missing:
                detail_parts.append(f'missing: {", ".join(missing)}')
            if disabled:
                detail_parts.append(f'disabled: {", ".join(disabled)}')
            details = "; ".join(detail_parts)
            return False, f'Cannot install "{pack_name}" until dependencies are installed and enabled ({details}).'

    try:
        shutil.copytree(source_path, dest_path)
        config_data = load_pack_config_from_path(dest_path, pack_name)
        types_data = load_pack_types_from_path(dest_path)
        sync_feature_pack_to_db(
            pack_name=pack_name,
            pack_path=dest_path,
            config=config_data,
            types_data=types_data,
        )
        reload_feature_packs()
    except Exception as exc:
        return False, f'Error adding feature pack "{pack_name}": {exc}'

    return True, f'Feature pack "{pack_name}" installed.'


def create_dynamic_node(label: str, properties: dict) -> DynamicNode:
    node_class = DynamicNode.get_or_create_label(label)
    return node_class(custom_properties=properties).save()


@require_http_methods(["GET", "POST"])
@login_required
@user_passes_test(is_staff_user)
def first_time_wizard(request):
    labels = set(TypeRegistry.known_labels())

    if request.method == "GET":
        context = {
            'has_org_pack': 'Organization' in labels,
            'has_data_center_pack': 'Rack' in labels or 'Row' in labels,
            'has_dns_pack': 'DNS_Zone' in labels,
            'has_ipam_pack': 'Network' in labels,
        }
        return render(request, 'cmdb/first_time_wizard.html', context)

    install_org = request.POST.get('install_org') == 'on'
    install_data_center = request.POST.get('install_data_center') == 'on'
    install_dns = request.POST.get('install_dns') == 'on'
    install_ipam = request.POST.get('install_ipam') == 'on'
    install_dhcp = request.POST.get('install_dhcp') == 'on'
    install_virtualization = request.POST.get('install_virtualization') == 'on'
    install_itsm = request.POST.get('install_itsm') == 'on'
    install_audit_log = request.POST.get('install_audit_log') == 'on'

    pack_order = []
    if install_org:
        pack_order.append('organization_pack')
    if install_data_center:
        pack_order.extend(['vendor_management_pack', 'inventory_pack', 'network_pack', 'data_center_pack'])
    if install_dns:
        pack_order.append('dns_pack')
    if install_ipam or install_dhcp:
        pack_order.append('ipam_pack')
    if install_dhcp:
        pack_order.append('dhcp_pack')
    if install_virtualization:
        pack_order.append('virtualization_pack')
    if install_itsm:
        pack_order.append('itsm_pack')
    if install_audit_log:
        pack_order.append('audit_log_pack')

    seen = set()
    pack_order = [pack for pack in pack_order if not (pack in seen or seen.add(pack))]

    installed_messages = []
    for pack_name in pack_order:
        success, message = install_feature_pack(pack_name)
        if success:
            installed_messages.append(message)
        else:
            messages.error(request, message)

    if installed_messages:
        messages.success(request, " ".join(installed_messages))

    labels = set(TypeRegistry.known_labels())

    created_nodes = []
    try:
        org_name = request.POST.get('org_name', '').strip()
        site_name = request.POST.get('site_name', '').strip()
        site_address = request.POST.get('site_address', '').strip()
        site_city = request.POST.get('site_city', '').strip()
        site_country = request.POST.get('site_country', '').strip()

        building_name = request.POST.get('building_name', '').strip()
        building_address = request.POST.get('building_address', '').strip() or site_address
        floor_number = request.POST.get('floor_number', '').strip()

        data_center_room = request.POST.get('dc_room', '').strip()
        rack_row_name = request.POST.get('rack_row', '').strip()
        rack_count = request.POST.get('rack_count', '').strip()

        dns_zone = request.POST.get('dns_zone', '').strip()
        ip_cidr = request.POST.get('ip_cidr', '').strip()
        dhcp_scope_name = request.POST.get('dhcp_scope_name', '').strip()
        dhcp_range_start = request.POST.get('dhcp_range_start', '').strip()
        dhcp_range_end = request.POST.get('dhcp_range_end', '').strip()
        dhcp_gateway = request.POST.get('dhcp_gateway', '').strip()
        dhcp_dns_server = request.POST.get('dhcp_dns_server', '').strip()

        virtual_cluster_name = request.POST.get('virtual_cluster_name', '').strip()
        virtual_host_count = request.POST.get('virtual_host_count', '').strip()

        org_node = None
        site_node = None
        building_node = None
        floor_node = None
        room_node = None
        row_node = None

        if org_name and 'Organization' in labels:
            org_node = create_dynamic_node('Organization', {'name': org_name})
            created_nodes.append('Organization')

        if site_name and 'Site' in labels:
            site_props = {
                'name': site_name,
                'address': site_address,
                'city': site_city,
                'country': site_country,
            }
            site_node = create_dynamic_node('Site', site_props)
            created_nodes.append('Site')

        if org_node and site_node:
            DynamicNode.connect_nodes(org_node.element_id, 'Organization', 'LOCATED_AT', site_node.element_id, 'Site')

        if building_name and 'Building' in labels:
            building_props = {
                'name': building_name,
                'address': building_address,
            }
            building_node = create_dynamic_node('Building', building_props)
            created_nodes.append('Building')

        if building_node and site_node:
            DynamicNode.connect_nodes(building_node.element_id, 'Building', 'LOCATED_IN', site_node.element_id, 'Site')

        if floor_number and 'Floor' in labels:
            floor_node = create_dynamic_node('Floor', {'floor_number': floor_number})
            created_nodes.append('Floor')

        if floor_node and building_node:
            DynamicNode.connect_nodes(floor_node.element_id, 'Floor', 'LOCATED_IN', building_node.element_id, 'Building')

        if data_center_room and 'Room' in labels:
            room_node = create_dynamic_node('Room', {'name': data_center_room, 'orientation': 'front'})
            created_nodes.append('Room')

        if room_node and floor_node:
            DynamicNode.connect_nodes(room_node.element_id, 'Room', 'LOCATED_IN', floor_node.element_id, 'Floor')

        if rack_row_name and 'Row' in labels:
            row_node = create_dynamic_node('Row', {
                'name': rack_row_name,
                'orientation': 'front',
                'row_number': rack_row_name,
            })
            created_nodes.append('Row')

        if row_node and room_node:
            DynamicNode.connect_nodes(row_node.element_id, 'Row', 'LOCATED_IN', room_node.element_id, 'Room')

        if rack_count.isdigit() and int(rack_count) > 0 and 'Rack' in labels:
            for rack_index in range(1, int(rack_count) + 1):
                rack_props = {
                    'name': f"Rack {rack_index}",
                    'height': 42,
                    'rack_number': rack_index,
                }
                rack_node = create_dynamic_node('Rack', rack_props)
                created_nodes.append('Rack')
                if row_node:
                    DynamicNode.connect_nodes(rack_node.element_id, 'Rack', 'LOCATED_IN', row_node.element_id, 'Row')

        if dns_zone and 'DNS_Zone' in labels:
            create_dynamic_node('DNS_Zone', {'name': dns_zone})
            created_nodes.append('DNS_Zone')

        network_node = None
        if ip_cidr and 'Network' in labels:
            network_node = create_dynamic_node('Network', {'name': ip_cidr, 'cidr': ip_cidr})
            created_nodes.append('Network')

        if dhcp_scope_name and dhcp_range_start and dhcp_range_end and 'DHCP_Scope' in labels:
            dhcp_props = {
                'name': dhcp_scope_name,
                'range_start': dhcp_range_start,
                'range_end': dhcp_range_end,
            }
            if dhcp_gateway:
                dhcp_props['gateway'] = dhcp_gateway
            if dhcp_dns_server:
                dhcp_props['dns_server'] = dhcp_dns_server
            dhcp_node = create_dynamic_node('DHCP_Scope', dhcp_props)
            created_nodes.append('DHCP_Scope')
            if network_node:
                DynamicNode.connect_nodes(dhcp_node.element_id, 'DHCP_Scope', 'PART_OF', network_node.element_id, 'Network')

        cluster_node = None
        if virtual_cluster_name and 'Virtual_Cluster' in labels:
            cluster_node = create_dynamic_node('Virtual_Cluster', {'name': virtual_cluster_name})
            created_nodes.append('Virtual_Cluster')

        if virtual_host_count.isdigit() and int(virtual_host_count) > 0 and 'Virtual_Host' in labels:
            for host_index in range(1, int(virtual_host_count) + 1):
                host_props = {'name': f"Host {host_index}"}
                host_node = create_dynamic_node('Virtual_Host', host_props)
                created_nodes.append('Virtual_Host')
                if cluster_node:
                    DynamicNode.connect_nodes(host_node.element_id, 'Virtual_Host', 'PART_OF', cluster_node.element_id, 'Virtual_Cluster')


        if created_nodes:
            messages.success(request, f"Created: {', '.join(sorted(set(created_nodes)))}")
        else:
            messages.info(request, 'No initial objects were created. Adjust selections and try again.')
    except Exception as exc:
        messages.error(request, f'Wizard setup failed: {exc}')

    return redirect('cmdb:first_time_wizard')

def get_feature_pack_modal_override(label, modal_type):
    for modal in getattr(settings, 'FEATURE_PACK_MODALS', []):
        if modal.get('type') != modal_type:
            continue
        for_labels = modal.get('for_labels', []) or []
        if not for_labels or label in for_labels:
            return modal
    return None

def get_property_names(property_defs):
    names = []
    for prop_def in property_defs:
        parsed_prop = parse_property_definition(prop_def)
        if parsed_prop['name']:
            names.append(parsed_prop['name'])
    return names

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

def dashboard(request):
    labels = TypeRegistry.known_labels()
    counts = {}
    for label in labels:
        try:
            # Use Neomodel's count method instead of raw Cypher
            node_class = DynamicNode.get_or_create_label(label)
            count = len(node_class.nodes)
            counts[label] = count
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

@login_required
@node_permission_required('view')
def nodes_list(request, label):
    """
    List view for nodes of a specific label
    Supports HTMX partial updates
    """
    try:
        node_class = DynamicNode.get_or_create_label(label)
        nodes_queryset = node_class.nodes.all()
    except Exception as e:
        print(f"Error fetching {label}: {e}")
        nodes_queryset = []

    page_number = request.GET.get('page', 1)

    # Persist per_page in session
    if 'per_page' in request.GET:
        try:
            page_size = int(request.GET['per_page'])
        except (TypeError, ValueError):
            page_size = request.session.get('per_page', 50)
        page_size = max(1, min(page_size, 200))
        request.session['per_page'] = page_size
    else:
        page_size = request.session.get('per_page', 50)
        page_size = max(1, min(page_size, 200))

    paginator = Paginator(list(nodes_queryset), page_size)
    page_obj = paginator.get_page(page_number)
    nodes = page_obj.object_list
    
    # Get column configuration from type registry
    metadata = TypeRegistry.get_metadata(label)
    default_columns = get_property_names(metadata.get('columns', []))
    all_properties = get_property_names(metadata.get('properties', []))
    
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
        'page_obj': page_obj,
        'paginator': paginator,
        'page_size': page_size,
        'per_page_options': [10, 25, 50, 100, 200],
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
    
@login_required
@node_permission_required('view')
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
@login_required
@node_permission_required('change')
def node_edit(request, label, element_id):
    
    try:
        node_class = DynamicNode.get_or_create_label(label)
        # Use helper method instead of raw Cypher
        node = node_class.get_by_element_id(element_id)
        if not node:
            raise node_class.DoesNotExist

    except node_class.DoesNotExist:
        return JsonResponse({'error': 'Node not found'}, status=404)

    modal_override = get_feature_pack_modal_override(label, 'edit')
    if modal_override and modal_override.get('custom_view'):
        pack_view = importlib.import_module(modal_override['custom_view'].rsplit('.', 1)[0])
        custom_view_func = getattr(pack_view, modal_override['custom_view'].rsplit('.', 1)[1])
        return custom_view_func(request, label, element_id)

    template_name = 'cmdb/partials/node_edit_form.html'
    if modal_override and modal_override.get('template'):
        template_name = modal_override['template']

    context = {
        'label': label,
        'element_id': element_id,
        'csrf_token': get_token(request),
        'node': node,
        'relationships': TypeRegistry.get_metadata(label).get('relationships', {}),
        'all_labels': TypeRegistry.known_labels(),
    }

    if request.method == 'GET':
        current_props = node.custom_properties or {}
        
        # Get metadata to check for property definitions with choices
        meta = TypeRegistry.get_metadata(label)
        props_metadata = meta.get('properties', [])
        
        # Build a map of property names to their definitions
        prop_choices_map = {}
        for prop_def in props_metadata:
            parsed_prop = parse_property_definition(prop_def)
            if parsed_prop['choices']:
                prop_choices_map[parsed_prop['name']] = parsed_prop['choices']
        
        # Build list of form fields
        form_fields = []
        for key, value in current_props.items():
            field_type = 'text'
            choices = None
            
            # Check if this property has predefined choices
            if key in prop_choices_map:
                field_type = 'select'
                choices = prop_choices_map[key]
            elif isinstance(value, bool):
                field_type = 'checkbox'
            elif isinstance(value, (int, float)):
                field_type = 'number'
            elif isinstance(value, list):
                field_type = 'textarea'  # comma-separated
            
            field_data = {
                'key': key,
                'value': value,
                'type': field_type,
                'input_name': f'prop_{key}',  # for POST collection
            }
            
            if choices:
                field_data['choices'] = choices
            
            form_fields.append(field_data)

        context['form_fields'] = form_fields
        context['current_json'] = json.dumps(current_props, indent=2)  # fallback raw
        context['original_json'] = json.dumps(current_props)

        return render(request, template_name, context)

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
        changes_detail = {
            key: {
                'old': old_props.get(key),
                'new': current.get(key)
            }
            for key in set(old_props.keys()) | set(current.keys())
            if old_props.get(key) != current.get(key)
        }
        emit_audit(
            action='update',
            node_label=label,
            node_id=element_id,
            node_name=node_name,
            user=request.user.username if request.user.is_authenticated else 'System',
            changes=json.dumps(changes_detail, sort_keys=True, indent=2) if changes_detail else "Properties updated",
            old_props=old_props,
            new_props=current
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
        return render(request, template_name, context)
    
    
@require_http_methods(["POST"])
@login_required
@node_permission_required('delete')
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
        emit_audit(
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
@login_required
@node_permission_required('add')
def node_create(request, label):
    try:
        meta = TypeRegistry.get_metadata(label)
        if not meta:
            raise ValueError(f"No metadata for label '{label}'")

        modal_override = get_feature_pack_modal_override(label, 'create')
        if modal_override and modal_override.get('custom_view'):
            pack_view = importlib.import_module(modal_override['custom_view'].rsplit('.', 1)[0])
            custom_view_func = getattr(pack_view, modal_override['custom_view'].rsplit('.', 1)[1])
            return custom_view_func(request, label)

        template_name = 'cmdb/partials/node_create_form.html'
        if modal_override and modal_override.get('template'):
            template_name = modal_override['template']

        required_props = meta.get('required_properties', [])
        optional_props = meta.get('optional_properties', [])

        context = {
            'label': label,
            'csrf_token': get_token(request),
            'required_props': required_props,
            'optional_props': optional_props,
            'all_props': required_props + optional_props,
        }

        # Build dynamic fields from registry
        required_props = meta.get('required', [])
        props = meta.get('properties', [])

        form_fields = []
        for prop_def in props:
            parsed_prop = parse_property_definition(prop_def)
            prop_name = parsed_prop['name']
            choices = parsed_prop['choices']

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

        if request.method == 'GET':
            context = {
                'label': label,
                'csrf_token': get_token(request),
                'form_fields': form_fields,
                'relationships': meta.get('relationships', {}),
                'all_labels': TypeRegistry.known_labels(),
            }
            return render(request, template_name, context)

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
                    return render(request, template_name, {
                        'label': label,
                        'error': f'Invalid raw JSON: {str(e)}',
                        'form_fields': form_fields,
                        'relationships': meta.get('relationships', {}),
                        'all_labels': TypeRegistry.known_labels(),
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
                return render(request, template_name, {
                    'label': label,
                    'error': f"Missing required properties: {', '.join(missing)}",
                    'form_fields': form_fields,
                    'relationships': meta.get('relationships', {}),
                    'all_labels': TypeRegistry.known_labels(),
                })
            
            # Save as dict (not string)
            node_class = DynamicNode.get_or_create_label(label)
            node = node_class(custom_properties=new_props).save()  

            # Create audit log entry
            node_name = new_props.get('name', '')
            emit_audit(
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
            return render(request, template_name, {
                'label': label,
                'error': str(e),
                'form_fields': form_fields,
                'relationships': meta.get('relationships', {}),
                'all_labels': TypeRegistry.known_labels(),
            })
            
            
    except Exception as e:
        context['error'] = str(e)
        return render(request, template_name, context)

@require_http_methods(["POST"])
@login_required
@node_permission_required('change')
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
        emit_audit(
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
@login_required
@node_permission_required('change')
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
        emit_audit(
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
    query = request.GET.get('q', '').strip().lower()
    selected_id = request.GET.get('selected_id', '').strip()
    select_id = request.GET.get('select_id', 'target_id').strip() or 'target_id'
    select_name = request.GET.get('select_name', 'target_id').strip() or 'target_id'
    placeholder = request.GET.get('placeholder', 'Select target node').strip() or 'Select target node'
    required = request.GET.get('required', 'true').lower() != 'false'
    if not target_label:
        return HttpResponse('<option disabled>No label selected</option>')

    try:
        node_class = DynamicNode.get_or_create_label(target_label)
        nodes = node_class.nodes.all()[:200]

        def node_display(node):
            props = node.custom_properties or {}
            if target_label == 'IP_Address' and props.get('address'):
                return str(props.get('address'))
            return str(props.get('name') or props.get('primary_ns') or node.element_id)

        if query:
            nodes = [n for n in nodes if query in node_display(n).lower()]

        sorted_nodes = sorted(nodes, key=node_display)

        # Load the partial template manually as string
        template = Template(open('cmdb/templates/cmdb/partials/target_node_options.html').read())
        html = template.render(Context({
            'nodes': sorted_nodes,
            'target_label': target_label,
            'select_id': select_id,
            'select_name': select_name,
            'placeholder': placeholder,
            'required': required,
            'selected_id': selected_id,
        }))

        return HttpResponse(html)

    except Exception as e:
        return HttpResponse(f'<option disabled>Error loading nodes for {target_label}: {str(e)}</option>')



@require_http_methods(["GET", "POST"])
@login_required
@node_permission_required('add')
def node_import(request, label):
    """
    Handle bulk node import from CSV/XLS files
    GET: Display import form and download template
    POST: Process uploaded file and create nodes
    """
    try:
        meta = TypeRegistry.get_metadata(label)
        if not meta:
            raise ValueError(f"No metadata for label '{label}'")
        
        # Get properties and relationships from metadata
        properties = meta.get('properties', [])
        required_props = meta.get('required', [])
        relationships = meta.get('relationships', {})
        
        context = {
            'label': label,
            'csrf_token': get_token(request),
            'properties': properties,
            'required_props': required_props,
            'relationships': relationships,
            'all_labels': TypeRegistry.known_labels(),
        }
        
        if request.method == 'GET':
            # Check if downloading template
            if request.GET.get('download_template') == 'true':
                # Create template CSV with headers
                headers = properties.copy()
                # Add relationship columns
                for rel_type, rel_info in relationships.items():
                    headers.append(f"{rel_type}{RELATIONSHIP_SUFFIX}")
                
                # Create DataFrame with headers only
                df = pd.DataFrame(columns=headers)
                
                # Return as CSV download
                response = HttpResponse(content_type='text/csv')
                response['Content-Disposition'] = f'attachment; filename="{label}_import_template.csv"'
                df.to_csv(response, index=False)
                return response
            
            # Otherwise show the import form
            return render(request, 'cmdb/node_import.html', context)
        
        # POST: Process file upload
        if 'import_file' not in request.FILES:
            context['error'] = 'No file uploaded'
            return render(request, 'cmdb/node_import.html', context)
        
        uploaded_file = request.FILES['import_file']
        file_ext = uploaded_file.name.split('.')[-1].lower()
        
        # Read file into DataFrame
        try:
            if file_ext == 'csv':
                df = pd.read_csv(uploaded_file)
            elif file_ext in ['xls', 'xlsx']:
                df = pd.read_excel(uploaded_file)
            else:
                context['error'] = 'Unsupported file format. Please upload CSV or Excel file.'
                return render(request, 'cmdb/node_import.html', context)
        except Exception as e:
            context['error'] = f'Error reading file: {str(e)}'
            return render(request, 'cmdb/node_import.html', context)
        
        # Process each row
        node_class = DynamicNode.get_or_create_label(label)
        created_nodes = []
        errors = []
        relationship_queue = []  # Store relationships to create after all nodes
        
        for idx, row in df.iterrows():
            try:
                # Build properties dict from row
                node_props = {}
                row_relationships = {}
                
                for col in df.columns:
                    value = row[col]
                    
                    # Skip NaN values
                    if pd.isna(value):
                        continue
                    
                    # Check if this is a relationship column
                    if col.endswith(RELATIONSHIP_SUFFIX):
                        rel_type = col[:-len(RELATIONSHIP_SUFFIX)]  # Remove suffix
                        # Relationship types in metadata are uppercase (e.g., BELONGS_TO)
                        # Check if this matches a known relationship (case-insensitive)
                        rel_type_upper = rel_type.upper()
                        if rel_type_upper in relationships:
                            # Store with uppercase key for consistency
                            row_relationships[rel_type_upper] = str(value)
                        continue
                    
                    # Regular property
                    if col in properties:
                        # Type coercion
                        if isinstance(value, (int, float, bool)):
                            node_props[col] = value
                        else:
                            node_props[col] = str(value)
                
                # Validate required properties
                missing = [r for r in required_props if r not in node_props or not node_props[r]]
                if missing:
                    errors.append(f"Row {idx + CSV_ROW_OFFSET}: Missing required properties: {', '.join(missing)}")
                    continue
                
                # Create node
                node = node_class(custom_properties=node_props).save()
                created_nodes.append(node)
                
                # Queue relationships for creation
                if row_relationships:
                    relationship_queue.append({
                        'node': node,
                        'relationships': row_relationships
                    })
                
                # Create audit log entry
                node_name = node_props.get('name', '')
                emit_audit(
                    action='create',
                    node_label=label,
                    node_id=node.element_id,
                    node_name=node_name,
                    user=request.user.username if request.user.is_authenticated else 'System',
                    changes=f"Imported from file with properties: {', '.join(node_props.keys())}"
                )
                
            except Exception as e:
                errors.append(f"Row {idx + CSV_ROW_OFFSET}: {str(e)}")
        
        # Process queued relationships
        for item in relationship_queue:
            node = item['node']
            node_name = (node.custom_properties or {}).get('name', node.element_id)
            
            for rel_type, target_names in item['relationships'].items():
                # Split multiple target names by comma
                target_name_list = [name.strip() for name in target_names.split(',')]
                
                # Get target label from relationships metadata
                rel_info = relationships.get(rel_type, {})
                target_label = rel_info.get('target')  # Field is 'target' not 'target_label'
                
                if not target_label:
                    errors.append(f"Node '{node_name}': Unknown relationship type '{rel_type}'")
                    continue
                
                # Validate target_label to prevent injection
                # Target labels come from metadata but validate for safety
                if not target_label or not target_label.replace('_', '').isalnum():
                    errors.append(f"Node '{node_name}': Invalid target label '{target_label}' for relationship '{rel_type}'")
                    continue
                
                # Find target nodes by name
                target_class = DynamicNode.get_or_create_label(target_label)
                
                for target_name in target_name_list:
                    # Query for target node by name property
                    query = f"""
                        MATCH (n:`{target_label}`)
                        WHERE n.custom_properties IS NOT NULL
                        AND apoc.convert.fromJsonMap(n.custom_properties).name = $name
                        RETURN elementId(n) AS eid
                        LIMIT 1
                    """
                    result, _ = db.cypher_query(query, {'name': target_name})
                    
                    if not result:
                        errors.append(f"Node '{node_name}': Target node '{target_name}' of type '{target_label}' not found for relationship '{rel_type}'")
                        continue
                    
                    target_id = result[0][0]
                    
                    # Create relationship
                    try:
                        node_class.connect_nodes(
                            node.element_id, label,
                            rel_type,  # Already uppercase from storage
                            target_id, target_label
                        )
                    except Exception as e:
                        errors.append(f"Node '{node_name}': Failed to create relationship '{rel_type}' to '{target_name}': {str(e)}")
        
        # Prepare success/error summary
        context['success'] = True
        context['created_count'] = len(created_nodes)
        context['error_count'] = len(errors)
        context['errors'] = errors
        
        return render(request, 'cmdb/node_import.html', context)
        
    except Exception as e:
        context = {
            'label': label,
            'csrf_token': get_token(request),
            'error': f'Unexpected error: {str(e)}',
            'all_labels': TypeRegistry.known_labels(),
        }
        return render(request, 'cmdb/node_import.html', context)
