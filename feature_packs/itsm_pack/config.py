FEATURE_PACK_CONFIG = {
    'name': 'ITSM Pack',
    'applies_to_labels': ['Issue', 'Problem', 'Change', 'Release', 'Event'],
    'dependencies': ['inventory_pack'],
    'tabs': [
        {
            'id': 'issue_details',
            'name': 'ITSM Details',
            'template': 'issue_details_tab.html',
            'custom_view': 'itsm_pack.views.issue_details_tab',  
            'for_labels': ['Issue']
        },
        {
            'id': 'problem_details',
            'name': 'ITSM Details',
            'template': 'problem_details_tab.html',
            'custom_view': 'itsm_pack.views.problem_details_tab',
            'for_labels': ['Problem']
        },
        {
            'id': 'change_details',
            'name': 'ITSM Details',
            'template': 'change_details_tab.html',
            'custom_view': 'itsm_pack.views.change_details_tab',
            'for_labels': ['Change']
        },
        {
            'id': 'release_details',
            'name': 'ITSM Details',
            'template': 'release_details_tab.html',
            'custom_view': 'itsm_pack.views.release_details_tab',
            'for_labels': ['Release']
        },
        {
            'id': 'event_details',
            'name': 'ITSM Details',
            'template': 'event_details_tab.html',
            'custom_view': 'itsm_pack.views.event_details_tab',
            'for_labels': ['Event']
        },
    ]
}
