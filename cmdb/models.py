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
    
    def get_outgoing_relationships(self):
        """
        Get all outgoing relationships from this node.
        Returns a dict where keys are relationship types and values are lists of related node info.
        
        Each related node info contains:
        - target_id: Neo4j element ID
        - target_label: Node label
        - target_name: Name extracted from custom_properties (or fallback)
        """
        if not hasattr(self, '__label__'):
            raise ValueError("Node must have a __label__ attribute")
        
        query = f"""
            MATCH (n:`{self.__label__}`) WHERE elementId(n) = $eid
            MATCH (n)-[r]->(m)
            WITH 
                type(r) AS rel_type,
                elementId(m) AS target_id,
                labels(m)[0] AS target_label,
                apoc.convert.fromJsonMap(m.custom_properties) AS props_map
            RETURN 
                rel_type,
                target_id,
                target_label,
                COALESCE(
                    props_map.name,
                    props_map[head(keys(props_map))]
                ) AS target_name
        """
        result, _ = db.cypher_query(query, {'eid': self.element_id})
        
        relationships = {}
        for row in result:
            rel_type = row[0]
            if rel_type not in relationships:
                relationships[rel_type] = []
            relationships[rel_type].append({
                'target_id': row[1],
                'target_label': row[2],
                'target_name': row[3] or row[1][:50] + '...',
            })
        
        return relationships
    
    def get_incoming_relationships(self):
        """
        Get all incoming relationships to this node.
        Returns a dict where keys are relationship types and values are lists of related node info.
        
        Each related node info contains:
        - source_id: Neo4j element ID
        - source_label: Node label
        - source_name: Name extracted from custom_properties (or fallback)
        """
        if not hasattr(self, '__label__'):
            raise ValueError("Node must have a __label__ attribute")
        
        query = f"""
            MATCH (n:`{self.__label__}`) WHERE elementId(n) = $eid
            MATCH (m)-[r]->(n)
            WITH 
                type(r) AS rel_type,
                elementId(m) AS source_id,
                labels(m)[0] AS source_label,
                apoc.convert.fromJsonMap(m.custom_properties) AS props_map
            RETURN 
                rel_type,
                source_id,
                source_label,
                COALESCE(
                    props_map.name,
                    props_map[head(keys(props_map))]
                ) AS source_name
        """
        result, _ = db.cypher_query(query, {'eid': self.element_id})
        
        relationships = {}
        for row in result:
            rel_type = row[0]
            if rel_type not in relationships:
                relationships[rel_type] = []
            relationships[rel_type].append({
                'source_id': row[1],
                'source_label': row[2],
                'source_name': row[3] or row[1][:50] + '...',
            })
        
        return relationships
    
    @classmethod
    def connect_nodes(cls, source_element_id: str, source_label: str, 
                     rel_type: str, target_element_id: str, target_label: str):
        """
        Create a relationship between two nodes identified by their element IDs.
        
        Args:
            source_element_id: Element ID of the source node
            source_label: Label of the source node
            rel_type: Type of relationship to create
            target_element_id: Element ID of the target node
            target_label: Label of the target node
            
        Returns:
            True if successful, False otherwise
        """
        # Validate relationship type follows Neo4j conventions
        if not re.match(r'^[A-Z_][A-Z0-9_]*$', rel_type):
            raise ValueError(
                f"Invalid relationship type: {rel_type}. "
                "Must be uppercase with underscores."
            )
        
        query = f"""
            MATCH (source:`{source_label}`) WHERE elementId(source) = $sid
            MATCH (target:`{target_label}`) WHERE elementId(target) = $tid
            MERGE (source)-[:`{rel_type}`]->(target)
            RETURN elementId(source) AS source_id
        """
        result, _ = db.cypher_query(query, {'sid': source_element_id, 'tid': target_element_id})
        return bool(result)
    
    @classmethod
    def disconnect_nodes(cls, source_element_id: str, source_label: str,
                        rel_type: str, target_element_id: str, target_label: str):
        """
        Remove a relationship between two nodes identified by their element IDs.
        
        Args:
            source_element_id: Element ID of the source node
            source_label: Label of the source node
            rel_type: Type of relationship to delete
            target_element_id: Element ID of the target node
            target_label: Label of the target node
            
        Returns:
            Number of relationships deleted (0 or 1)
        """
        query = f"""
            MATCH (source:`{source_label}`)-[r:`{rel_type}`]->(target:`{target_label}`)
            WHERE elementId(source) = $sid AND elementId(target) = $tid
            DELETE r
            RETURN count(r) AS deleted
        """
        result, _ = db.cypher_query(query, {'sid': source_element_id, 'tid': target_element_id})
        return result[0][0] if result else 0