# cmdb/schema.py
import graphene
from graphene import (
    ObjectType, Mutation, String, ID, JSONString, Boolean, Field, List,
    Int, NonNull
)
from graphql import GraphQLError

from .models import DynamicNode
from .registry import TypeRegistry


# ────────────────────────────────────────────────────────────────
# Generic Node Type (same as before)
# ────────────────────────────────────────────────────────────────

class DynamicNodeType(ObjectType):
    id = ID()
    label = String()
    properties = JSONString()
    relationships = JSONString()  # placeholder – can be expanded

    @staticmethod
    def resolve_id(root, info):
        return str(root.id)

    @staticmethod
    def resolve_label(root, info):
        return root.__label__

    @staticmethod
    def resolve_properties(root, info):
        props = dict(root.__dict__)
        props.update(root.custom_properties or {})
        props.pop('_id', None)
        props.pop('__label__', None)
        return props

    @staticmethod
    def resolve_relationships(root, info):
        rels = {}
        for attr in dir(root):
            if attr.isupper() and not attr.startswith('_'):
                rel = getattr(root, attr)
                if hasattr(rel, 'all'):
                    targets = rel.all()
                    rels[attr] = [
                        {"id": str(t.id), "label": t.__label__} for t in targets
                    ]
        return rels


# ────────────────────────────────────────────────────────────────
# Generic Queries (unchanged from previous version)
# ────────────────────────────────────────────────────────────────

class Query(ObjectType):
    nodes_by_label = List(
        DynamicNodeType,
        label=String(required=True),
        limit=Int(default_value=50),
        skip=Int(default_value=0)
    )

    node_by_id = Field(
        DynamicNodeType,
        id=ID(required=True)
    )

    def resolve_nodes_by_label(root, info, label, limit, skip):
        try:
            node_class = DynamicNode.get_or_create_label(label)
            return node_class.nodes.all()[skip:skip + limit]
        except Exception as e:
            raise GraphQLError(f"Error fetching nodes for label '{label}': {str(e)}")

    def resolve_node_by_id(root, info, id):
        try:
            for label in TypeRegistry.known_labels():
                node_class = DynamicNode.get_or_create_label(label)
                try:
                    node = node_class.nodes.get(id=int(id))
                    if node:
                        return node
                except node_class.DoesNotExist:
                    continue
            return None
        except Exception as e:
            raise GraphQLError(f"Error fetching node {id}: {str(e)}")


# ────────────────────────────────────────────────────────────────
# Generic Node Mutations (create / update / delete – same as before)
# ────────────────────────────────────────────────────────────────

class CreateNode(Mutation):
    class Arguments:
        label = NonNull(String)
        properties = NonNull(JSONString)

    node = Field(DynamicNodeType)
    success = Boolean()
    message = String()

    def mutate(root, info, label, properties):
        try:
            meta = TypeRegistry.get_metadata(label)
            if meta and 'required' in meta:
                for req in meta['required']:
                    if req not in properties:
                        raise ValueError(f"Missing required property: {req}")

            node_class = DynamicNode.get_or_create_label(label)
            node = node_class(**properties).save()
            return CreateNode(node=node, success=True, message="Node created")
        except Exception as e:
            return CreateNode(node=None, success=False, message=str(e))


class UpdateNode(Mutation):
    class Arguments:
        id = NonNull(ID)
        properties = NonNull(JSONString)

    node = Field(DynamicNodeType)
    success = Boolean()
    message = String()

    def mutate(root, info, id, properties):
        try:
            found_node = None
            for label in TypeRegistry.known_labels():
                node_class = DynamicNode.get_or_create_label(label)
                try:
                    node = node_class.nodes.get(id=int(id))
                    found_node = node
                    break
                except node_class.DoesNotExist:
                    continue

            if not found_node:
                return UpdateNode(node=None, success=False, message="Node not found")

            if hasattr(found_node, 'custom_properties'):
                current = found_node.custom_properties or {}
                current.update(properties)
                found_node.custom_properties = current
            else:
                for k, v in properties.items():
                    if hasattr(found_node, k):
                        setattr(found_node, k, v)

            found_node.save()
            return UpdateNode(node=found_node, success=True, message="Node updated")
        except Exception as e:
            return UpdateNode(node=None, success=False, message=str(e))


