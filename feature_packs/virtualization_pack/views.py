# feature_packs/virtualization_pack/views.py

from django.shortcuts import render
from neomodel import db
from cmdb.models import DynamicNode


def virtual_machine_details_tab(request, label, element_id):
    """
    Context builder for Virtual Machine Details tab.
    Shows host cluster (HOSTED_ON outgoing to Virtual_Cluster).
    Returns context dictionary rather than rendering template directly.
    """
    context = {
        'label': label,
        'element_id': element_id,
        'node': None,
        'custom_data': {
            'cluster': None
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
            context['error'] = f"Virtual Machine node not found: {element_id}"
            return context

        raw_node = result[0][0]
        node = node_class.inflate(raw_node)
        context['node'] = node

        # Fetch cluster (outgoing HOSTED_ON relationship)
        cluster_query = """
            MATCH (vm:Virtual_Machine) WHERE elementId(vm) = $eid
            MATCH (vm)-[:HOSTED_ON]->(cluster:Virtual_Cluster)
            WITH cluster, apoc.convert.fromJsonMap(cluster.custom_properties) AS cluster_props
            RETURN 
                elementId(cluster) AS cluster_id,
                labels(cluster)[0] AS cluster_label,
                COALESCE(cluster_props.name, 'Unnamed') AS name,
                COALESCE(cluster_props.type, 'Unknown') AS type,
                COALESCE(cluster_props.status, 'Unknown') AS status,
                COALESCE(cluster_props.description, '') AS description
        """
        cluster_result, _ = db.cypher_query(cluster_query, {'eid': element_id})
        if cluster_result:
            row = cluster_result[0]
            context['custom_data']['cluster'] = {
                'id': row[0],
                'label': row[1],
                'name': row[2],
                'type': row[3],
                'status': row[4],
                'description': row[5]
            }

    except Exception as e:
        context['error'] = str(e)

    return context


def virtual_host_details_tab(request, label, element_id):
    """
    Context builder for Virtual Host Details tab.
    Shows physical device (HOSTED_ON outgoing to Device).
    Note: Virtual_Machine nodes connect to Virtual_Cluster, not Virtual_Host,
    so VM hosting relationships are shown at the cluster level.
    Returns context dictionary rather than rendering template directly.
    """
    context = {
        'label': label,
        'element_id': element_id,
        'node': None,
        'custom_data': {
            'device': None
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
            context['error'] = f"Virtual Host node not found: {element_id}"
            return context

        raw_node = result[0][0]
        node = node_class.inflate(raw_node)
        context['node'] = node

        # Fetch physical device (outgoing HOSTED_ON relationship)
        device_query = """
            MATCH (host:Virtual_Host) WHERE elementId(host) = $eid
            MATCH (host)-[:HOSTED_ON]->(device:Device)
            WITH device, apoc.convert.fromJsonMap(device.custom_properties) AS device_props
            RETURN 
                elementId(device) AS device_id,
                labels(device)[0] AS device_label,
                COALESCE(device_props.name, 'Unnamed') AS name,
                COALESCE(device_props.type, 'Unknown') AS type,
                COALESCE(device_props.status, 'Unknown') AS status,
                COALESCE(device_props.location, '') AS location
        """
        device_result, _ = db.cypher_query(device_query, {'eid': element_id})
        if device_result:
            row = device_result[0]
            context['custom_data']['device'] = {
                'id': row[0],
                'label': row[1],
                'name': row[2],
                'type': row[3],
                'status': row[4],
                'location': row[5]
            }

    except Exception as e:
        context['error'] = str(e)

    return context


def virtual_cluster_details_tab(request, label, element_id):
    """
    Context builder for Virtual Cluster Details tab.
    Shows managed by person (MANAGED_BY outgoing),
    and virtual machines in cluster (HOSTED_ON incoming from Virtual_Machine).
    Returns context dictionary rather than rendering template directly.
    """
    context = {
        'label': label,
        'element_id': element_id,
        'node': None,
        'custom_data': {
            'manager': None,
            'virtual_machines': []
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
            context['error'] = f"Virtual Cluster node not found: {element_id}"
            return context

        raw_node = result[0][0]
        node = node_class.inflate(raw_node)
        context['node'] = node

        # Fetch manager (outgoing MANAGED_BY relationship)
        manager_query = """
            MATCH (cluster:Virtual_Cluster) WHERE elementId(cluster) = $eid
            MATCH (cluster)-[:MANAGED_BY]->(person:Person)
            WITH person, apoc.convert.fromJsonMap(person.custom_properties) AS person_props
            RETURN 
                elementId(person) AS person_id,
                labels(person)[0] AS person_label,
                COALESCE(person_props.name, 'Unnamed') AS name,
                COALESCE(person_props.email, '') AS email,
                COALESCE(person_props.role, '') AS role
        """
        manager_result, _ = db.cypher_query(manager_query, {'eid': element_id})
        if manager_result:
            row = manager_result[0]
            context['custom_data']['manager'] = {
                'id': row[0],
                'label': row[1],
                'name': row[2],
                'email': row[3],
                'role': row[4]
            }

        # Fetch virtual machines in this cluster (incoming HOSTED_ON from Virtual_Machine)
        vms_query = """
            MATCH (cluster:Virtual_Cluster) WHERE elementId(cluster) = $eid
            MATCH (vm:Virtual_Machine)-[:HOSTED_ON]->(cluster)
            WITH vm, apoc.convert.fromJsonMap(vm.custom_properties) AS vm_props
            RETURN 
                elementId(vm) AS vm_id,
                labels(vm)[0] AS vm_label,
                COALESCE(vm_props.name, 'Unnamed') AS name,
                COALESCE(vm_props.os, 'Unknown') AS os,
                COALESCE(vm_props.vcpus, 0) AS vcpus,
                COALESCE(vm_props.memory_mb, 0) AS memory_mb,
                COALESCE(vm_props.disk_gb, 0) AS disk_gb,
                COALESCE(vm_props.status, 'Unknown') AS status
            ORDER BY vm_props.name
        """
        vms_result, _ = db.cypher_query(vms_query, {'eid': element_id})
        for row in vms_result:
            context['custom_data']['virtual_machines'].append({
                'id': row[0],
                'label': row[1],
                'name': row[2],
                'os': row[3],
                'vcpus': row[4],
                'memory_mb': row[5],
                'disk_gb': row[6],
                'status': row[7]
            })

    except Exception as e:
        context['error'] = str(e)

    return context
