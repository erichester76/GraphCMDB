from django.urls import path
from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required, user_passes_test

def is_staff_user(user):
    return user.is_staff

@login_required
@user_passes_test(is_staff_user)
def feature_pack_store_detail(request, pack_name):
    """
    Show detailed information about a feature pack from the store (not installed).
    """
    store_dir = get_feature_pack_store_dir()
    pack_path = os.path.join(store_dir, pack_name)
    config = load_pack_config_from_path(pack_path, pack_name)
    types_data = load_pack_types_from_path(pack_path)
    type_info = []
    for label, metadata in (types_data or {}).items():
        type_info.append({
            'label': label,
            'enabled': False,
            'metadata': metadata,
        })
    context = {
        'pack': {
            'name': pack_name,
            'display_name': config.get('name', pack_name),
            'enabled': False,
            'path': pack_path,
            'last_modified': None,
            'last_synced': None,
            'config': config,
            'types': type_info,
        }
    }
    return render(request, 'feature_packs/store_detail.html', context)
# cmdb/feature_pack_views.py
"""
Views for managing feature packs - enabling/disabling and viewing status.
"""
from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.conf import settings
from cmdb.feature_pack_models import FeaturePackNode
from cmdb.registry import TypeRegistry
from core.apps import reload_feature_packs
import json
import importlib.util
import os
import shutil
import subprocess


def is_staff_user(user):
    """Check if user is staff (required for feature pack management)."""
    return user.is_staff


def load_pack_config_from_path(pack_path, pack_name):
    if not pack_path:
        return {}

    config_path = os.path.join(pack_path, 'config.py')
    if not os.path.exists(config_path):
        return {}

    spec = importlib.util.spec_from_file_location(f"{pack_name}.config_view", config_path)
    if not spec or not spec.loader:
        return {}

    config_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(config_module)
    return getattr(config_module, 'FEATURE_PACK_CONFIG', {}) or {}


def load_pack_types_from_path(pack_path):
    types_path = os.path.join(pack_path, 'types.json')
    if not os.path.exists(types_path):
        return {}
    with open(types_path, 'r') as handle:
        return json.load(handle)


def get_feature_packs_dir():
    return getattr(settings, 'FEATURE_PACKS_DIR', settings.BASE_DIR / 'feature_packs')


def get_feature_pack_store_dir():
    return getattr(settings, 'FEATURE_PACK_STORE_DIR', settings.BASE_DIR / 'feature_packs_store')


def get_feature_pack_store_repo():
    return getattr(settings, 'FEATURE_PACK_STORE_REPO', "")


def get_feature_pack_store_branch():
    return getattr(settings, 'FEATURE_PACK_STORE_BRANCH', "main")


def ensure_store_repo():
    repo_url = get_feature_pack_store_repo()
    store_dir = get_feature_pack_store_dir()
    if not repo_url:
        return False, 'FEATURE_PACK_STORE_REPO is not set.'

    store_dir = str(store_dir)
    if not os.path.exists(store_dir):
        os.makedirs(store_dir, exist_ok=True)

    git_dir = os.path.join(store_dir, '.git')
    if not os.path.exists(git_dir):
        clone_result = subprocess.run(
            ["git", "clone", repo_url, store_dir],
            check=False,
            capture_output=True,
            text=True,
        )
        if clone_result.returncode != 0:
            return False, (clone_result.stderr or clone_result.stdout or 'Git clone failed.')
        return True, 'Store repo cloned.'

    fetch_result = subprocess.run(
        ["git", "-C", store_dir, "fetch", "--all", "--prune"],
        check=False,
        capture_output=True,
        text=True,
    )
    checkout_result = subprocess.run(
        ["git", "-C", store_dir, "checkout", get_feature_pack_store_branch()],
        check=False,
        capture_output=True,
        text=True,
    )
    pull_result = subprocess.run(
        ["git", "-C", store_dir, "pull"],
        check=False,
        capture_output=True,
        text=True,
    )
    if fetch_result.returncode != 0:
        return False, (fetch_result.stderr or fetch_result.stdout or 'Git fetch failed.')
    if checkout_result.returncode != 0:
        return False, (checkout_result.stderr or checkout_result.stdout or 'Git checkout failed.')
    if pull_result.returncode != 0:
        return False, (pull_result.stderr or pull_result.stdout or 'Git pull failed.')
    return True, 'Store repo updated.'


