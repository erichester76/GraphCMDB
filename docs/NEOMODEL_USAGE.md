# Neomodel vs Raw Cypher Usage Guidelines

This document explains when to use Neomodel ORM methods vs raw Cypher queries in GraphCMDB.

## General Principle

**Use Neomodel abstraction methods when possible for maintainability. Cypher is encapsulated in helper methods.**

## Available Helper Methods

### ✅ Node Operations
```python
# Creating nodes
node = node_class(custom_properties={'name': 'Server1'}).save()

# Reading nodes
nodes = node_class.nodes.all()
count = node_class.nodes.count()

# Get node by element ID
node = node_class.get_by_element_id(element_id)

# Get property safely
value = node.get_property('name', default='Unknown')

# Updating nodes
node.custom_properties = {'name': 'Server2'}
node.save()

# Deleting nodes
node.delete()
```

### ✅ Relationship Operations
```python
# Get all outgoing relationships
out_rels = node.get_outgoing_relationships()
# Returns: {'REL_TYPE': [{'target_id': '...', 'target_label': '...', 'target_name': '...'}]}

# Get all incoming relationships  
in_rels = node.get_incoming_relationships()
# Returns: {'REL_TYPE': [{'source_id': '...', 'source_label': '...', 'source_name': '...'}]}

# Create relationship
DynamicNode.connect_nodes(source_eid, source_label, 'REL_TYPE', target_eid, target_label)

# Delete relationship
deleted_count = DynamicNode.disconnect_nodes(source_eid, source_label, 'REL_TYPE', target_eid, target_label)
```

## When Raw Cypher is Used (Internally)

The helper methods encapsulate Cypher queries for:

### 1. Element ID Lookups
Getting nodes by Neo4j element ID requires Cypher since Neomodel uses integer IDs:
```python
# In get_by_element_id()
MATCH (n:`Label`) WHERE elementId(n) = $eid RETURN n
```

### 2. Relationship Traversals with APOC
Getting all relationships with related node metadata:
```python
# In get_outgoing_relationships() and get_incoming_relationships()
MATCH (n)-[r]->(m)
WITH type(r), elementId(m), labels(m)[0],
     apoc.convert.fromJsonMap(m.custom_properties) AS props
RETURN type(r), elementId(m), labels(m)[0], 
       COALESCE(props.name, props[head(keys(props))]) AS name
```

### 3. Dynamic Relationship Creation/Deletion
Creating/deleting relationships with runtime-determined types:
```python
# In connect_nodes() and disconnect_nodes()
MATCH (source:`Label1`) WHERE elementId(source) = $sid
MATCH (target:`Label2`) WHERE elementId(target) = $tid
MERGE (source)-[:`DYNAMIC_TYPE`]->(target)
```

## Benefits of This Approach

1. **Clean Views**: Views no longer contain raw Cypher queries
2. **Centralized Logic**: All Cypher is in the model layer
3. **Reusability**: Helper methods used across multiple views
4. **Maintainability**: Changes to query logic only need to be made in one place
5. **Testability**: Helper methods can be unit tested independently

## Code Organization

### DynamicNode Helper Methods
All relationship and node operations are now abstracted in `cmdb/models.py`:

```python
# Node operations
node = DynamicNode.get_by_element_id(element_id)
value = node.get_property('key', default)

# Relationship queries
out_rels = node.get_outgoing_relationships()
in_rels = node.get_incoming_relationships()

# Relationship mutations
DynamicNode.connect_nodes(source_eid, source_label, rel_type, target_eid, target_label)
DynamicNode.disconnect_nodes(source_eid, source_label, rel_type, target_eid, target_label)
```

### Views Layer
Views now use clean, abstracted methods:
- No raw Cypher queries in `cmdb/views.py`
- Business logic focuses on HTTP handling
- Data access delegated to model layer

## Feature Pack Integration

Feature packs still use Cypher for domain-specific hierarchical queries (e.g., data center rack layouts) as these require:
- Multi-level nested relationships
- Complex APOC aggregations  
- Domain-specific ordering and filtering

These are kept as Cypher because they are specialized use cases that benefit from Neo4j's query language.

## Migration Summary

### Phase 1 (Completed)
- ✅ Added `get_by_element_id()` helper method
- ✅ Added `get_property()` helper method  
- ✅ Dashboard counts use `node_class.nodes.count()`

### Phase 2 (Completed)
- ✅ Added `get_outgoing_relationships()` helper method
- ✅ Added `get_incoming_relationships()` helper method
- ✅ Added `connect_nodes()` class method
- ✅ Added `disconnect_nodes()` class method
- ✅ Updated all views to use helper methods
- ✅ **Eliminated all raw Cypher from cmdb/views.py**

This provides excellent separation of concerns and code maintainability.
