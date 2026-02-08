# cmdb/registry.py
from typing import Dict, Any, List, Optional
import json
from pathlib import Path

class TypeRegistry:
    _types: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def register(cls, label: str, metadata: Dict[str, Any]):
        cls._types[label] = metadata

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
    def unregister(cls, label: str):
        cls._types.pop(label, None)

    @classmethod
    def clear(cls):
        cls._types.clear()


registry = TypeRegistry()

