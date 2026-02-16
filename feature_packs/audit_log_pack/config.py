FEATURE_PACK_CONFIG = {
    'name': 'Audit Log Pack',
    'applies_to_labels': 'all',  # Apply to all node types
    'dependencies': [],
    'tabs': [
        {
            'id': 'audit_log',
            'name': 'Audit Log',
            'template': 'audit_log_tab.html',
            'custom_view': 'audit_log_pack.views.audit_log_tab',
            'for_labels': [],  # Will be populated dynamically for all labels
            'tab_order': 100  # Always appear at the end
        }
    ]
}
