FEATURE_PACK_CONFIG = {
    'name': 'DHCP Pack',
    'applies_to_labels': ['DHCP_Scope', 'DHCP_Lease'],
    'dependencies': ['ipam_pack'],
    'tabs': [
        {
            'id': 'dhcp_scope_details',
            'name': 'DHCP Details',
            'template': 'dhcp_scope_details_tab.html',
            'custom_view': 'dhcp_pack.views.dhcp_scope_details_tab',
            'for_labels': ['DHCP_Scope']
        },
        {
            'id': 'dhcp_lease_details',
            'name': 'DHCP Details',
            'template': 'dhcp_lease_details_tab.html',
            'custom_view': 'dhcp_pack.views.dhcp_lease_details_tab',
            'for_labels': ['DHCP_Lease']
        },
    ]
}
