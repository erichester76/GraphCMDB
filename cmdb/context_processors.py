from .registry import TypeRegistry

def categories_context(request):
    return {
        'categories': TypeRegistry.get_categories(),
    }