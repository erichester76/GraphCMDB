# cmdb/models.py
import re  # Used for label validation in get_or_create_label()
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

        # Validate label name follows Neo4j conventions
        # Must start with letter/underscore, followed by alphanumeric/underscore
        # This prevents potential injection and ensures valid Neo4j labels
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', label_name):
            raise ValueError(
                f"Invalid label name: {label_name}. "
                "Must start with a letter or underscore, followed by alphanumeric characters or underscores."
            )

        # Create dynamic subclass
        class_name = f"Dynamic{label_name}Node"
        attrs = {
            '__label__': label_name,
            '__module__': cls.__module__,
        }

        new_class = type(class_name, (cls,), attrs)

        _LABEL_REGISTRY[label_name] = new_class
        return new_class
    
    def get_property(self, key: str, default=None):
        """
        Safely retrieve a property from custom_properties with null handling.
        Returns the property value or the provided default if not found or if custom_properties is None.
        """
        return (self.custom_properties or {}).get(key, default)
    
    @classmethod
    def get_by_element_id(cls, element_id: str):
        """
        Retrieve a node by its Neo4j element ID.
        Returns the inflated node or None if not found.
        
        Note: The label is safely obtained from cls.__label__ which is set
        during class creation via get_or_create_label() and comes from
        TypeRegistry (application-controlled, not user input).
        """
        # Validate label exists (defensive check)
        if not hasattr(cls, '__label__') or not cls.__label__:
            raise ValueError("Class must have a valid __label__ attribute")
        
        # Label is parameterized as part of the node pattern for Neo4j
        # Element ID is properly parameterized to prevent injection
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