# cmdb/models.py
from neomodel import StructuredNode, JSONProperty, config
from django.conf import settings
from cmdb.registry import TypeRegistry

config.DATABASE_URL = settings.NEO4J_BOLT_URL

class DynamicNode(StructuredNode):
    __abstract_node__ = True
    custom_properties = JSONProperty(default=dict)

    @classmethod
    def get_or_create_label(cls, label_name: str):
        if label_name in cls._label_registry:
            return cls._label_registry[label_name]

        attrs = {
            '__label__': label_name,
            '__module__': cls.__module__,
        }

        # Add all allowed relationships from registry at creation time
        meta = TypeRegistry.get_metadata(label_name)
        for rel_type, rel_info in meta.get('relationships', {}).items():
            if rel_info['direction'] == 'out':
                from neomodel import RelationshipTo
                attrs[rel_type] = RelationshipTo(rel_info['target'], rel_type)

        new_class = type(f"Dynamic{label_name}Node", (cls,), attrs)

        from neomodel import install_labels
        install_labels(new_class)

        cls._label_registry[label_name] = new_class
        return new_class

    _label_registry = {}  # class-level cache