def get_pack_config(pack):
    config = pack.config or {}
    if not isinstance(config, dict):
        config = {}

    if config.get('dependencies') is None:
        file_config = load_pack_config_from_path(pack.path, pack.name)
        if file_config:
            merged = dict(config)
            for key, value in file_config.items():
                if key not in merged or merged.get(key) in (None, '', [], {}):
                    merged[key] = value
            return merged

    return config


def normalize_dependencies(config: dict) -> list:
    dependencies = config.get('dependencies') if isinstance(config, dict) else None
    if not dependencies:
        return []
    if isinstance(dependencies, str):
        dependencies = [dependencies]
    if not isinstance(dependencies, (list, tuple, set)):
        return []
    normalized = []
    for dependency in dependencies:
        if isinstance(dependency, str):
            dep = dependency.strip()
            if dep:
                normalized.append(dep)
    return normalized


def get_dependency_status() -> dict:
    packs = FeaturePackNode.get_all_packs()
    return {pack.name: pack.enabled for pack in packs}


@login_required
@user_passes_test(is_staff_user)
def feature_pack_list(request):
    """
    Display all feature packs with their status (enabled/disabled).
    """
    try:
        ensure_store_repo()
        packs = FeaturePackNode.get_all_packs()
        store_dir = get_feature_pack_store_dir()
        store_packs = []
        if os.path.exists(store_dir):
            store_packs = sorted(
                entry for entry in os.listdir(store_dir)
                if os.path.isdir(os.path.join(store_dir, entry))
                and not entry.startswith('.')
            )
        
        pack_info = []
        store_versions = {}
        for store_pack_name in store_packs:
            store_pack_path = os.path.join(store_dir, store_pack_name)
            store_config = load_pack_config_from_path(store_pack_path, store_pack_name)
            store_versions[store_pack_name] = store_config.get('version', '0.0.0')

        for pack in packs:
            types = TypeRegistry.get_types_for_pack(pack.name)
            installed_version = getattr(pack, 'version', '0.0.0')
            store_version = store_versions.get(pack.name, '0.0.0')
            def parse_version(v):
                return tuple(int(x) for x in v.split('.'))
            upgrade_available = parse_version(store_version) > parse_version(installed_version)
            pack_info.append({
                'name': pack.name,
                'display_name': pack.display_name,
                'enabled': pack.enabled,
                'path': pack.path,
                'last_modified': pack.last_modified.isoformat() if pack.last_modified else None,
                'last_synced': pack.last_synced.isoformat() if pack.last_synced else None,
                'type_count': len(types),
                'types': types,
                'config': get_pack_config(pack),
                'installed_version': installed_version,
                'store_version': store_version,
                'upgrade_available': upgrade_available,
            })

        installed_names = {pack['name'] for pack in pack_info}
        available_store_packs = store_packs

        context = {
            'packs': pack_info,
            'total_packs': len(pack_info),
            'enabled_packs': sum(1 for p in pack_info if p['enabled']),
            'disabled_packs': sum(1 for p in pack_info if not p['enabled']),
            'store_packs': store_packs,
            'available_store_packs': available_store_packs,
            'installed_store_packs': installed_names,
            'store_versions': store_versions,
        }
        
        return render(request, 'feature_packs/list.html', context)
    except Exception as e:
        return render(request, 'feature_packs/list.html', {
            'error': str(e),
            'packs': [],
            'total_packs': 0,
            'enabled_packs': 0,
            'disabled_packs': 0,
        })


