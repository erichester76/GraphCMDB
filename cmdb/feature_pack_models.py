# cmdb/feature_pack_models.py
"""
Models for storing feature pack and type registry information in GraphDB.
"""
from neomodel import (
    StructuredNode, StringProperty, JSONProperty, 
    DateTimeProperty, BooleanProperty, db
)
from datetime import datetime
from typing import Dict, List, Optional, Any
import os


class FeaturePackNode(StructuredNode):
    """
    Represents a feature pack stored in GraphDB.
    
    Attributes:
        name: The name of the feature pack (e.g., 'itsm_pack')
        display_name: Human-readable name
        enabled: Whether this feature pack is active
        path: Filesystem path to the feature pack
        last_modified: Last modification timestamp from filesystem
        last_synced: Last time this was synced to GraphDB
        config: Full configuration from config.py (FEATURE_PACK_CONFIG)
        types: List of type labels provided by this pack
    """
    name = StringProperty(unique_index=True, required=True)
    display_name = StringProperty()
    enabled = BooleanProperty(default=True)
    path = StringProperty()
    last_modified = DateTimeProperty()
    last_synced = DateTimeProperty(default_now=True)
    config = JSONProperty(default=dict)
    types = JSONProperty(default=list)  # List of type labels from types.json
    
    @classmethod
    def get_or_create_pack(cls, name: str, **kwargs) -> 'FeaturePackNode':
        """Get existing feature pack or create a new one."""
        existing = cls.nodes.get_or_none(name=name)
        if existing:
            # Update fields
            for key, value in kwargs.items():
                setattr(existing, key, value)
            existing.last_synced = datetime.now()
            existing.save()
            return existing
        else:
            # Create new
            pack = cls(name=name, **kwargs)
            pack.save()
            return pack
    
    @classmethod
    def get_all_packs(cls) -> List['FeaturePackNode']:
        """Get all feature packs from GraphDB."""
        return list(cls.nodes.all())
    
    @classmethod
    def get_enabled_packs(cls) -> List['FeaturePackNode']:
        """Get only enabled feature packs."""
        return list(cls.nodes.filter(enabled=True))
    
    def enable(self):
        """Enable this feature pack."""
        self.enabled = True
        self.save()
    
    def disable(self):
        """Disable this feature pack."""
        self.enabled = False
        self.save()


class TypeDefinitionNode(StructuredNode):
    """
    Represents a type definition from a feature pack's types.json.
    
    Attributes:
        label: The type label (e.g., 'Issue', 'Server')
        feature_pack_name: Name of the feature pack that provides this type
        metadata: Full type metadata (properties, relationships, etc.)
        enabled: Whether this type is active (inherits from feature pack)
        last_synced: Last time this was synced to GraphDB
    """
    label = StringProperty(unique_index=True, required=True)
    feature_pack_name = StringProperty(required=True)
    metadata = JSONProperty(default=dict)
    enabled = BooleanProperty(default=True)
    last_synced = DateTimeProperty(default_now=True)
    
    @classmethod
    def get_or_create_type(cls, label: str, feature_pack_name: str, 
                          metadata: Dict[str, Any]) -> 'TypeDefinitionNode':
        """Get existing type definition or create a new one."""
        existing = cls.nodes.get_or_none(label=label)
        if existing:
            # Update metadata
            existing.feature_pack_name = feature_pack_name
            existing.metadata = metadata
            existing.last_synced = datetime.now()
            existing.save()
            return existing
        else:
            # Create new
            type_def = cls(
                label=label,
                feature_pack_name=feature_pack_name,
                metadata=metadata
            )
            type_def.save()
            return type_def
    
    @classmethod
    def get_all_types(cls) -> List['TypeDefinitionNode']:
        """Get all type definitions from GraphDB."""
        return list(cls.nodes.all())
    
    @classmethod
    def get_enabled_types(cls) -> List['TypeDefinitionNode']:
        """Get only enabled type definitions."""
        return list(cls.nodes.filter(enabled=True))
    
    @classmethod
    def get_types_for_pack(cls, feature_pack_name: str) -> List['TypeDefinitionNode']:
        """Get all type definitions for a specific feature pack."""
        return list(cls.nodes.filter(feature_pack_name=feature_pack_name))


def sync_feature_pack_to_db(pack_name: str, pack_path: str, 
                            config: Optional[Dict] = None,
                            types_data: Optional[Dict] = None) -> FeaturePackNode:
    """
    Sync a feature pack from filesystem to GraphDB.
    
    Args:
        pack_name: Name of the feature pack
        pack_path: Filesystem path to the pack
        config: Configuration from config.py (FEATURE_PACK_CONFIG)
        types_data: Type definitions from types.json
    
    Returns:
        The created or updated FeaturePackNode
    """
    # Get last modified time of the directory
    last_modified = datetime.fromtimestamp(os.path.getmtime(pack_path))
    
    # Get or create feature pack node
    display_name = config.get('name', pack_name) if config else pack_name
    
    pack_node = FeaturePackNode.get_or_create_pack(
        name=pack_name,
        display_name=display_name,
        path=pack_path,
        last_modified=last_modified,
        config=config or {},
        types=list(types_data.keys()) if types_data else []
    )
    
    # Sync type definitions
    if types_data:
        for label, metadata in types_data.items():
            TypeDefinitionNode.get_or_create_type(
                label=label,
                feature_pack_name=pack_name,
                metadata=metadata
            )
    
    return pack_node


def load_feature_packs_from_db() -> Dict[str, Dict[str, Any]]:
    """
    Load all enabled feature packs from GraphDB.
    
    Returns:
        Dictionary with pack names as keys and pack data as values
    """
    enabled_packs = FeaturePackNode.get_enabled_packs()
    
    result = {}
    for pack in enabled_packs:
        result[pack.name] = {
            'display_name': pack.display_name,
            'path': pack.path,
            'config': pack.config,
            'types': pack.types,
            'last_modified': pack.last_modified,
        }
    
    return result


def should_sync_pack(pack_name: str, pack_path: str) -> bool:
    """
    Check if a feature pack needs to be synced based on modification time.
    
    Args:
        pack_name: Name of the feature pack
        pack_path: Filesystem path to the pack
    
    Returns:
        True if pack should be synced (new or modified), False otherwise
    """
    pack_node = FeaturePackNode.nodes.get_or_none(name=pack_name)
    
    if not pack_node:
        # Pack doesn't exist in DB, needs sync
        return True
    
    # Check if filesystem is newer than DB
    fs_mtime = datetime.fromtimestamp(os.path.getmtime(pack_path))
    
    if pack_node.last_modified is None:
        return True
    
    return fs_mtime > pack_node.last_modified
