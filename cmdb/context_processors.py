from .registry import TypeRegistry

def categories_context(request):
    categories_metadata = {}
    for label in TypeRegistry.known_labels():
        metadata = TypeRegistry.get_metadata(label)
        categories_metadata[label] = metadata
    
    return {
        'categories': TypeRegistry.get_categories(),
        'categories_metadata': categories_metadata,
    }