@login_required
@user_passes_test(is_staff_user)
@require_http_methods(["POST"])
def feature_pack_enable(request, pack_name):
    """
    Enable a feature pack.
    """
    try:
        pack = FeaturePackNode.nodes.get_or_none(name=pack_name)
        if not pack:
            return JsonResponse({
                'success': False,
                'error': f'Feature pack "{pack_name}" not found'
            }, status=404)
        
        pack.enable()
        
        return JsonResponse({
            'success': True,
            'message': f'Feature pack "{pack.display_name}" enabled successfully',
            'pack_name': pack_name,
            'enabled': True,
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_http_methods(["POST"])
def feature_pack_disable(request, pack_name):
    """
    Disable a feature pack.
    """
    try:
        pack = FeaturePackNode.nodes.get_or_none(name=pack_name)
        if not pack:
            return JsonResponse({
                'success': False,
                'error': f'Feature pack "{pack_name}" not found'
            }, status=404)

        # Check for installed packs that depend on this pack
        installed_packs = FeaturePackNode.get_all_packs()
        dependents = []
        for other_pack in installed_packs:
            config = other_pack.config or {}
            dependencies = config.get('dependencies', [])
            if isinstance(dependencies, str):
                dependencies = [dependencies]
            if pack_name in dependencies and other_pack.enabled:
                dependents.append(other_pack.display_name or other_pack.name)

        if dependents:
            return JsonResponse({
                'success': False,
                'error': f'Cannot disable "{pack_name}" because these enabled packs depend on it: {", ".join(dependents)}',
                'pack_name': pack_name,
                'enabled': True,
            }, status=400)

        pack.disable()

        return JsonResponse({
            'success': True,
            'message': f'Feature pack "{pack.display_name}" disabled successfully',
            'pack_name': pack_name,
            'enabled': False,
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@user_passes_test(is_staff_user)
@require_http_methods(["POST"])
def feature_pack_add(request):
    pack_name = request.POST.get('pack_name')
    if not pack_name:
        messages.error(request, 'Select a feature pack to add.')
        return redirect('cmdb:feature_pack_list')

    ensure_store_repo()
    store_dir = get_feature_pack_store_dir()
    packs_dir = get_feature_packs_dir()
    source_path = os.path.join(store_dir, pack_name)
    dest_path = os.path.join(packs_dir, pack_name)

    if not os.path.exists(source_path):
        messages.error(request, f'Feature pack "{pack_name}" not found in the store.')
        return redirect('cmdb:feature_pack_list')

    if os.path.exists(dest_path):
        # Check version for upgrade
        installed_config = load_pack_config_from_path(dest_path, pack_name)
        store_config = load_pack_config_from_path(source_path, pack_name)
        installed_version = installed_config.get('version', '0.0.0')
        store_version = store_config.get('version', '0.0.0')
        def parse_version(v):
            return tuple(int(x) for x in v.split('.'))
        if parse_version(store_version) > parse_version(installed_version):
            try:
                shutil.rmtree(dest_path)
                shutil.copytree(source_path, dest_path)
                config_data = load_pack_config_from_path(dest_path, pack_name)
                types_data = load_pack_types_from_path(dest_path)
                from cmdb.feature_pack_models import sync_feature_pack_to_db
                sync_feature_pack_to_db(
                    pack_name=pack_name,
                    pack_path=dest_path,
                    config=config_data,
                    types_data=types_data,
                )
                reload_feature_packs()
                messages.success(
                    request,
                    f'Feature pack "{pack_name}" upgraded to version {store_version}.'
                )
            except Exception as exc:
                messages.error(request, f'Error upgrading feature pack: {exc}')
            return redirect('cmdb:feature_pack_list')
        else:
            messages.warning(request, f'Feature pack "{pack_name}" is already installed and up to date.')
            return redirect('cmdb:feature_pack_list')

    config_data = load_pack_config_from_path(source_path, pack_name)
    dependencies = normalize_dependencies(config_data)
    if dependencies:
        dependency_status = get_dependency_status()
        missing = [dep for dep in dependencies if dep not in dependency_status]
        disabled = [dep for dep in dependencies if dep in dependency_status and not dependency_status[dep]]
        if missing or disabled:
            detail_parts = []
            if missing:
                detail_parts.append(f'missing: {", ".join(missing)}')
            if disabled:
                detail_parts.append(f'disabled: {", ".join(disabled)}')
            details = "; ".join(detail_parts)
            messages.error(
                request,
                f'Cannot install "{pack_name}" until dependencies are installed and enabled ({details}).'
            )
            return redirect('cmdb:feature_pack_list')

    try:
        shutil.copytree(source_path, dest_path)
        config_data = load_pack_config_from_path(dest_path, pack_name)
        types_data = load_pack_types_from_path(dest_path)
        from cmdb.feature_pack_models import sync_feature_pack_to_db
        sync_feature_pack_to_db(
            pack_name=pack_name,
            pack_path=dest_path,
            config=config_data,
            types_data=types_data,
        )
        reload_feature_packs()
        messages.success(
            request,
            f'Feature pack "{pack_name}" added and loaded.'
        )
    except Exception as exc:
        messages.error(request, f'Error adding feature pack: {exc}')

    return redirect('cmdb:feature_pack_list')


@login_required
@user_passes_test(is_staff_user)
@require_http_methods(["POST"])
def feature_pack_refresh_store(request):
    success, message = ensure_store_repo()
    if success:
        messages.success(request, message)
    else:
        messages.error(request, message)
    return redirect('cmdb:feature_pack_list')


@login_required
@user_passes_test(is_staff_user)
@require_http_methods(["POST"])
def feature_pack_delete(request, pack_name):
    packs_dir = get_feature_packs_dir()
    pack_path = os.path.join(packs_dir, pack_name)

    if not os.path.exists(pack_path):
        messages.error(request, f'Feature pack "{pack_name}" not found.')
        return redirect('cmdb:feature_pack_list')

    # Check for installed packs that depend on this pack
    from cmdb.feature_pack_models import FeaturePackNode
    installed_packs = FeaturePackNode.get_all_packs()
    dependents = []
    for pack in installed_packs:
        config = pack.config or {}
        dependencies = config.get('dependencies', [])
        if isinstance(dependencies, str):
            dependencies = [dependencies]
        if pack_name in dependencies:
            dependents.append(pack.display_name or pack.name)

    if dependents:
        messages.error(request, f'Cannot delete "{pack_name}" because these installed packs depend on it: {", ".join(dependents)}')
        return redirect('cmdb:feature_pack_list')

    try:
        shutil.rmtree(pack_path)
        pack_node = FeaturePackNode.nodes.get_or_none(name=pack_name)
        if pack_node:
            pack_node.delete()
        for label in TypeRegistry.get_types_for_pack(pack_name):
            TypeRegistry.unregister(label)
        reload_feature_packs()
        messages.success(
            request,
            f'Feature pack "{pack_name}" removed and unloaded.'
        )
    except Exception as exc:
        messages.error(request, f'Error removing feature pack: {exc}')

    return redirect('cmdb:feature_pack_list')


def feature_pack_detail(request, pack_name):
    """
    Show detailed information about a specific feature pack.
    """
    try:
        pack = FeaturePackNode.nodes.get_or_none(name=pack_name)
        if not pack:
            return render(request, 'feature_packs/detail.html', {
                'error': f'Feature pack "{pack_name}" not found',
            })
        
        # Get types for this pack from TypeRegistry
        type_labels = TypeRegistry.get_types_for_pack(pack.name)
        
        type_info = []
        for label in type_labels:
            metadata = TypeRegistry.get_metadata(label)
            type_info.append({
                'label': label,
                'enabled': pack.enabled,  # Types follow pack enable/disable state
                'metadata': metadata,
            })
        
        context = {
            'pack': {
                'name': pack.name,
                'display_name': pack.display_name,
                'enabled': pack.enabled,
                'path': pack.path,
                'last_modified': pack.last_modified,
                'last_synced': pack.last_synced,
                'config': get_pack_config(pack),
                'types': type_info,
            }
        }
        
        return render(request, 'feature_packs/detail.html', context)
    except Exception as e:
        return render(request, 'feature_packs/detail.html', {
            'error': str(e),
        })


@login_required
@user_passes_test(is_staff_user)
def feature_pack_status_api(request):
    """
    API endpoint to get feature pack status as JSON.
    """
    try:
        packs = FeaturePackNode.get_all_packs()
        
        pack_data = []
        for pack in packs:
            pack_data.append({
                'name': pack.name,
                'display_name': pack.display_name,
                'enabled': pack.enabled,
                'type_count': len(pack.types or []),
            })
        
        return JsonResponse({
            'success': True,
            'packs': pack_data,
            'total': len(pack_data),
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
