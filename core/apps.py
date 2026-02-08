# core/apps.py
from django.apps import AppConfig
from django.conf import settings
import os
import importlib.util
import json
from cmdb.registry import TypeRegistry
from django.urls import path, include
import sys

class CoreConfig(AppConfig):
    name = 'core'

    def ready(self):
        self.load_feature_packs()

    def load_feature_packs(self):
        feature_packs_dir = os.path.join(settings.BASE_DIR, 'feature_packs')
        print(f"[DEBUG] Looking for feature packs in: {feature_packs_dir}")
        
        if not os.path.exists(feature_packs_dir):
            print(f"[DEBUG] Feature packs directory does not exist")
            return

        print(f"[DEBUG] Loading feature packs...")
        for pack_name in os.listdir(feature_packs_dir):
            pack_path = os.path.join(feature_packs_dir, pack_name)
            if os.path.isdir(pack_path):
                print(f"[DEBUG] Processing pack: {pack_name}")
                
                # Load types.json
                types_json_path = os.path.join(pack_path, 'types.json')
                if os.path.exists(types_json_path):
                    print(f"[DEBUG] Loading types.json for {pack_name}")
                    with open(types_json_path, 'r') as f:
                        types_data = json.load(f)
                        for label, metadata in types_data.items():
                            TypeRegistry.register(label, metadata)

                # Add template dir
                template_dir = os.path.join(pack_path, 'templates')
                if os.path.exists(template_dir):
                    print(f"[DEBUG] Adding template dir {template_dir} for {pack_name}")
                    settings.TEMPLATES[0]['DIRS'].append(template_dir)

                # Load config.py
                config_path = os.path.join(pack_path, 'config.py')
                if os.path.exists(config_path):
                    print(f"[DEBUG] Loading config.py for {pack_name}")
                    spec = importlib.util.spec_from_file_location(f"{pack_name}.config", config_path)
                    config_module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(config_module)
                    if not hasattr(settings, 'FEATURE_PACK_TABS'):
                        settings.FEATURE_PACK_TABS = []
                    for tab in config_module.FEATURE_PACK_CONFIG['tabs']:
                        tab['pack_name'] = pack_name
                        # Store original for_labels for dynamic expansion
                        tab['original_for_labels'] = tab.get('for_labels', [])
                        settings.FEATURE_PACK_TABS.append(tab)
                        print(f"[DEBUG] Added tab: {tab}")
            
                feature_packs_dir = os.path.join(settings.BASE_DIR, 'feature_packs')
                if feature_packs_dir not in sys.path:
                    sys.path.insert(0, feature_packs_dir)
        
        print(f"[DEBUG] Feature pack loading complete")