class DeleteNode(Mutation):
    class Arguments:
        id = NonNull(ID)

    success = Boolean()
    message = String()

    def mutate(root, info, id):
        try:
            found = False
            for label in TypeRegistry.known_labels():
                node_class = DynamicNode.get_or_create_label(label)
                try:
                    node = node_class.nodes.get(id=int(id))
                    node.delete()
                    found = True
                    break
                except node_class.DoesNotExist:
                    continue
            if found:
                return DeleteNode(success=True, message="Node deleted")
            else:
                return DeleteNode(success=False, message="Node not found")
        except Exception as e:
            return DeleteNode(success=False, message=str(e))


# ────────────────────────────────────────────────────────────────
# Generic Relationship Mutations – NEW
# ────────────────────────────────────────────────────────────────

class ConnectNodes(Mutation):
    """
    Create a relationship between two existing nodes.
    Direction is always OUTGOING from source → target.
    """
    class Arguments:
        source_id    = NonNull(ID,   description="ID of the source node")
        source_label = NonNull(String, description="Label of the source node")
        rel_type     = NonNull(String, description="Relationship type (e.g. LOCATED_IN, DEPENDS_ON)")
        target_id    = NonNull(ID,   description="ID of the target node")
        target_label = NonNull(String, description="Label of the target node")
        properties   = JSONString(default_value={}, description="Optional relationship properties")

    success = Boolean()
    message = String()

    def mutate(root, info, source_id, source_label, rel_type, target_id, target_label, properties):
        try:
            # Get source node
            source_class = DynamicNode.get_or_create_label(source_label)
            source = source_class.nodes.get(id=int(source_id))

            # Get target node
            target_class = DynamicNode.get_or_create_label(target_label)
            target = target_class.nodes.get(id=int(target_id))

            # Dynamically get/create the relationship
            rel = getattr(source, rel_type, None)
            if rel is None:
                # Create relationship definition on the fly (neomodel allows this)
                from neomodel import RelationshipTo
                source_class.__dict__[rel_type] = RelationshipTo(target_label, rel_type)
                rel = getattr(source, rel_type)

            # Connect with optional properties
            rel.connect(target, properties or {})
            
            return ConnectNodes(success=True, message=f"Relationship {rel_type} created")
        except source_class.DoesNotExist:
            return ConnectNodes(success=False, message="Source node not found")
        except target_class.DoesNotExist:
            return ConnectNodes(success=False, message="Target node not found")
        except Exception as e:
            return ConnectNodes(success=False, message=str(e))


class DisconnectNodes(Mutation):
    """
    Remove a specific relationship between two nodes.
    """
    class Arguments:
        source_id    = NonNull(ID)
        source_label = NonNull(String)
        rel_type     = NonNull(String)
        target_id    = NonNull(ID)
        target_label = NonNull(String)

    success = Boolean()
    message = String()

    def mutate(root, info, source_id, source_label, rel_type, target_id, target_label):
        try:
            source_class = DynamicNode.get_or_create_label(source_label)
            source = source_class.nodes.get(id=int(source_id))

            target_class = DynamicNode.get_or_create_label(target_label)
            target = target_class.nodes.get(id=int(target_id))

            rel = getattr(source, rel_type, None)
            if rel is None:
                return DisconnectNodes(success=False, message=f"No such relationship type: {rel_type}")

            # Disconnect (removes the relationship if exists)
            disconnected = rel.disconnect(target)
            
            if disconnected:
                return DisconnectNodes(success=True, message=f"Relationship {rel_type} removed")
            else:
                return DisconnectNodes(success=False, message="Relationship did not exist")
        except Exception as e:
            return DisconnectNodes(success=False, message=str(e))


# ────────────────────────────────────────────────────────────────
# Root Mutation – add the new relationship operations
# ────────────────────────────────────────────────────────────────

class Mutation(ObjectType):
    create_node     = CreateNode.Field()
    update_node     = UpdateNode.Field()
    delete_node     = DeleteNode.Field()
    connect_nodes   = ConnectNodes.Field()
    disconnect_nodes = DisconnectNodes.Field()


# ────────────────────────────────────────────────────────────────
# Schema
# ────────────────────────────────────────────────────────────────

schema = graphene.Schema(
    query=Query,
    mutation=Mutation,
)