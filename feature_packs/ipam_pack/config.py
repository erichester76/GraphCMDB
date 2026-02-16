FEATURE_PACK_CONFIG = {
    'name': 'IPAM Pack',
    'applies_to_labels': ['Network', 'IP_Address', 'Mac_Address'],
    'dependencies': ['network_pack'],
    'tabs': [
        {
            'id': 'network_details',
            'name': 'IPAM Details',
            'template': 'network_details_tab.html',
            'custom_view': 'ipam_pack.views.network_details_tab',
            'for_labels': ['Network']
        },
        {
            'id': 'ip_address_details',
            'name': 'IPAM Details',
            'template': 'ip_address_details_tab.html',
            'custom_view': 'ipam_pack.views.ip_address_details_tab',
            'for_labels': ['IP_Address']
        },
        {
            'id': 'mac_address_details',
            'name': 'IPAM Details',
            'template': 'mac_address_details_tab.html',
            'custom_view': 'ipam_pack.views.mac_address_details_tab',
            'for_labels': ['Mac_Address']
        },
    ]
}
