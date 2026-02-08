# feature_packs/organization_pack/views.py

from django.shortcuts import render
from neomodel import db
from cmdb.models import DynamicNode


def person_details_tab(request, label, element_id):
    """
    Context builder for Person Details tab.
    Shows department (WORKS_IN outgoing), managed departments (MANAGES outgoing),
    reports to (REPORTS_TO outgoing), and located in room (LOCATED_IN outgoing).
    Returns context dictionary rather than rendering template directly.
    """
    context = {
        'label': label,
        'element_id': element_id,
        'node': None,
        'custom_data': {
            'department': None,
            'managed_departments': [],
            'reports_to': None,
            'room': None
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
            context['error'] = f"Person node not found: {element_id}"
            return context

        raw_node = result[0][0]
        node = node_class.inflate(raw_node)
        context['node'] = node

        # Fetch department (outgoing WORKS_IN relationship)
        department_query = """
            MATCH (person:Person) WHERE elementId(person) = $eid
            MATCH (person)-[:WORKS_IN]->(dept:Department)
            WITH dept, apoc.convert.fromJsonMap(dept.custom_properties) AS dept_props
            RETURN 
                elementId(dept) AS dept_id,
                labels(dept)[0] AS dept_label,
                COALESCE(dept_props.name, 'Unnamed') AS name,
                COALESCE(dept_props.code, '') AS code,
                COALESCE(dept_props.description, '') AS description
        """
        department_result, _ = db.cypher_query(department_query, {'eid': element_id})
        if department_result:
            row = department_result[0]
            context['custom_data']['department'] = {
                'id': row[0],
                'label': row[1],
                'name': row[2],
                'code': row[3],
                'description': row[4]
            }

        # Fetch managed departments (outgoing MANAGES relationships)
        managed_depts_query = """
            MATCH (person:Person) WHERE elementId(person) = $eid
            MATCH (person)-[:MANAGES]->(dept:Department)
            WITH dept, apoc.convert.fromJsonMap(dept.custom_properties) AS dept_props
            RETURN 
                elementId(dept) AS dept_id,
                labels(dept)[0] AS dept_label,
                COALESCE(dept_props.name, 'Unnamed') AS name,
                COALESCE(dept_props.code, '') AS code,
                COALESCE(dept_props.headcount, 0) AS headcount
            ORDER BY dept_props.name
        """
        managed_depts_result, _ = db.cypher_query(managed_depts_query, {'eid': element_id})
        for row in managed_depts_result:
            context['custom_data']['managed_departments'].append({
                'id': row[0],
                'label': row[1],
                'name': row[2],
                'code': row[3],
                'headcount': row[4]
            })

        # Fetch reports to (outgoing REPORTS_TO relationship)
        reports_to_query = """
            MATCH (person:Person) WHERE elementId(person) = $eid
            MATCH (person)-[:REPORTS_TO]->(manager:Person)
            WITH manager, apoc.convert.fromJsonMap(manager.custom_properties) AS mgr_props
            RETURN 
                elementId(manager) AS mgr_id,
                labels(manager)[0] AS mgr_label,
                COALESCE(mgr_props.name, 'Unnamed') AS name,
                COALESCE(mgr_props.title, '') AS title,
                COALESCE(mgr_props.email, '') AS email
        """
        reports_to_result, _ = db.cypher_query(reports_to_query, {'eid': element_id})
        if reports_to_result:
            row = reports_to_result[0]
            context['custom_data']['reports_to'] = {
                'id': row[0],
                'label': row[1],
                'name': row[2],
                'title': row[3],
                'email': row[4]
            }

        # Fetch room (outgoing LOCATED_IN relationship)
        room_query = """
            MATCH (person:Person) WHERE elementId(person) = $eid
            MATCH (person)-[:LOCATED_IN]->(room:Room)
            WITH room, apoc.convert.fromJsonMap(room.custom_properties) AS room_props
            RETURN 
                elementId(room) AS room_id,
                labels(room)[0] AS room_label,
                COALESCE(room_props.name, 'Unnamed') AS name,
                COALESCE(room_props.room_number, '') AS room_number,
                COALESCE(room_props.floor, '') AS floor
        """
        room_result, _ = db.cypher_query(room_query, {'eid': element_id})
        if room_result:
            row = room_result[0]
            context['custom_data']['room'] = {
                'id': row[0],
                'label': row[1],
                'name': row[2],
                'room_number': row[3],
                'floor': row[4]
            }

    except Exception as e:
        context['error'] = str(e)

    return context


def department_details_tab(request, label, element_id):
    """
    Context builder for Department Details tab.
    Shows parent organization (PART_OF outgoing), managed by person (MANAGED_BY outgoing),
    located at building (LOCATED_AT outgoing), and team members (WORKS_IN incoming).
    Returns context dictionary rather than rendering template directly.
    """
    context = {
        'label': label,
        'element_id': element_id,
        'node': None,
        'custom_data': {
            'organization': None,
            'manager': None,
            'building': None,
            'team_members': []
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
            context['error'] = f"Department node not found: {element_id}"
            return context

        raw_node = result[0][0]
        node = node_class.inflate(raw_node)
        context['node'] = node

        # Fetch parent organization (outgoing PART_OF relationship)
        org_query = """
            MATCH (dept:Department) WHERE elementId(dept) = $eid
            MATCH (dept)-[:PART_OF]->(org:Organization)
            WITH org, apoc.convert.fromJsonMap(org.custom_properties) AS org_props
            RETURN 
                elementId(org) AS org_id,
                labels(org)[0] AS org_label,
                COALESCE(org_props.name, 'Unnamed') AS name,
                COALESCE(org_props.legal_name, '') AS legal_name,
                COALESCE(org_props.industry, '') AS industry
        """
        org_result, _ = db.cypher_query(org_query, {'eid': element_id})
        if org_result:
            row = org_result[0]
            context['custom_data']['organization'] = {
                'id': row[0],
                'label': row[1],
                'name': row[2],
                'legal_name': row[3],
                'industry': row[4]
            }

        # Fetch manager (outgoing MANAGED_BY relationship)
        manager_query = """
            MATCH (dept:Department) WHERE elementId(dept) = $eid
            MATCH (dept)-[:MANAGED_BY]->(manager:Person)
            WITH manager, apoc.convert.fromJsonMap(manager.custom_properties) AS mgr_props
            RETURN 
                elementId(manager) AS mgr_id,
                labels(manager)[0] AS mgr_label,
                COALESCE(mgr_props.name, 'Unnamed') AS name,
                COALESCE(mgr_props.title, '') AS title,
                COALESCE(mgr_props.email, '') AS email
        """
        manager_result, _ = db.cypher_query(manager_query, {'eid': element_id})
        if manager_result:
            row = manager_result[0]
            context['custom_data']['manager'] = {
                'id': row[0],
                'label': row[1],
                'name': row[2],
                'title': row[3],
                'email': row[4]
            }

        # Fetch building (outgoing LOCATED_AT relationship)
        building_query = """
            MATCH (dept:Department) WHERE elementId(dept) = $eid
            MATCH (dept)-[:LOCATED_AT]->(building:Building)
            WITH building, apoc.convert.fromJsonMap(building.custom_properties) AS bldg_props
            RETURN 
                elementId(building) AS bldg_id,
                labels(building)[0] AS bldg_label,
                COALESCE(bldg_props.name, 'Unnamed') AS name,
                COALESCE(bldg_props.address, '') AS address,
                COALESCE(bldg_props.floors, 0) AS floors
        """
        building_result, _ = db.cypher_query(building_query, {'eid': element_id})
        if building_result:
            row = building_result[0]
            context['custom_data']['building'] = {
                'id': row[0],
                'label': row[1],
                'name': row[2],
                'address': row[3],
                'floors': row[4]
            }

        # Fetch team members (incoming WORKS_IN relationships)
        team_members_query = """
            MATCH (dept:Department) WHERE elementId(dept) = $eid
            MATCH (person:Person)-[:WORKS_IN]->(dept)
            WITH person, apoc.convert.fromJsonMap(person.custom_properties) AS person_props
            RETURN 
                elementId(person) AS person_id,
                labels(person)[0] AS person_label,
                COALESCE(person_props.name, 'Unnamed') AS name,
                COALESCE(person_props.title, '') AS title,
                COALESCE(person_props.email, '') AS email,
                COALESCE(person_props.status, 'Unknown') AS status
            ORDER BY person_props.name
        """
        team_members_result, _ = db.cypher_query(team_members_query, {'eid': element_id})
        for row in team_members_result:
            context['custom_data']['team_members'].append({
                'id': row[0],
                'label': row[1],
                'name': row[2],
                'title': row[3],
                'email': row[4],
                'status': row[5]
            })

    except Exception as e:
        context['error'] = str(e)

    return context


def site_details_tab(request, label, element_id):
    """
    Context builder for Site Details tab.
    Shows managed by person (MANAGED_BY outgoing), and buildings at site (LOCATED_IN incoming from Building).
    Returns context dictionary rather than rendering template directly.
    """
    context = {
        'label': label,
        'element_id': element_id,
        'node': None,
        'custom_data': {
            'manager': None,
            'buildings': []
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
            context['error'] = f"Site node not found: {element_id}"
            return context

        raw_node = result[0][0]
        node = node_class.inflate(raw_node)
        context['node'] = node

        # Fetch manager (outgoing MANAGED_BY relationship)
        manager_query = """
            MATCH (site:Site) WHERE elementId(site) = $eid
            MATCH (site)-[:MANAGED_BY]->(manager:Person)
            WITH manager, apoc.convert.fromJsonMap(manager.custom_properties) AS mgr_props
            RETURN 
                elementId(manager) AS mgr_id,
                labels(manager)[0] AS mgr_label,
                COALESCE(mgr_props.name, 'Unnamed') AS name,
                COALESCE(mgr_props.title, '') AS title,
                COALESCE(mgr_props.email, '') AS email
        """
        manager_result, _ = db.cypher_query(manager_query, {'eid': element_id})
        if manager_result:
            row = manager_result[0]
            context['custom_data']['manager'] = {
                'id': row[0],
                'label': row[1],
                'name': row[2],
                'title': row[3],
                'email': row[4]
            }

        # Fetch buildings (incoming LOCATED_IN relationships from Building)
        buildings_query = """
            MATCH (site:Site) WHERE elementId(site) = $eid
            MATCH (building:Building)-[:LOCATED_IN]->(site)
            WITH building, apoc.convert.fromJsonMap(building.custom_properties) AS bldg_props
            RETURN 
                elementId(building) AS bldg_id,
                labels(building)[0] AS bldg_label,
                COALESCE(bldg_props.name, 'Unnamed') AS name,
                COALESCE(bldg_props.address, '') AS address,
                COALESCE(bldg_props.floors, 0) AS floors,
                COALESCE(bldg_props.square_footage, 0) AS square_footage,
                COALESCE(bldg_props.status, 'Unknown') AS status
            ORDER BY bldg_props.name
        """
        buildings_result, _ = db.cypher_query(buildings_query, {'eid': element_id})
        for row in buildings_result:
            context['custom_data']['buildings'].append({
                'id': row[0],
                'label': row[1],
                'name': row[2],
                'address': row[3],
                'floors': row[4],
                'square_footage': row[5],
                'status': row[6]
            })

    except Exception as e:
        context['error'] = str(e)

    return context


def building_details_tab(request, label, element_id):
    """
    Context builder for Building Details tab.
    Shows parent site (LOCATED_IN outgoing), managed by (MANAGED_BY outgoing),
    and floors (LOCATED_IN incoming from Floor).
    Returns context dictionary rather than rendering template directly.
    """
    context = {
        'label': label,
        'element_id': element_id,
        'node': None,
        'custom_data': {
            'site': None,
            'manager': None,
            'floors': []
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
            context['error'] = f"Building node not found: {element_id}"
            return context

        raw_node = result[0][0]
        node = node_class.inflate(raw_node)
        context['node'] = node

        # Fetch parent site (outgoing LOCATED_IN relationship)
        site_query = """
            MATCH (building:Building) WHERE elementId(building) = $eid
            MATCH (building)-[:LOCATED_IN]->(site:Site)
            WITH site, apoc.convert.fromJsonMap(site.custom_properties) AS site_props
            RETURN 
                elementId(site) AS site_id,
                labels(site)[0] AS site_label,
                COALESCE(site_props.name, 'Unnamed') AS name,
                COALESCE(site_props.city, '') AS city,
                COALESCE(site_props.country, '') AS country
        """
        site_result, _ = db.cypher_query(site_query, {'eid': element_id})
        if site_result:
            row = site_result[0]
            context['custom_data']['site'] = {
                'id': row[0],
                'label': row[1],
                'name': row[2],
                'city': row[3],
                'country': row[4]
            }

        # Fetch manager (outgoing MANAGED_BY relationship)
        manager_query = """
            MATCH (building:Building) WHERE elementId(building) = $eid
            MATCH (building)-[:MANAGED_BY]->(manager:Person)
            WITH manager, apoc.convert.fromJsonMap(manager.custom_properties) AS mgr_props
            RETURN 
                elementId(manager) AS mgr_id,
                labels(manager)[0] AS mgr_label,
                COALESCE(mgr_props.name, 'Unnamed') AS name,
                COALESCE(mgr_props.title, '') AS title,
                COALESCE(mgr_props.email, '') AS email
        """
        manager_result, _ = db.cypher_query(manager_query, {'eid': element_id})
        if manager_result:
            row = manager_result[0]
            context['custom_data']['manager'] = {
                'id': row[0],
                'label': row[1],
                'name': row[2],
                'title': row[3],
                'email': row[4]
            }

        # Fetch floors (incoming LOCATED_IN relationships from Floor)
        floors_query = """
            MATCH (building:Building) WHERE elementId(building) = $eid
            MATCH (floor:Floor)-[:LOCATED_IN]->(building)
            WITH floor, apoc.convert.fromJsonMap(floor.custom_properties) AS floor_props
            RETURN 
                elementId(floor) AS floor_id,
                labels(floor)[0] AS floor_label,
                COALESCE(floor_props.floor_number, 'Unknown') AS floor_number,
                COALESCE(floor_props.description, '') AS description,
                COALESCE(floor_props.square_footage, 0) AS square_footage
            ORDER BY floor_props.floor_number
        """
        floors_result, _ = db.cypher_query(floors_query, {'eid': element_id})
        for row in floors_result:
            context['custom_data']['floors'].append({
                'id': row[0],
                'label': row[1],
                'floor_number': row[2],
                'description': row[3],
                'square_footage': row[4]
            })

    except Exception as e:
        context['error'] = str(e)

    return context
