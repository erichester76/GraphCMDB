# cmdb/registry.py
from typing import Dict, Any, List, Optional

class TypeRegistry:
    _types: Dict[str, Dict[str, Any]] = {}
    _pack_mapping: Dict[str, str] = {}  # Maps type label to pack name

    @classmethod
    def register(cls, label: str, metadata: Dict[str, Any], pack_name: Optional[str] = None):
        """Register a type with its metadata and optionally track which pack it came from."""
        cls._types[label] = metadata
        if pack_name:
            cls._pack_mapping[label] = pack_name

    @classmethod
    def get_metadata(cls, label: str) -> Dict[str, Any]:
        metadata = cls._types.get(label, {
            'display_name': label,
            'description': 'No description',
            'required': [],
            'properties': [],
            'relationships': {},
            'columns': [],
        })
        # If no columns specified, use first 5 properties as default
        if 'columns' not in metadata or not metadata['columns']:
            properties = metadata.get('properties', [])
            metadata['columns'] = properties[:5] if properties else []
        return metadata

    @classmethod
    def get_categories(cls):
        categories = {}
        for label in cls.known_labels():
            meta = cls.get_metadata(label)
            cat = meta.get('category', 'Uncategorized')
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(label)
        return categories  # dict: category → list of labels

    @classmethod
    def known_labels(cls) -> List[str]:
        return sorted(cls._types.keys())  # sort for consistent UI
    
    @classmethod
    def get_types_for_pack(cls, pack_name: str) -> List[str]:
        """Get all type labels that belong to a specific feature pack."""
        return [label for label, pack in cls._pack_mapping.items() if pack == pack_name]
    
    @classmethod
    def get_pack_for_type(cls, label: str) -> Optional[str]:
        """Get the pack name for a specific type label."""
        return cls._pack_mapping.get(label)

    @classmethod
    def unregister(cls, label: str):
        cls._types.pop(label, None)
        cls._pack_mapping.pop(label, None)

    @classmethod
    def clear(cls):
        cls._types.clear()
        cls._pack_mapping.clear()


registry = TypeRegistry()

