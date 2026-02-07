# feature_packs/itsm_pack/views.py

from django.shortcuts import render
from neomodel import db
from cmdb.models import DynamicNode


def issue_details_tab(request, label, element_id):
    """
    Custom view for Issue Details tab.
    Shows related problems, changes, events, and impacted devices.
    """
    context = {
        'label': label,
        'element_id': element_id,
        'node': None,
        'custom_data': {
            'problems': [],
            'changes': [],
            'events': [],
            'impacted_devices': []
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
            context['error'] = f"Issue node not found: {element_id}"
            return context

        raw_node = result[0][0]
        node = node_class.inflate(raw_node)
        context['node'] = node

        # Fetch related problems (CAUSED_BY relationship)
        problems_query = """
            MATCH (issue:Issue) WHERE elementId(issue) = $eid
            MATCH (issue)-[:CAUSED_BY]->(problem:Problem)
            WITH problem, apoc.convert.fromJsonMap(problem.custom_properties) AS props
            RETURN 
                elementId(problem) AS id,
                labels(problem)[0] AS label,
                COALESCE(props.name, 'Unnamed') AS name,
                COALESCE(props.status, 'Unknown') AS status,
                COALESCE(props.priority, 'Unknown') AS priority
        """
        problems_result, _ = db.cypher_query(problems_query, {'eid': element_id})
        for row in problems_result:
            context['custom_data']['problems'].append({
                'id': row[0],
                'label': row[1],
                'name': row[2],
                'status': row[3],
                'priority': row[4]
            })

        # Fetch related changes (RESOLVED_BY relationship)
        changes_query = """
            MATCH (issue:Issue) WHERE elementId(issue) = $eid
            MATCH (issue)-[:RESOLVED_BY]->(change:Change)
            WITH change, apoc.convert.fromJsonMap(change.custom_properties) AS props
            RETURN 
                elementId(change) AS id,
                labels(change)[0] AS label,
                COALESCE(props.name, 'Unnamed') AS name,
                COALESCE(props.status, 'Unknown') AS status,
                COALESCE(props.change_type, 'Unknown') AS change_type
        """
        changes_result, _ = db.cypher_query(changes_query, {'eid': element_id})
        for row in changes_result:
            context['custom_data']['changes'].append({
                'id': row[0],
                'label': row[1],
                'name': row[2],
                'status': row[3],
                'change_type': row[4]
            })

        # Fetch related events (TRIGGERED_BY relationship)
        events_query = """
            MATCH (issue:Issue) WHERE elementId(issue) = $eid
            MATCH (issue)-[:TRIGGERED_BY]->(event:Event)
            WITH event, apoc.convert.fromJsonMap(event.custom_properties) AS props
            RETURN 
                elementId(event) AS id,
                labels(event)[0] AS label,
                COALESCE(props.name, 'Unnamed') AS name,
                COALESCE(props.severity, 'Unknown') AS severity,
                COALESCE(props.timestamp, 'Unknown') AS timestamp
        """
        events_result, _ = db.cypher_query(events_query, {'eid': element_id})
        for row in events_result:
            context['custom_data']['events'].append({
                'id': row[0],
                'label': row[1],
                'name': row[2],
                'severity': row[3],
                'timestamp': row[4]
            })

        # Fetch impacted devices (IMPACTS relationship)
        devices_query = """
            MATCH (issue:Issue) WHERE elementId(issue) = $eid
            MATCH (issue)-[:IMPACTS]->(device:Device)
            WITH device, apoc.convert.fromJsonMap(device.custom_properties) AS props
            RETURN 
                elementId(device) AS id,
                labels(device)[0] AS label,
                COALESCE(props.name, 'Unnamed') AS name
        """
        devices_result, _ = db.cypher_query(devices_query, {'eid': element_id})
        for row in devices_result:
            context['custom_data']['impacted_devices'].append({
                'id': row[0],
                'label': row[1],
                'name': row[2]
            })

    except Exception as e:
        context['error'] = str(e)

    return context


def problem_details_tab(request, label, element_id):
    """
    Custom view for Problem Details tab.
    Shows related issues, changes, root causes, and affected devices.
    """
    context = {
        'label': label,
        'element_id': element_id,
        'node': None,
        'custom_data': {
            'issues': [],
            'changes': [],
            'related_problems': [],
            'affected_devices': []
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
            context['error'] = f"Problem node not found: {element_id}"
            return context

        raw_node = result[0][0]
        node = node_class.inflate(raw_node)
        context['node'] = node

        # Fetch related issues (CAUSES relationship)
        issues_query = """
            MATCH (problem:Problem) WHERE elementId(problem) = $eid
            MATCH (problem)-[:CAUSES]->(issue:Issue)
            WITH issue, apoc.convert.fromJsonMap(issue.custom_properties) AS props
            RETURN 
                elementId(issue) AS id,
                labels(issue)[0] AS label,
                COALESCE(props.name, 'Unnamed') AS name,
                COALESCE(props.status, 'Unknown') AS status,
                COALESCE(props.priority, 'Unknown') AS priority
        """
        issues_result, _ = db.cypher_query(issues_query, {'eid': element_id})
        for row in issues_result:
            context['custom_data']['issues'].append({
                'id': row[0],
                'label': row[1],
                'name': row[2],
                'status': row[3],
                'priority': row[4]
            })

        # Fetch related changes (RESOLVED_BY relationship)
        changes_query = """
            MATCH (problem:Problem) WHERE elementId(problem) = $eid
            MATCH (problem)-[:RESOLVED_BY]->(change:Change)
            WITH change, apoc.convert.fromJsonMap(change.custom_properties) AS props
            RETURN 
                elementId(change) AS id,
                labels(change)[0] AS label,
                COALESCE(props.name, 'Unnamed') AS name,
                COALESCE(props.status, 'Unknown') AS status,
                COALESCE(props.change_type, 'Unknown') AS change_type
        """
        changes_result, _ = db.cypher_query(changes_query, {'eid': element_id})
        for row in changes_result:
            context['custom_data']['changes'].append({
                'id': row[0],
                'label': row[1],
                'name': row[2],
                'status': row[3],
                'change_type': row[4]
            })

        # Fetch related problems (RELATED_TO relationship)
        related_problems_query = """
            MATCH (problem:Problem) WHERE elementId(problem) = $eid
            MATCH (problem)-[:RELATED_TO]->(related:Problem)
            WITH related, apoc.convert.fromJsonMap(related.custom_properties) AS props
            RETURN 
                elementId(related) AS id,
                labels(related)[0] AS label,
                COALESCE(props.name, 'Unnamed') AS name,
                COALESCE(props.status, 'Unknown') AS status
        """
        related_result, _ = db.cypher_query(related_problems_query, {'eid': element_id})
        for row in related_result:
            context['custom_data']['related_problems'].append({
                'id': row[0],
                'label': row[1],
                'name': row[2],
                'status': row[3]
            })

        # Fetch affected devices (AFFECTS relationship)
        devices_query = """
            MATCH (problem:Problem) WHERE elementId(problem) = $eid
            MATCH (problem)-[:AFFECTS]->(device:Device)
            WITH device, apoc.convert.fromJsonMap(device.custom_properties) AS props
            RETURN 
                elementId(device) AS id,
                labels(device)[0] AS label,
                COALESCE(props.name, 'Unnamed') AS name
        """
        devices_result, _ = db.cypher_query(devices_query, {'eid': element_id})
        for row in devices_result:
            context['custom_data']['affected_devices'].append({
                'id': row[0],
                'label': row[1],
                'name': row[2]
            })

    except Exception as e:
        context['error'] = str(e)

    return context


def change_details_tab(request, label, element_id):
    """
    Custom view for Change Details tab.
    Shows related issues, problems, releases, and impacted devices.
    """
    context = {
        'label': label,
        'element_id': element_id,
        'node': None,
        'custom_data': {
            'issues': [],
            'problems': [],
            'releases': [],
            'impacted_devices': []
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
            context['error'] = f"Change node not found: {element_id}"
            return context

        raw_node = result[0][0]
        node = node_class.inflate(raw_node)
        context['node'] = node

        # Fetch related issues (RESOLVES relationship)
        issues_query = """
            MATCH (change:Change) WHERE elementId(change) = $eid
            MATCH (change)-[:RESOLVES]->(issue:Issue)
            WITH issue, apoc.convert.fromJsonMap(issue.custom_properties) AS props
            RETURN 
                elementId(issue) AS id,
                labels(issue)[0] AS label,
                COALESCE(props.name, 'Unnamed') AS name,
                COALESCE(props.status, 'Unknown') AS status,
                COALESCE(props.priority, 'Unknown') AS priority
        """
        issues_result, _ = db.cypher_query(issues_query, {'eid': element_id})
        for row in issues_result:
            context['custom_data']['issues'].append({
                'id': row[0],
                'label': row[1],
                'name': row[2],
                'status': row[3],
                'priority': row[4]
            })

        # Fetch related problems (FIXES relationship)
        problems_query = """
            MATCH (change:Change) WHERE elementId(change) = $eid
            MATCH (change)-[:FIXES]->(problem:Problem)
            WITH problem, apoc.convert.fromJsonMap(problem.custom_properties) AS props
            RETURN 
                elementId(problem) AS id,
                labels(problem)[0] AS label,
                COALESCE(props.name, 'Unnamed') AS name,
                COALESCE(props.status, 'Unknown') AS status,
                COALESCE(props.priority, 'Unknown') AS priority
        """
        problems_result, _ = db.cypher_query(problems_query, {'eid': element_id})
        for row in problems_result:
            context['custom_data']['problems'].append({
                'id': row[0],
                'label': row[1],
                'name': row[2],
                'status': row[3],
                'priority': row[4]
            })

        # Fetch related releases (PART_OF relationship)
        releases_query = """
            MATCH (change:Change) WHERE elementId(change) = $eid
            MATCH (change)-[:PART_OF]->(release:Release)
            WITH release, apoc.convert.fromJsonMap(release.custom_properties) AS props
            RETURN 
                elementId(release) AS id,
                labels(release)[0] AS label,
                COALESCE(props.name, 'Unnamed') AS name,
                COALESCE(props.version, 'Unknown') AS version,
                COALESCE(props.status, 'Unknown') AS status
        """
        releases_result, _ = db.cypher_query(releases_query, {'eid': element_id})
        for row in releases_result:
            context['custom_data']['releases'].append({
                'id': row[0],
                'label': row[1],
                'name': row[2],
                'version': row[3],
                'status': row[4]
            })

        # Fetch impacted devices (IMPACTS relationship)
        devices_query = """
            MATCH (change:Change) WHERE elementId(change) = $eid
            MATCH (change)-[:IMPACTS]->(device:Device)
            WITH device, apoc.convert.fromJsonMap(device.custom_properties) AS props
            RETURN 
                elementId(device) AS id,
                labels(device)[0] AS label,
                COALESCE(props.name, 'Unnamed') AS name
        """
        devices_result, _ = db.cypher_query(devices_query, {'eid': element_id})
        for row in devices_result:
            context['custom_data']['impacted_devices'].append({
                'id': row[0],
                'label': row[1],
                'name': row[2]
            })

    except Exception as e:
        context['error'] = str(e)

    return context


def release_details_tab(request, label, element_id):
    """
    Custom view for Release Details tab.
    Shows related changes, deployed devices, and superseded releases.
    """
    context = {
        'label': label,
        'element_id': element_id,
        'node': None,
        'custom_data': {
            'changes': [],
            'deployed_devices': [],
            'superseded_by': [],
            'supersedes': []
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
            context['error'] = f"Release node not found: {element_id}"
            return context

        raw_node = result[0][0]
        node = node_class.inflate(raw_node)
        context['node'] = node

        # Fetch related changes (CONTAINS relationship)
        changes_query = """
            MATCH (release:Release) WHERE elementId(release) = $eid
            MATCH (release)-[:CONTAINS]->(change:Change)
            WITH change, apoc.convert.fromJsonMap(change.custom_properties) AS props
            RETURN 
                elementId(change) AS id,
                labels(change)[0] AS label,
                COALESCE(props.name, 'Unnamed') AS name,
                COALESCE(props.status, 'Unknown') AS status,
                COALESCE(props.change_type, 'Unknown') AS change_type
        """
        changes_result, _ = db.cypher_query(changes_query, {'eid': element_id})
        for row in changes_result:
            context['custom_data']['changes'].append({
                'id': row[0],
                'label': row[1],
                'name': row[2],
                'status': row[3],
                'change_type': row[4]
            })

        # Fetch deployed devices (DEPLOYS_TO relationship)
        devices_query = """
            MATCH (release:Release) WHERE elementId(release) = $eid
            MATCH (release)-[:DEPLOYS_TO]->(device:Device)
            WITH device, apoc.convert.fromJsonMap(device.custom_properties) AS props
            RETURN 
                elementId(device) AS id,
                labels(device)[0] AS label,
                COALESCE(props.name, 'Unnamed') AS name
        """
        devices_result, _ = db.cypher_query(devices_query, {'eid': element_id})
        for row in devices_result:
            context['custom_data']['deployed_devices'].append({
                'id': row[0],
                'label': row[1],
                'name': row[2]
            })

        # Fetch superseded releases (SUPERSEDES relationship - outgoing)
        supersedes_query = """
            MATCH (release:Release) WHERE elementId(release) = $eid
            MATCH (release)-[:SUPERSEDES]->(old_release:Release)
            WITH old_release, apoc.convert.fromJsonMap(old_release.custom_properties) AS props
            RETURN 
                elementId(old_release) AS id,
                labels(old_release)[0] AS label,
                COALESCE(props.name, 'Unnamed') AS name,
                COALESCE(props.version, 'Unknown') AS version
        """
        supersedes_result, _ = db.cypher_query(supersedes_query, {'eid': element_id})
        for row in supersedes_result:
            context['custom_data']['supersedes'].append({
                'id': row[0],
                'label': row[1],
                'name': row[2],
                'version': row[3]
            })

        # Fetch superseding releases (SUPERSEDES relationship - incoming)
        superseded_by_query = """
            MATCH (release:Release) WHERE elementId(release) = $eid
            MATCH (new_release:Release)-[:SUPERSEDES]->(release)
            WITH new_release, apoc.convert.fromJsonMap(new_release.custom_properties) AS props
            RETURN 
                elementId(new_release) AS id,
                labels(new_release)[0] AS label,
                COALESCE(props.name, 'Unnamed') AS name,
                COALESCE(props.version, 'Unknown') AS version
        """
        superseded_by_result, _ = db.cypher_query(superseded_by_query, {'eid': element_id})
        for row in superseded_by_result:
            context['custom_data']['superseded_by'].append({
                'id': row[0],
                'label': row[1],
                'name': row[2],
                'version': row[3]
            })

    except Exception as e:
        context['error'] = str(e)

    return context


def event_details_tab(request, label, element_id):
    """
    Custom view for Event Details tab.
    Shows triggered issues, related events, and source devices.
    """
    context = {
        'label': label,
        'element_id': element_id,
        'node': None,
        'custom_data': {
            'triggered_issues': [],
            'related_events': [],
            'source_devices': []
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
            context['error'] = f"Event node not found: {element_id}"
            return context

        raw_node = result[0][0]
        node = node_class.inflate(raw_node)
        context['node'] = node

        # Fetch triggered issues (TRIGGERS relationship)
        issues_query = """
            MATCH (event:Event) WHERE elementId(event) = $eid
            MATCH (event)-[:TRIGGERS]->(issue:Issue)
            WITH issue, apoc.convert.fromJsonMap(issue.custom_properties) AS props
            RETURN 
                elementId(issue) AS id,
                labels(issue)[0] AS label,
                COALESCE(props.name, 'Unnamed') AS name,
                COALESCE(props.status, 'Unknown') AS status,
                COALESCE(props.priority, 'Unknown') AS priority
        """
        issues_result, _ = db.cypher_query(issues_query, {'eid': element_id})
        for row in issues_result:
            context['custom_data']['triggered_issues'].append({
                'id': row[0],
                'label': row[1],
                'name': row[2],
                'status': row[3],
                'priority': row[4]
            })

        # Fetch related events (RELATED_TO relationship)
        related_events_query = """
            MATCH (event:Event) WHERE elementId(event) = $eid
            MATCH (event)-[:RELATED_TO]->(related:Event)
            WITH related, apoc.convert.fromJsonMap(related.custom_properties) AS props
            RETURN 
                elementId(related) AS id,
                labels(related)[0] AS label,
                COALESCE(props.name, 'Unnamed') AS name,
                COALESCE(props.severity, 'Unknown') AS severity,
                COALESCE(props.timestamp, 'Unknown') AS timestamp
        """
        related_result, _ = db.cypher_query(related_events_query, {'eid': element_id})
        for row in related_result:
            context['custom_data']['related_events'].append({
                'id': row[0],
                'label': row[1],
                'name': row[2],
                'severity': row[3],
                'timestamp': row[4]
            })

        # Fetch source devices (ORIGINATED_FROM relationship)
        devices_query = """
            MATCH (event:Event) WHERE elementId(event) = $eid
            MATCH (event)-[:ORIGINATED_FROM]->(device:Device)
            WITH device, apoc.convert.fromJsonMap(device.custom_properties) AS props
            RETURN 
                elementId(device) AS id,
                labels(device)[0] AS label,
                COALESCE(props.name, 'Unnamed') AS name
        """
        devices_result, _ = db.cypher_query(devices_query, {'eid': element_id})
        for row in devices_result:
            context['custom_data']['source_devices'].append({
                'id': row[0],
                'label': row[1],
                'name': row[2]
            })

    except Exception as e:
        context['error'] = str(e)

    return context
