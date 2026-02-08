FEATURE_PACK_CONFIG = {
    'name': 'DNS Pack',
    'applies_to_labels': ['DNS_Zone', 'DNS_Record', 'DNS_View'],
    'tabs': [
        {
            'id': 'dns_zone_details',
            'name': 'DNS Details',
            'template': 'dns_zone_details_tab.html',
            'custom_view': 'dns_pack.views.dns_zone_details_tab',
            'for_labels': ['DNS_Zone']
        },
        {
            'id': 'dns_record_details',
            'name': 'DNS Details',
            'template': 'dns_record_details_tab.html',
            'custom_view': 'dns_pack.views.dns_record_details_tab',
            'for_labels': ['DNS_Record']
        },
        {
            'id': 'dns_view_details',
            'name': 'DNS Details',
            'template': 'dns_view_details_tab.html',
            'custom_view': 'dns_pack.views.dns_view_details_tab',
            'for_labels': ['DNS_View']
        },
    ]
}
