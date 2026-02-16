FEATURE_PACK_CONFIG = {
    'name': 'Virtualization Pack',
    'applies_to_labels': ['Virtual_Machine', 'Virtual_Host', 'Virtual_Cluster'],
    'dependencies': ['inventory_pack', 'organization_pack'],
    'tabs': [
        {
            'id': 'virtual_machine_details',
            'name': 'Virtualization Details',
            'template': 'virtual_machine_details_tab.html',
            'custom_view': 'virtualization_pack.views.virtual_machine_details_tab',
            'for_labels': ['Virtual_Machine']
        },
        {
            'id': 'virtual_host_details',
            'name': 'Virtualization Details',
            'template': 'virtual_host_details_tab.html',
            'custom_view': 'virtualization_pack.views.virtual_host_details_tab',
            'for_labels': ['Virtual_Host']
        },
        {
            'id': 'virtual_cluster_details',
            'name': 'Virtualization Details',
            'template': 'virtual_cluster_details_tab.html',
            'custom_view': 'virtualization_pack.views.virtual_cluster_details_tab',
            'for_labels': ['Virtual_Cluster']
        },
    ]
}
