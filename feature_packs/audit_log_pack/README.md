# Audit Log Feature Pack

## Overview
The Audit Log Pack provides comprehensive change tracking and auditing capabilities for the GraphCMDB system. It logs all create, update, delete, and relationship operations on nodes in the database.

## Features

### 1. Automatic Change Tracking
All modifications to the CMDB are automatically logged with the following information:
- **Timestamp**: When the change occurred
- **Action**: Type of operation (create, update, delete, connect, disconnect)
- **Node Information**: Label, ID, and name of the affected node
- **User**: User who performed the action (or 'System' if not authenticated)
- **Changes**: Description of what was modified
- **Relationship Information**: For connect/disconnect operations, includes relationship type, target label, and target ID

### 2. Global Audit Log View
Access the complete audit log from the sidebar navigation:
- Path: `/cmdb/audit-log/`
- Shows all audit entries across the entire system
- Limited to the latest 200 entries
- Sorted by timestamp (most recent first)
- Color-coded badges for different action types

### 3. Per-Node Audit Log Tab
Each node detail page includes an "Audit Log" tab:
- Tab order: 100 (always appears at the end)
- Shows only entries related to that specific node
- Limited to the latest 100 entries for that node
- Same color-coded interface as the global view

## Installation

The feature pack is automatically loaded by the core application when present in the `feature_packs/audit_log_pack/` directory.

### Files Structure
```
feature_packs/audit_log_pack/
├── config.py                 # Feature pack configuration
├── views.py                  # Audit log view functions and utilities
├── types.json               # AuditLogEntry node type definition
├── templates/
│   └── audit_log_tab.html   # Template for per-node audit log tab
└── README.md                # This file
```

## Data Model

### AuditLogEntry Node Type
The audit log uses a Neo4j node with the label `AuditLogEntry` and the following properties:

**Required Properties:**
- `timestamp` (string): ISO 8601 timestamp
- `action` (string): One of: create, update, delete, connect, disconnect
- `node_label` (string): Label of the affected node
- `node_id` (string): Element ID of the affected node

**Optional Properties:**
- `node_name` (string): Display name of the affected node
- `user` (string): Username of the user who performed the action
- `changes` (string): Description of the changes made
- `relationship_type` (string): For relationship operations
- `target_label` (string): For relationship operations
- `target_id` (string): For relationship operations

## Usage

### Viewing the Global Audit Log
1. Click "Audit Log" in the sidebar navigation
2. View all recent changes across the system
3. Click on any node link to navigate to its detail page

### Viewing Per-Node Audit Log
1. Navigate to any node detail page
2. Click on the "Audit Log" tab (rightmost tab)
3. View all changes specific to that node

### Audit Entry Colors
- **Green**: Create operations
- **Blue**: Update operations
- **Red**: Delete operations
- **Purple**: Connect (relationship creation) operations
- **Orange**: Disconnect (relationship removal) operations

## Integration with CMDB Operations

The audit logging is automatically integrated into the following CMDB operations:
- `node_create`: Logs node creation with initial properties
- `node_edit`: Logs property updates with list of changed keys
- `node_delete`: Logs node deletion
- `node_connect`: Logs relationship creation
- `node_disconnect`: Logs relationship removal

## Developer Notes

### Adding Audit Logging to Custom Operations
To add audit logging to custom operations, use the `create_audit_entry` function:

```python
from audit_log_pack.views import create_audit_entry

create_audit_entry(
    action='create',  # or 'update', 'delete', 'connect', 'disconnect'
    node_label='YourLabel',
    node_id='element-id',
    node_name='Optional display name',
    user='username',
    changes='Description of changes',
    # For relationship operations:
    relationship_type='RELATIONSHIP_TYPE',
    target_label='TargetLabel',
    target_id='target-element-id'
)
```

### Error Handling
The audit logging system is designed to be fail-safe:
- If audit log creation fails, it logs the error but doesn't interrupt the main operation
- This ensures that CMDB operations continue to work even if audit logging has issues

## Configuration

The feature pack is configured in `config.py`:

```python
FEATURE_PACK_CONFIG = {
    'name': 'Audit Log Pack',
    'applies_to_labels': 'all',
    'tabs': [
        {
            'id': 'audit_log',
            'name': 'Audit Log',
            'template': 'audit_log_tab.html',
            'custom_view': 'audit_log_pack.views.audit_log_tab',
            'for_labels': [],  # Empty list = applies to all labels
            'tab_order': 100   # Always appear at the end
        }
    ]
}
```

## Future Enhancements

Potential improvements for future versions:
- Pagination for audit log views
- Advanced filtering (by date range, action type, user)
- Export audit logs to CSV/JSON
- Audit log retention policies
- More detailed change tracking (before/after values)
- Real-time audit log updates using WebSockets
