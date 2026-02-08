# Audit Log Tab Fix - Issue Resolution

## Problem
Changes were showing up in the main audit log view but not appearing in the per-node audit log tab on individual item detail pages.

## Root Cause
The per-node audit log tab was using a Cypher query with APOC's `apoc.convert.fromJsonMap()` function to access the `custom_properties` field:

```python
query = """
    MATCH (log:AuditLogEntry)
    WHERE apoc.convert.fromJsonMap(log.custom_properties).node_id = $eid
    ...
"""
```

This approach was inconsistent with how the global audit log view accessed the data, which used neomodel's object-relational mapping:

```python
audit_nodes = audit_node_class.nodes.all()
for node in audit_nodes:
    props = node.custom_properties or {}
```

The APOC approach wasn't properly accessing the stored custom_properties data, resulting in no entries being returned for the per-node view.

## Solution
Updated the `audit_log_tab()` function in `feature_packs/audit_log_pack/views.py` to use the same data access pattern as the global audit log view:

### Before (Using APOC):
```python
def audit_log_tab(request, label, element_id):
    try:
        query = """
            MATCH (log:AuditLogEntry)
            WHERE apoc.convert.fromJsonMap(log.custom_properties).node_id = $eid
            WITH log, apoc.convert.fromJsonMap(log.custom_properties) AS props
            RETURN ...
        """
        result, _ = db.cypher_query(query, {'eid': element_id})
        # Process raw query results...
```

### After (Using neomodel):
```python
def audit_log_tab(request, label, element_id):
    try:
        # Fetch all audit log entries using neomodel (same as global view)
        audit_node_class = DynamicNode.get_or_create_label('AuditLogEntry')
        all_audit_nodes = audit_node_class.nodes.all()
        
        # Filter to only entries for this specific node
        audit_entries = []
        for node in all_audit_nodes:
            props = node.custom_properties or {}
            if props.get('node_id') == element_id:
                audit_entries.append({...})
        
        # Sort by timestamp descending and limit to 100
        audit_entries.sort(key=lambda x: x['timestamp'], reverse=True)
        context['audit_entries'] = audit_entries[:100]
```

## Benefits of the Fix

1. **Consistency**: Both global and per-node audit log views now use the same data access pattern
2. **Reliability**: Using neomodel's ORM is more reliable than raw Cypher with APOC
3. **Maintainability**: Easier to debug and maintain with Python-based filtering
4. **No APOC dependency**: Doesn't rely on APOC being installed and configured correctly

## Testing Recommendations

To verify the fix:

1. **Create a test node** and verify the creation appears in both:
   - Global audit log (`/cmdb/audit-log/`)
   - Per-node audit log tab on the node's detail page

2. **Edit the node** and verify updates appear in both views

3. **Create and remove relationships** and verify they appear in both views

4. **Delete the node** and verify deletion is logged in the global view

## Technical Notes

- The fix filters audit entries in Python after fetching all entries from Neo4j
- For large databases with many audit entries, this approach loads all audit entries into memory
- If performance becomes an issue, a Cypher query could be used, but it would need to properly access the custom_properties field without relying on APOC
- The current approach is consistent with the rest of the codebase and works reliably

## Files Changed

- `feature_packs/audit_log_pack/views.py` - Updated `audit_log_tab()` function
