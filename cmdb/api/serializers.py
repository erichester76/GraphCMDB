# cmdb/api/serializers.py
"""
Serializers for GraphCMDB REST API.
"""
from rest_framework import serializers


class NodeTypeSerializer(serializers.Serializer):
    """Serializer for node type metadata."""
    label = serializers.CharField()
    display_name = serializers.CharField()
    category = serializers.CharField()
    description = serializers.CharField()
    properties = serializers.ListField()
    required = serializers.ListField()
    relationships = serializers.DictField()


class NodePropertiesSerializer(serializers.Serializer):
    """Serializer for node properties (dynamic fields)."""
    def to_representation(self, instance):
        return instance or {}


class NodeSerializer(serializers.Serializer):
    """Serializer for node instances."""
    id = serializers.CharField(read_only=True)
    properties = NodePropertiesSerializer()
    
    def to_representation(self, instance):
        return {
            'id': instance.element_id,
            'properties': instance.custom_properties or {}
        }


class NodeDetailSerializer(serializers.Serializer):
    """Detailed serializer for node instances with relationships."""
    id = serializers.CharField(read_only=True)
    label = serializers.CharField(read_only=True)
    properties = NodePropertiesSerializer()
    relationships = serializers.DictField(read_only=True)
    
    def to_representation(self, instance):
        return {
            'id': instance.element_id,
            'label': instance.__label__,
            'properties': instance.custom_properties or {},
            'relationships': {
                'outgoing': instance.get_outgoing_relationships(),
                'incoming': instance.get_incoming_relationships()
            }
        }


class NodeCreateUpdateSerializer(serializers.Serializer):
    """Serializer for creating/updating nodes."""
    properties = serializers.DictField(required=True)


class RelationshipCreateSerializer(serializers.Serializer):
    """Serializer for creating relationships."""
    relationship_type = serializers.CharField(required=True)
    target_label = serializers.CharField(required=True)
    target_id = serializers.CharField(required=True)
