FEATURE_PACK_CONFIG = {
    'name': 'Vendor Management Pack',
    'applies_to_labels': ['Vendor', 'Contract'],
    'dependencies': ['organization_pack'],
    'tabs': [
        {
            'id': 'vendor_details',
            'name': 'Vendor Details',
            'template': 'vendor_details_tab.html',
            'custom_view': 'vendor_management_pack.views.vendor_details_tab',
            'for_labels': ['Vendor']
        },
        {
            'id': 'contract_details',
            'name': 'Contract Details',
            'template': 'contract_details_tab.html',
            'custom_view': 'vendor_management_pack.views.contract_details_tab',
            'for_labels': ['Contract']
        },
    ]
}
