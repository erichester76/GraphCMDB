# cmdb/registry.py
from typing import Dict, Any, List, Optional
import json
from pathlib import Path

REGISTRY_FILE = Path(__file__).parent / 'registry_data.json'  # cmdb/registry_data.json

class TypeRegistry:
    _types: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def register(cls, label: str, metadata: Dict[str, Any]):
        cls._types[label] = metadata
        try:
            with open(REGISTRY_FILE, 'w') as f:
                json.dump(cls._types, f, indent=2)
            print(f"Saved registry to {REGISTRY_FILE}")
        except Exception as e:
            print(f"Failed to save registry: {e}")

    @classmethod
    def get_metadata(cls, label: str) -> Dict[str, Any]:
        return cls._types.get(label, {})

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

# Load persisted data if file exists
if REGISTRY_FILE.exists():
    try:
        with open(REGISTRY_FILE, 'r') as f:
            loaded = json.load(f)
            for label, meta in loaded.items():
                registry.register(label, meta)
        print(f"Loaded {len(loaded)} types from {REGISTRY_FILE}")
    except Exception as e:
        print(f"Failed to load registry: {e}")
        
registry.register("Site", {
    "display_name": "Site / Location",
    "properties": ["name"],
    "required": ["name"],
    "relationships": {
        "contains": {"target": "Device", "direction": "out"},
        "hosts": {"target": "Rack", "direction": "out"},
    },
})

registry.register("Device", {
    "display_name": "Device / Server / Network Equipment",
    "properties": ["name", "ip", "serial", "model"],
    "required": ["name"],
    "relationships": {
        "located_in": {"target": "Site", "direction": "out"},
    },
})

registry.register("Rack", {
    "display_name": "Rack ID",
    "properties": ["name", "height", "width", "model"],
    "required": ["name"],
    "relationships": {
        "LOCATED_IN": {"target": "Site", "direction": "out"},
    },
})