# cmdb/feature_pack_views.py
"""
Views for managing feature packs - enabling/disabling and viewing status.
"""
from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from cmdb.feature_pack_models import (
    FeaturePackNode, TypeDefinitionNode
)
import json


def feature_pack_list(request):
    """
    Display all feature packs with their status (enabled/disabled).
    """
    try:
        packs = FeaturePackNode.get_all_packs()
        
        pack_info = []
        for pack in packs:
            # Get types for this pack
            types = TypeDefinitionNode.get_types_for_pack(pack.name)
            
            pack_info.append({
                'name': pack.name,
                'display_name': pack.display_name,
                'enabled': pack.enabled,
                'path': pack.path,
                'last_modified': pack.last_modified.isoformat() if pack.last_modified else None,
                'last_synced': pack.last_synced.isoformat() if pack.last_synced else None,
                'type_count': len(types),
                'types': [t.label for t in types],
                'config': pack.config,
            })
        
        context = {
            'packs': pack_info,
            'total_packs': len(pack_info),
            'enabled_packs': sum(1 for p in pack_info if p['enabled']),
            'disabled_packs': sum(1 for p in pack_info if not p['enabled']),
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
        
        # Also enable all types from this pack
        types = TypeDefinitionNode.get_types_for_pack(pack_name)
        for type_def in types:
            type_def.enabled = True
            type_def.save()
        
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
        
        pack.disable()
        
        # Also disable all types from this pack
        types = TypeDefinitionNode.get_types_for_pack(pack_name)
        for type_def in types:
            type_def.enabled = False
            type_def.save()
        
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
        
        # Get types for this pack
        types = TypeDefinitionNode.get_types_for_pack(pack.name)
        
        type_info = []
        for type_def in types:
            type_info.append({
                'label': type_def.label,
                'enabled': type_def.enabled,
                'metadata': type_def.metadata,
            })
        
        context = {
            'pack': {
                'name': pack.name,
                'display_name': pack.display_name,
                'enabled': pack.enabled,
                'path': pack.path,
                'last_modified': pack.last_modified,
                'last_synced': pack.last_synced,
                'config': pack.config,
                'types': type_info,
            }
        }
        
        return render(request, 'feature_packs/detail.html', context)
    except Exception as e:
        return render(request, 'feature_packs/detail.html', {
            'error': str(e),
        })


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
