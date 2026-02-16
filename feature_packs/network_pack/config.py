FEATURE_PACK_CONFIG = {
    'name': 'Network Pack',
    'applies_to_labels': ['Interface', 'Cable', 'Circuit', 'VLAN'],
    'dependencies': ['inventory_pack', 'vendor_management_pack'],
    'tabs': [
        {
            'id': 'interface_details',
            'name': 'Network Details',
            'template': 'interface_details_tab.html',
            'custom_view': 'network_pack.views.interface_details_tab',
            'for_labels': ['Interface']
        },
        {
            'id': 'cable_details',
            'name': 'Network Details',
            'template': 'cable_details_tab.html',
            'custom_view': 'network_pack.views.cable_details_tab',
            'for_labels': ['Cable']
        },
        {
            'id': 'circuit_details',
            'name': 'Network Details',
            'template': 'circuit_details_tab.html',
            'custom_view': 'network_pack.views.circuit_details_tab',
            'for_labels': ['Circuit']
        },
        {
            'id': 'vlan_details',
            'name': 'Network Details',
            'template': 'vlan_details_tab.html',
            'custom_view': 'network_pack.views.vlan_details_tab',
            'for_labels': ['VLAN']
        },
    ]
}
