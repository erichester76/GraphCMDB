FEATURE_PACK_CONFIG = {
    'name': 'Data Center Pack',
    'applies_to_labels': ['Rack_Unit', 'Rack', 'Row', 'Room'],
    'dependencies': ['inventory_pack', 'organization_pack'],
    'tabs': [
        {
            'id': 'rack_elevation',
            'name': 'Rack Elevation',
            'template': 'rack_elevation_tab.html',
            'custom_view': 'data_center_pack.views.rack_elevation_tab',  
            'for_labels': ['Rack'],
            'tab_order': 0  # Show first (before Core Details)
        },
        {
            'id': 'row_racks',
            'name': 'Row Racks',
            'template': 'row_racks_tab.html',
            'custom_view': 'data_center_pack.views.row_racks_tab',
            'for_labels': ['Row'],
            'tab_order': 0  # Show first (before Core Details)
        },
        {
            'id': 'room_overview',
            'name': 'Room Overview',
            'template': 'room_racks_tab.html',
            'custom_view': 'data_center_pack.views.room_racks_tab',
            'for_labels': ['Room'],
            'tab_order': 2  # Show after Core Details
        },
    ]
}