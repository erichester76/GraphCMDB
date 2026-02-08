# List View UI Changes - Visual Overview

## Before (Original Implementation)

```
┌─────────────────────────────────────────────────────────────┐
│ Header: [Some Node Type] Nodes                              │
│ Actions: [Create Button] [Refresh Button]                   │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ ID             │ Properties      │ Actions                  │
├─────────────────────────────────────────────────────────────┤
│ 4:a1b2c3...    │ Interface-01    │ Detail | Delete         │
│ 4:d4e5f6...    │ Interface-02    │ Detail | Delete         │
│ 4:g7h8i9...    │ Interface-03    │ Detail | Delete         │
└─────────────────────────────────────────────────────────────┘

Issues:
✗ Header spillover from detail view
✗ Only shows one property value
✗ No column management
✗ No filtering capability
```

## After (Enhanced Implementation)

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Interface Nodes                                                          │
│ [Columns ▼] [Filter: _______] [Create Interface] [Refresh]             │
└─────────────────────────────────────────────────────────────────────────┘
      │
      └─→ Dropdown Menu:
          ┌───────────────────────┐
          │ Show/Hide Columns     │
          ├───────────────────────┤
          │ ☑ name               │
          │ ☑ speed_mbps         │
          │ ☐ duplex             │
          │ ☑ status             │
          │ ☑ description        │
          └───────────────────────┘

┌──────────────┬──────────┬──────────────┬────────────┬─────────────────┐
│ ID           │ Name     │ Speed Mbps   │ Status     │ Actions         │
├──────────────┼──────────┼──────────────┼────────────┼─────────────────┤
│ 4:a1b2c3..  │ eth0     │ 1000         │ up         │ Detail | Delete │
│ 4:d4e5f6..  │ eth1     │ 1000         │ down       │ Detail | Delete │
│ 4:g7h8i9..  │ eth2     │ 100          │ up         │ Detail | Delete │
└──────────────┴──────────┴──────────────┴────────────┴─────────────────┘
                           ↑
                           │
                    Columns shown based on:
                    1. Type registry configuration
                    2. User preferences (localStorage)

Features:
✓ Clean header updates (no spillover)
✓ Multiple property columns displayed
✓ Column show/hide with persistence
✓ Real-time filtering
✓ Dark mode support
```

## Column Management Flow

```
User Action                  System Response                   Storage
───────────────────────────────────────────────────────────────────────

1. Load list view       →    Load type columns            →   localStorage
   for "Interface"           from registry                     check for
                                                               "cmdb_list_columns_Interface"

2. Apply saved          →    Show/hide columns            
   preferences               based on saved state

3. User toggles         →    Update table display         →   Save to localStorage
   column checkbox           immediately                       as JSON array

4. User filters         →    Hide non-matching rows
   "eth0"                    (client-side only)

5. Navigate away        →    Preferences remain           →   Persisted in
   and return                for next visit                    localStorage
```

## Type Registry Integration

```
Feature Pack types.json
─────────────────────────────────────────────────
{
  "Interface": {
    "display_name": "Network Interface",
    "properties": [
      "name",          ←─┐
      "speed_mbps",      │  All available properties
      "duplex",          │
      "status",          │
      "description"    ←─┘
    ],
    "columns": [
      "name",          ←─┐
      "speed_mbps",      │  Default visible columns
      "status"         ←─┘  (can be customized by user)
    ]
  }
}

                    ↓

Registry.get_metadata("Interface")
─────────────────────────────────────────────────
Returns:
{
  "columns": ["name", "speed_mbps", "status"],
  "properties": ["name", "speed_mbps", "duplex", "status", "description"],
  ...
}

                    ↓

View (nodes_list)
─────────────────────────────────────────────────
Extracts property values for each column:
nodes_data = [{
  "element_id": "4:abc123",
  "columns": {
    "name": "eth0",
    "speed_mbps": 1000,
    "status": "up"
  }
}, ...]

                    ↓

Template (nodes_table.html)
─────────────────────────────────────────────────
<th data-column="name">Name</th>
<th data-column="speed_mbps">Speed Mbps</th>
<th data-column="status">Status</th>
...
<td data-column="name">eth0</td>
<td data-column="speed_mbps">1000</td>
<td data-column="status">up</td>
```

## JavaScript Architecture

```
list_view.js Module
═══════════════════════════════════════════════

┌─────────────────────────────────────────┐
│ Initialization on DOM Ready             │
│  └─ initListView()                      │
│      ├─ initColumnSelector()            │
│      │   ├─ Setup dropdown toggle       │
│      │   ├─ Bind checkbox handlers      │
│      │   └─ applySavedPreferences()     │
│      └─ initFiltering()                 │
│          ├─ Setup input handler         │
│          └─ Setup clear button          │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│ User Interactions                        │
│                                          │
│ Column Toggle Clicked                   │
│  └─ applyColumnVisibility()             │
│      ├─ getVisibleColumns()             │
│      ├─ Update DOM (show/hide)          │
│      └─ saveColumnPreferences()         │
│                                          │
│ Filter Input Changed                    │
│  └─ applyFilter()                       │
│      └─ Show/hide rows based on text   │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│ HTMX Integration                        │
│                                          │
│ htmx:afterSwap event                    │
│  └─ Re-run initListView()               │
│      └─ Reinitialize after partial     │
│          page updates                   │
└─────────────────────────────────────────┘
```

## Local Storage Schema

```javascript
// Storage Key Format
"cmdb_list_columns_{NodeLabel}"

// Example Keys
"cmdb_list_columns_Interface"
"cmdb_list_columns_Network"
"cmdb_list_columns_IP_Address"

// Storage Value Format (JSON Array)
["name", "speed_mbps", "status"]

// Example Storage State
localStorage = {
  "cmdb_list_columns_Interface": '["name","speed_mbps","status"]',
  "cmdb_list_columns_Network": '["name","cidr","description"]',
  "cmdb_list_columns_IP_Address": '["address","type","status"]'
}
```

## Component Interaction Flow

```
┌─────────────┐
│   Browser   │
│  LocalStore │
└──────┬──────┘
       │ load preferences
       ↓
┌─────────────────────────┐      ┌──────────────────┐
│  list_view.js           │←────→│  nodes_table.html│
│  - Column visibility    │      │  - Dynamic cols  │
│  - Filtering            │      │  - Data display  │
└──────┬──────────────────┘      └──────────────────┘
       │                                   ↑
       │ apply to DOM                      │
       ↓                                   │
┌─────────────────────────┐      ┌──────────────────┐
│  Column Selector UI     │      │  views.py        │
│  (nodes_list_header)    │      │  - Extract cols  │
└─────────────────────────┘      │  - Format data   │
                                  └────────┬─────────┘
                                           │
                                           ↓
                                  ┌──────────────────┐
                                  │  registry.py     │
                                  │  - Column config │
                                  └────────┬─────────┘
                                           │
                                           ↓
                                  ┌──────────────────┐
                                  │  types.json      │
                                  │  - Column defs   │
                                  └──────────────────┘
```
