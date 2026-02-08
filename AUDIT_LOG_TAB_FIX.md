# Audit Log Tab Fix - Issue Resolution

## Problem
Changes were showing up in the main audit log view but not appearing in the per-node audit log tab on individual item detail pages.

## Root Causes

### Issue 1: Incompatible Query Method
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

### Issue 2: Incorrect Context Structure
The context structure returned by the `audit_log_tab()` function didn't match what the template expected. The function was returning:
```python
context = {
    'audit_entries': [...]  # Wrong: at top level
    'error': None
}
```

But the template expected the feature pack pattern:
```python
context = {
    'custom_data': {
        'audit_entries': [...]  # Correct: nested under custom_data
    },
    'error': None  # Correct: at top level
}
```

## Solution

### Fix 1: Use neomodel for Data Access
Updated the `audit_log_tab()` function in `feature_packs/audit_log_pack/views.py` to use the same data access pattern as the global audit log view:

```python
def audit_log_tab(request, label, element_id):
    context = {
        'label': label,
        'element_id': element_id,
        'custom_data': {
            'audit_entries': []
        },
        'error': None,
    }
    
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
        context['custom_data']['audit_entries'] = audit_entries[:100]
        
    except Exception as e:
        context['error'] = str(e)
    
    return context
```

### Fix 2: Correct Template Structure
Updated the template in `feature_packs/audit_log_pack/templates/audit_log_tab.html` to match the feature pack pattern:

**Before:**
```django
{% if custom_data.error %}
    <div class="p-4 bg-red-100 text-red-800 rounded">
        Error loading audit log: {{ custom_data.error }}
    </div>
```

**After:**
```django
{% if error %}
    <div class="p-4 bg-red-100 text-red-800 rounded">
        Error loading audit log: {{ error }}
    </div>
```

## Benefits of the Fix

1. **Consistency**: Both global and per-node audit log views now use the same data access pattern
2. **Reliability**: Using neomodel's ORM is more reliable than raw Cypher with APOC
3. **Maintainability**: Easier to debug and maintain with Python-based filtering
4. **Standard Pattern**: Follows the established feature pack pattern used by other packs (e.g., ITSM pack)
5. **No APOC dependency issues**: Doesn't rely on APOC being installed and configured correctly

## Testing Recommendations

To verify the fix:

1. **Create a test node** and verify the creation appears in both:
   - Global audit log (`/cmdb/audit-log/`)
   - Per-node audit log tab on the node's detail page

2. **Edit the node** and verify updates appear in both views

3. **Create and remove relationships** and verify they appear in both views

4. **Delete the node** and verify deletion is logged in the global view

5. **Check for errors** - the error should display properly if there's an issue loading the audit log

## Technical Notes

- The fix filters audit entries in Python after fetching all entries from Neo4j
- For large databases with many audit entries, this approach loads all audit entries into memory
- If performance becomes an issue, a Cypher query could be used, but it would need to properly access the custom_properties field without relying on APOC
- The current approach is consistent with the rest of the codebase and works reliably
- The context structure now matches the pattern used by other feature packs (ITSM, Data Center, etc.)

## Files Changed

- `feature_packs/audit_log_pack/views.py` - Updated `audit_log_tab()` function
  - Changed from APOC Cypher query to neomodel data access
  - Fixed context structure to nest audit_entries under custom_data
- `feature_packs/audit_log_pack/templates/audit_log_tab.html` - Updated template
  - Changed error check from `custom_data.error` to `error`
