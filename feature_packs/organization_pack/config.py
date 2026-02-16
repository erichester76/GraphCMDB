FEATURE_PACK_CONFIG = {
    'name': 'Organization Pack',
    'applies_to_labels': ['Person', 'Department', 'Site', 'Building'],
    'dependencies': [],
    'tabs': [
        {
            'id': 'person_details',
            'name': 'Organization Details',
            'template': 'person_details_tab.html',
            'custom_view': 'organization_pack.views.person_details_tab',
            'for_labels': ['Person']
        },
        {
            'id': 'department_details',
            'name': 'Organization Details',
            'template': 'department_details_tab.html',
            'custom_view': 'organization_pack.views.department_details_tab',
            'for_labels': ['Department']
        },
        {
            'id': 'site_details',
            'name': 'Organization Details',
            'template': 'site_details_tab.html',
            'custom_view': 'organization_pack.views.site_details_tab',
            'for_labels': ['Site']
        },
        {
            'id': 'building_details',
            'name': 'Organization Details',
            'template': 'building_details_tab.html',
            'custom_view': 'organization_pack.views.building_details_tab',
            'for_labels': ['Building']
        },
    ]
}
