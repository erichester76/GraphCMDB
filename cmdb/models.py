# cmdb/models.py
from neomodel import StructuredNode, JSONProperty, config, db
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

        _LABEL_REGISTRY[label_name] = new_class
        return new_class
    
    @classmethod
    def get_by_element_id(cls, element_id: str):
        """
        Retrieve a node by its Neo4j element ID.
        Returns the inflated node or None if not found.
        """
        query = f"""
            MATCH (n:`{cls.__label__}`)
            WHERE elementId(n) = $eid
            RETURN n
        """
        result, _ = db.cypher_query(query, {'eid': element_id})
        if not result:
            return None
        
        raw_node = result[0][0]
        return cls.inflate(raw_node)