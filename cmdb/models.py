# cmdb/models.py
from neomodel import StructuredNode, JSONProperty, config
from django.conf import settings
from cmdb.registry import TypeRegistry

config.DATABASE_URL = settings.NEO4J_BOLT_URL

# Module-level registry (global, shared across all calls)
_LABEL_REGISTRY = {}

class DynamicNode(StructuredNode):
    __abstract_node__ = True
    custom_properties = JSONProperty(default=dict)

    @classmethod
    def get_or_create_label(cls, label_name: str):
        if label_name in _LABEL_REGISTRY:
            return _LABEL_REGISTRY[label_name]

        # Create dynamic subclass
        class_name = f"Dynamic{label_name}Node"
        attrs = {
            '__label__': label_name,
            '__module__': cls.__module__,
        }

        new_class = type(class_name, (cls,), attrs)

        # Optional: install labels (constraints/indexes)
        from neomodel import install_labels
        install_labels(new_class)

        _LABEL_REGISTRY[label_name] = new_class
        return new_class