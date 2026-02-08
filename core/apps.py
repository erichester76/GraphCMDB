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
        """
        Load feature packs from filesystem and sync to GraphDB.
        Also loads enabled packs from GraphDB on startup.
        """
        from cmdb.feature_pack_models import (
            sync_feature_pack_to_db, 
            should_sync_pack,
            FeaturePackNode,
            TypeDefinitionNode
        )
        
        feature_packs_dir = os.path.join(settings.BASE_DIR, 'feature_packs')
        print(f"[DEBUG] Looking for feature packs in: {feature_packs_dir}")
        
        if not os.path.exists(feature_packs_dir):
            print(f"[DEBUG] Feature packs directory does not exist")
            return

        # First, load from GraphDB to see what's enabled
        print(f"[DEBUG] Loading enabled packs from GraphDB...")
        enabled_packs_from_db = set()
        try:
            for pack in FeaturePackNode.get_enabled_packs():
                enabled_packs_from_db.add(pack.name)
                print(f"[DEBUG] Pack '{pack.name}' is enabled in GraphDB")
        except Exception as e:
            print(f"[DEBUG] Could not load from GraphDB (first run?): {e}")
            enabled_packs_from_db = None  # First run, enable all by default

        print(f"[DEBUG] Scanning filesystem for feature packs...")
        for pack_name in os.listdir(feature_packs_dir):
            pack_path = os.path.join(feature_packs_dir, pack_name)
            if os.path.isdir(pack_path):
                print(f"[DEBUG] Processing pack: {pack_name}")
                
                # Check if this pack should be synced to DB
                try:
                    needs_sync = should_sync_pack(pack_name, pack_path)
                except Exception as e:
                    print(f"[DEBUG] Error checking sync status: {e}, assuming sync needed")
                    needs_sync = True
                
                # Load types.json
                types_data = None
                types_json_path = os.path.join(pack_path, 'types.json')
                if os.path.exists(types_json_path):
                    print(f"[DEBUG] Loading types.json for {pack_name}")
                    with open(types_json_path, 'r') as f:
                        types_data = json.load(f)

                # Load config.py
                config_data = None
                config_path = os.path.join(pack_path, 'config.py')
                if os.path.exists(config_path):
                    print(f"[DEBUG] Loading config.py for {pack_name}")
                    spec = importlib.util.spec_from_file_location(f"{pack_name}.config", config_path)
                    config_module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(config_module)
                    config_data = config_module.FEATURE_PACK_CONFIG

                # Sync to GraphDB if needed
                if needs_sync:
                    try:
                        print(f"[DEBUG] Syncing {pack_name} to GraphDB...")
                        sync_feature_pack_to_db(
                            pack_name=pack_name,
                            pack_path=pack_path,
                            config=config_data,
                            types_data=types_data
                        )
                        print(f"[DEBUG] Successfully synced {pack_name} to GraphDB")
                    except Exception as e:
                        print(f"[DEBUG] Error syncing {pack_name} to GraphDB: {e}")

                # Check if pack is enabled
                pack_enabled = True
                if enabled_packs_from_db is not None:
                    # Use DB state
                    pack_enabled = pack_name in enabled_packs_from_db
                else:
                    # First run, enable all
                    pack_enabled = True

                if not pack_enabled:
                    print(f"[DEBUG] Pack {pack_name} is disabled, skipping activation")
                    continue

                # Register types
                if types_data:
                    for label, metadata in types_data.items():
                        TypeRegistry.register(label, metadata)
                        print(f"[DEBUG] Registered type: {label}")

                # Add template dir
                template_dir = os.path.join(pack_path, 'templates')
                if os.path.exists(template_dir):
                    print(f"[DEBUG] Adding template dir {template_dir} for {pack_name}")
                    settings.TEMPLATES[0]['DIRS'].append(template_dir)

                # Register tabs
                if config_data and 'tabs' in config_data:
                    if not hasattr(settings, 'FEATURE_PACK_TABS'):
                        settings.FEATURE_PACK_TABS = []
                    for tab in config_data['tabs']:
                        tab['pack_name'] = pack_name
                        settings.FEATURE_PACK_TABS.append(tab)
                        print(f"[DEBUG] Added tab: {tab.get('id', 'unknown')}")
            
                # Add feature_packs to path for imports
                if feature_packs_dir not in sys.path:
                    sys.path.insert(0, feature_packs_dir)
        
        print(f"[DEBUG] Feature pack loading complete")
