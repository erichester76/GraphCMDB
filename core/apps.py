# core/apps.py
from django.apps import AppConfig, apps
from django.conf import settings
from django.core.signals import request_started
from django.db.models.signals import post_migrate
from django.dispatch import receiver
import os
import importlib.util
import json
from cmdb.registry import TypeRegistry
from cmdb.audit_hooks import register_audit_hook
from django.urls import path, include
import sys


def reload_feature_packs():
    feature_packs_dir = os.path.join(settings.BASE_DIR, 'feature_packs')

    TypeRegistry.clear()
    settings.FEATURE_PACK_TABS = []
    settings.FEATURE_PACK_MODALS = []
    settings.FEATURE_PACK_URLS = []

    existing_dirs = settings.TEMPLATES[0]['DIRS']
    settings.TEMPLATES[0]['DIRS'] = [
        directory for directory in existing_dirs
        if not str(directory).startswith(feature_packs_dir)
    ]

    core_app = apps.get_app_config('core')
    core_app.load_feature_packs()

class CoreConfig(AppConfig):
    name = 'core'
    _permissions_synced = False

    def ready(self):
        self.load_feature_packs()
        request_started.connect(self._sync_permissions_once, dispatch_uid='core.sync_permissions_once')
        post_migrate.connect(self._sync_permissions_once, dispatch_uid='core.sync_permissions_post_migrate')

    def _sync_permissions_once(self, **kwargs):
        if self._permissions_synced:
            return
        try:
            from cmdb.permissions import sync_all_node_type_permissions
            print(f"[DEBUG] Syncing permissions for node types...")
            sync_all_node_type_permissions()
            self._permissions_synced = True
        except Exception as e:
            print(f"[DEBUG] Could not sync permissions (database may not be ready): {e}")

    def load_feature_packs(self):
        """
        Load feature packs from filesystem and sync to GraphDB.
        Also loads enabled packs from GraphDB on startup.
        """
        from cmdb.feature_pack_models import (
            sync_feature_pack_to_db, 
            should_sync_pack,
            FeaturePackNode,
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
        
        # Add feature_packs to path for imports (once, outside the loop)
        if feature_packs_dir not in sys.path:
            sys.path.insert(0, feature_packs_dir)
        
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

                # Register hooks if declared in config
                try:
                    hooks_config = config_data.get('hooks', {}) if config_data else {}
                    audit_hook_path = hooks_config.get('audit')
                    if audit_hook_path:
                        module_path, func_name = audit_hook_path.rsplit('.', 1)
                        hooks_module = importlib.import_module(module_path)
                        register_hooks = getattr(hooks_module, func_name, None)
                        if callable(register_hooks):
                            register_hooks(register_audit_hook)
                            print(f"[DEBUG] Registered audit hooks for {pack_name}")
                except Exception as e:
                    print(f"[DEBUG] Could not register hooks for {pack_name}: {e}")

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
                        TypeRegistry.register(label, metadata, pack_name=pack_name)
                        print(f"[DEBUG] Registered type: {label} from pack: {pack_name}")

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
                        # Store original for_labels for dynamic expansion
                        tab['original_for_labels'] = tab.get('for_labels', [])
                        settings.FEATURE_PACK_TABS.append(tab)
                        print(f"[DEBUG] Added tab: {tab.get('id', 'unknown')}")

                # Register modal overrides
                if config_data and 'modals' in config_data:
                    if not hasattr(settings, 'FEATURE_PACK_MODALS'):
                        settings.FEATURE_PACK_MODALS = []
                    for modal in config_data['modals']:
                        modal['pack_name'] = pack_name
                        modal['original_for_labels'] = modal.get('for_labels', [])
                        settings.FEATURE_PACK_MODALS.append(modal)
                        print(f"[DEBUG] Added modal override: {modal.get('type', 'unknown')}")

                # Register URLs
                if config_data and 'urls' in config_data:
                    if not hasattr(settings, 'FEATURE_PACK_URLS'):
                        settings.FEATURE_PACK_URLS = []
                    urls_config = config_data.get('urls')
                    if isinstance(urls_config, dict):
                        urls_config = [urls_config]
                    if isinstance(urls_config, list):
                        for entry in urls_config:
                            if isinstance(entry, str):
                                settings.FEATURE_PACK_URLS.append({'prefix': '', 'module': entry})
                            elif isinstance(entry, dict):
                                module = entry.get('module')
                                if module:
                                    settings.FEATURE_PACK_URLS.append({
                                        'prefix': entry.get('prefix', ''),
                                        'module': module
                                    })
        
        print(f"[DEBUG] Feature pack loading complete")

        try:
            from cmdb.feature_pack_urls import refresh_feature_pack_urls
            refresh_feature_pack_urls()
        except Exception as e:
            print(f"[DEBUG] Could not refresh feature pack URLs: {e}")
