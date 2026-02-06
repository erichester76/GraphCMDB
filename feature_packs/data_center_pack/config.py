FEATURE_PACK_CONFIG = {
    'name': 'Data Center Pack',
    'applies_to_labels': ['Rack', 'Row', 'Room'],
    'tabs': [
        {
            'id': 'rack_elevation',
            'name': 'Rack Elevation',
            'template': 'rack_elevation_tab.html',
            'custom_view': 'data_center_pack.views.rack_elevation_tab',  
            'for_labels': ['Rack']
        },
        {
            'id': 'row_racks',
            'name': 'Row Racks',
            'template': 'row_racks_tab.html',
            'custom_view': 'data_center_pack.views.row_racks_tab',
            'for_labels': ['Row']
        },
        {
            'id': 'room_overview',
            'name': 'Room Overview',
            'template': 'room_racks_tab.html',
            'custom_view': 'data_center_pack.views.room_racks_tab',
            'for_labels': ['Room']
        },
    ]
}