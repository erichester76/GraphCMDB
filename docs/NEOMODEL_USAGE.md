# Neomodel vs Raw Cypher Usage Guidelines

This document explains when to use Neomodel ORM methods vs raw Cypher queries in GraphCMDB.

## General Principle

**Use Neomodel when possible for maintainability, use Cypher when necessary for performance and advanced features.**

## When to Use Neomodel

### ✅ Simple CRUD Operations
```python
# Creating nodes
node = node_class(custom_properties={'name': 'Server1'}).save()

# Reading nodes
nodes = node_class.nodes.all()
node = node_class.nodes.get(id=123)

# Counting nodes
count = node_class.nodes.count()  # Instead of MATCH (n:Label) RETURN count(n)

# Updating nodes
node.custom_properties = {'name': 'Server2'}
node.save()

# Deleting nodes
node.delete()
```

### ✅ Basic Node Retrieval
```python
# Use helper method for element ID lookups
node = node_class.get_by_element_id(element_id)
if not node:
    # Handle not found case
```

### ✅ Simple Relationship Operations
```python
# Connect nodes
source.RELATIONSHIP_TYPE.connect(target)

# Disconnect nodes
source.RELATIONSHIP_TYPE.disconnect(target)
```

## When to Use Raw Cypher

### ✅ Complex Graph Traversals
When you need to traverse multiple levels or match complex patterns:
```cypher
MATCH (n:Label) WHERE elementId(n) = $eid
MATCH (n)-[r]->(m)
RETURN type(r), elementId(m), labels(m)[0]
```

### ✅ APOC Function Calls
When using APOC for JSON manipulation, aggregations, or other advanced features:
```cypher
WITH apoc.convert.fromJsonMap(node.custom_properties) AS props
RETURN COALESCE(props.name, props.Name, 'Unnamed')
```

### ✅ Hierarchical Queries
Multi-level nested relationships (e.g., Room → Row → Rack → Unit):
```cypher
MATCH (room:Room) WHERE elementId(room) = $eid
MATCH (row:Row)-[:LOCATED_IN]->(room)
MATCH (rack:Rack)-[:LOCATED_IN]->(row)
RETURN row, rack ORDER BY row.name, rack.name
```

### ✅ Complex Aggregations and Ordering
When you need advanced filtering, sorting, or aggregation:
```cypher
MATCH (n:Label)-[r]->(m)
WITH type(r) AS rel_type, count(m) AS target_count
RETURN rel_type, target_count
ORDER BY target_count DESC
```

## Code Organization

### Helper Methods in models.py
Add reusable methods to `DynamicNode` for common operations:
```python
@classmethod
def get_by_element_id(cls, element_id: str):
    """Retrieve node by Neo4j element ID"""
    # Implementation using Cypher when necessary
```

### Views
- Use Neomodel methods for simple operations
- Use raw Cypher for complex queries
- Keep relationship traversal queries as Cypher (they need element IDs and APOC)

## Benefits of This Approach

1. **Maintainability**: Simple operations use clean ORM syntax
2. **Performance**: Complex operations use optimized Cypher
3. **Consistency**: Clear guidelines for when to use each approach
4. **Flexibility**: Can leverage both Neomodel and Neo4j's full power

## Migration Notes

We've updated the codebase to follow these guidelines:
- ✅ Dashboard counts now use `node_class.nodes.count()`
- ✅ Node retrieval by element ID uses helper method `get_by_element_id()`
- ✅ Complex relationship queries remain as raw Cypher
- ✅ APOC-based queries remain as raw Cypher

This provides the best balance of code clarity and performance.
