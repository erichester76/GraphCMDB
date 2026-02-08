# Property Choices Feature

## Overview
This document describes the property choices feature that allows type definitions to specify valid choices for properties. Properties with choices will render as dropdown/select fields in both create and edit forms instead of free-form text inputs.

## Motivation
Many properties have a limited set of valid values (e.g., status: "active", "decommissioned", "staged"). By defining these choices in the type definition, the UI can:
- Provide better user experience with dropdown selections
- Ensure data consistency by limiting input to valid values
- Reduce data entry errors
- Make the application more user-friendly

## Usage

### Defining Properties with Choices

In your `types.json` file, properties can be defined in two formats:

#### Simple Format (Backward Compatible)
```json
{
  "MyType": {
    "properties": ["name", "description", "status"]
  }
}
```

#### Format with Choices
```json
{
  "MyType": {
    "properties": [
      "name",
      "description",
      {
        "name": "status",
        "choices": ["active", "decommissioned", "staged", "maintenance"]
      }
    ]
  }
}
```

You can mix both formats in the same type definition:
```json
{
  "Device": {
    "properties": [
      "name",
      {"name": "type", "choices": ["server", "switch", "router", "firewall"]},
      "serial_number",
      {"name": "status", "choices": ["active", "decommissioned", "staged"]},
      "description"
    ]
  }
}
```

## Examples

### Network Interface
```json
{
  "Interface": {
    "display_name": "Network Interface",
    "category": "Networking",
    "properties": [
      "name",
      "speed_mbps",
      {"name": "duplex", "choices": ["full", "half", "auto"]},
      {"name": "status", "choices": ["active", "decommissioned", "staged", "maintenance"]},
      "description"
    ],
    "required": ["name"]
  }
}
```

### ITSM Issue
```json
{
  "Issue": {
    "display_name": "Issue",
    "category": "ITSM",
    "properties": [
      "name",
      "description",
      {"name": "priority", "choices": ["low", "medium", "high", "critical"]},
      {"name": "status", "choices": ["open", "in_progress", "resolved", "closed"]},
      "assignee",
      {"name": "impact", "choices": ["low", "medium", "high", "critical"]}
    ],
    "required": ["name", "priority", "status"]
  }
}
```

## User Interface Behavior

### Create Form
- Properties with choices render as dropdown/select fields
- Required fields with choices show a disabled "-- Select --" placeholder that cannot be submitted
- Optional fields with choices allow selecting the empty option to leave the field blank
- Properties without choices continue to render as text inputs

### Edit Form
- Properties with choices render as dropdown/select fields
- Current value is pre-selected in the dropdown
- Users can change the value by selecting a different option
- An empty option is available to clear the value if needed

### Raw JSON Editor
- The raw JSON editor fallback remains available on both create and edit forms
- This allows advanced users to bypass the form fields if needed
- Choices are not enforced in the raw JSON editor (validation happens at the application level)

## Implementation Details

### Parser Function
The `parse_property_definition()` function in `cmdb/views.py` handles parsing property definitions:

```python
def parse_property_definition(prop_def):
    """
    Parse a property definition which can be either:
    - A string: "property_name"
    - A dict: {"name": "property_name", "choices": ["choice1", "choice2"]}
    
    Returns a dict with keys: name, choices (list or None)
    """
    if isinstance(prop_def, str):
        return {'name': prop_def, 'choices': None}
    elif isinstance(prop_def, dict):
        return {
            'name': prop_def.get('name', ''),
            'choices': prop_def.get('choices', None)
        }
    raise TypeError(f"Property definition must be a string or dict, got {type(prop_def).__name__}")
```

### View Changes
Both `node_create()` and `node_edit()` views were updated to:
1. Parse property definitions using the helper function
2. Generate form field data with type='select' for properties with choices
3. Include the choices list in the field data for template rendering

### Template Changes
Both templates (`node_create_form.html` and `node_edit_form.html`) were updated to:
1. Check if a field has type='select'
2. Render a `<select>` dropdown instead of `<input>` for fields with choices
3. Populate the dropdown with all available choices
4. Handle required vs optional fields appropriately

## Backward Compatibility

The implementation is fully backward compatible:
- Existing type definitions using string property names continue to work unchanged
- No migration is required for existing data
- Feature packs can adopt choices gradually
- Mixed definitions (some properties with choices, some without) work correctly

## Best Practices

1. **Use meaningful choice values**: Choose clear, self-explanatory values like "active" instead of abbreviations like "act"

2. **Keep choice lists manageable**: Dropdown usability decreases with very long lists (>15-20 items). For longer lists, consider using autocomplete or search instead.

3. **Be consistent**: Use similar choice values across related types (e.g., use the same status values for all network equipment)

4. **Consider ordering**: List choices in logical order (e.g., by severity, frequency, or alphabetically)

5. **Document choices**: Consider adding comments in types.json to explain the meaning of each choice

## Migration Guide

To add choices to existing types:

1. **Identify properties with limited valid values**
   - Look for properties like status, priority, type, category, etc.
   - Review existing data to see what values are actually being used

2. **Update the types.json file**
   - Change property definitions from strings to objects with choices
   - Example: `"status"` → `{"name": "status", "choices": ["active", "inactive"]}`

3. **Test the forms**
   - Create new instances to verify dropdowns appear correctly
   - Edit existing instances to ensure current values are preserved

4. **Deploy the changes**
   - Changes take effect immediately (Django loads types.json dynamically)
   - No data migration or database changes are needed

## Common Use Cases

### Status Fields
```json
{"name": "status", "choices": ["active", "decommissioned", "staged", "maintenance"]}
```

### Priority Fields
```json
{"name": "priority", "choices": ["low", "medium", "high", "critical"]}
```

### Type/Category Fields
```json
{"name": "device_type", "choices": ["server", "switch", "router", "firewall", "load_balancer"]}
```

### Environment Fields
```json
{"name": "environment", "choices": ["production", "staging", "development", "test"]}
```

### Boolean-like Fields
```json
{"name": "approval_status", "choices": ["pending", "approved", "rejected"]}
```

## Troubleshooting

### Dropdown not appearing
- Verify the property definition syntax is correct in types.json
- Check that the JSON is valid (no syntax errors)
- Ensure the property name matches exactly (case-sensitive)

### Choices not showing in edit form
- Verify the property exists in the metadata
- Check that the view is correctly building the prop_choices_map
- Ensure templates are up to date

### Required field allows empty value
- In create forms, required fields should have `disabled selected` on the placeholder option
- This is enforced by HTML5 form validation

## Future Enhancements

Possible future improvements to this feature:

1. **Choice descriptions**: Add optional descriptions/tooltips for each choice
2. **Dynamic choices**: Load choices from the database instead of static definitions
3. **Dependent choices**: Make some choices available based on other field values
4. **Validation**: Enforce choices at the backend/database level
5. **Choice groups**: Support optgroups for categorizing choices in long lists
6. **Custom styling**: Allow feature packs to customize dropdown appearance
