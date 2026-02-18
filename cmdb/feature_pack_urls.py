import importlib
from django.conf import settings
from django.urls import clear_url_caches, include, path

urlpatterns = []


def refresh_feature_pack_urls():
    global urlpatterns
    new_patterns = []
    for item in getattr(settings, 'FEATURE_PACK_URLS', []):
        module = item.get('module') if isinstance(item, dict) else None
        prefix = item.get('prefix', '') if isinstance(item, dict) else ''
        if not module:
            continue

        try:
            urls_module = importlib.import_module(module)
            app_name = getattr(urls_module, 'app_name', None)
        except Exception:
            urls_module = None
            app_name = None

        if urls_module is None:
            continue

        new_patterns.append(path(prefix, include(urls_module.urlpatterns)))

    urlpatterns = new_patterns
    clear_url_caches()


refresh_feature_pack_urls()
