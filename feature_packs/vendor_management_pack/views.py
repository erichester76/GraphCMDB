# feature_packs/vendor_management_pack/views.py

from django.shortcuts import render
from neomodel import db
from cmdb.models import DynamicNode


def vendor_details_tab(request, label, element_id):
    """
    Context builder for Vendor Details tab.
    Shows all contracts provided by this vendor and circuits (if network_pack exists).
    Returns context dictionary rather than rendering template directly.
    """
    context = {
        'label': label,
        'element_id': element_id,
        'node': None,
        'custom_data': {
            'contracts': [],
            'circuits': []
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
            context['error'] = f"Vendor node not found: {element_id}"
            return context

        raw_node = result[0][0]
        node = node_class.inflate(raw_node)
        context['node'] = node

        # Fetch contracts (incoming PROVIDED_BY relationships from Contract nodes)
        contracts_query = """
            MATCH (vendor:Vendor) WHERE elementId(vendor) = $eid
            MATCH (contract:Contract)-[:PROVIDED_BY]->(vendor)
            WITH contract, apoc.convert.fromJsonMap(contract.custom_properties) AS contract_props
            OPTIONAL MATCH (contract)-[:MANAGED_BY]->(person:Person)
            WITH contract, contract_props, person, apoc.convert.fromJsonMap(person.custom_properties) AS person_props
            RETURN 
                elementId(contract) AS contract_id,
                labels(contract)[0] AS contract_label,
                COALESCE(contract_props.name, 'Unnamed') AS name,
                COALESCE(contract_props.contract_id, 'Unknown') AS contract_id_value,
                COALESCE(contract_props.start_date, '') AS start_date,
                COALESCE(contract_props.end_date, '') AS end_date,
                COALESCE(contract_props.value, '') AS value,
                elementId(person) AS person_id,
                labels(person)[0] AS person_label,
                COALESCE(person_props.name, 'Unknown') AS person_name
            ORDER BY contract_props.name
        """
        contracts_result, _ = db.cypher_query(contracts_query, {'eid': element_id})
        for row in contracts_result:
            contract_data = {
                'id': row[0],
                'label': row[1],
                'name': row[2],
                'contract_id': row[3],
                'start_date': row[4],
                'end_date': row[5],
                'value': row[6],
                'manager': None
            }
            if row[7]:  # person_id exists
                contract_data['manager'] = {
                    'id': row[7],
                    'label': row[8],
                    'name': row[9]
                }
            context['custom_data']['contracts'].append(contract_data)

        # Fetch circuits (incoming PROVIDED_BY relationships from Circuit nodes, if they exist)
        circuits_query = """
            MATCH (vendor:Vendor) WHERE elementId(vendor) = $eid
            MATCH (circuit:Circuit)-[:PROVIDED_BY]->(vendor)
            WITH circuit, apoc.convert.fromJsonMap(circuit.custom_properties) AS circuit_props
            RETURN 
                elementId(circuit) AS circuit_id,
                labels(circuit)[0] AS circuit_label,
                COALESCE(circuit_props.name, 'Unnamed') AS name,
                COALESCE(circuit_props.circuit_id, 'Unknown') AS circuit_id_value,
                COALESCE(circuit_props.bandwidth_mbps, 0) AS bandwidth_mbps,
                COALESCE(circuit_props.status, 'Unknown') AS status
            ORDER BY circuit_props.name
        """
        circuits_result, _ = db.cypher_query(circuits_query, {'eid': element_id})
        for row in circuits_result:
            context['custom_data']['circuits'].append({
                'id': row[0],
                'label': row[1],
                'name': row[2],
                'circuit_id': row[3],
                'bandwidth_mbps': row[4],
                'status': row[5]
            })

    except Exception as e:
        context['error'] = str(e)

    return context


def contract_details_tab(request, label, element_id):
    """
    Context builder for Contract Details tab.
    Shows providing vendor (PROVIDED_BY outgoing) and managed by person (MANAGED_BY outgoing).
    Returns context dictionary rather than rendering template directly.
    """
    context = {
        'label': label,
        'element_id': element_id,
        'node': None,
        'custom_data': {
            'vendor': None,
            'manager': None
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
            context['error'] = f"Contract node not found: {element_id}"
            return context

        raw_node = result[0][0]
        node = node_class.inflate(raw_node)
        context['node'] = node

        # Fetch providing vendor (outgoing PROVIDED_BY relationship)
        vendor_query = """
            MATCH (contract:Contract) WHERE elementId(contract) = $eid
            MATCH (contract)-[:PROVIDED_BY]->(vendor:Vendor)
            WITH vendor, apoc.convert.fromJsonMap(vendor.custom_properties) AS vendor_props
            RETURN 
                elementId(vendor) AS vendor_id,
                labels(vendor)[0] AS vendor_label,
                COALESCE(vendor_props.name, 'Unnamed') AS name,
                COALESCE(vendor_props.website, '') AS website,
                COALESCE(vendor_props.contact_email, '') AS contact_email
        """
        vendor_result, _ = db.cypher_query(vendor_query, {'eid': element_id})
        if vendor_result:
            row = vendor_result[0]
            context['custom_data']['vendor'] = {
                'id': row[0],
                'label': row[1],
                'name': row[2],
                'website': row[3],
                'contact_email': row[4]
            }

        # Fetch managing person (outgoing MANAGED_BY relationship)
        manager_query = """
            MATCH (contract:Contract) WHERE elementId(contract) = $eid
            MATCH (contract)-[:MANAGED_BY]->(person:Person)
            WITH person, apoc.convert.fromJsonMap(person.custom_properties) AS person_props
            RETURN 
                elementId(person) AS person_id,
                labels(person)[0] AS person_label,
                COALESCE(person_props.name, 'Unnamed') AS name,
                COALESCE(person_props.email, '') AS email,
                COALESCE(person_props.phone, '') AS phone
        """
        manager_result, _ = db.cypher_query(manager_query, {'eid': element_id})
        if manager_result:
            row = manager_result[0]
            context['custom_data']['manager'] = {
                'id': row[0],
                'label': row[1],
                'name': row[2],
                'email': row[3],
                'phone': row[4]
            }

    except Exception as e:
        context['error'] = str(e)

    return context
