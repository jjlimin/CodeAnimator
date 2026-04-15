"""
Object Registry - The Memory

This module maintains a live dictionary of all visual objects on the canvas.
It allows the engine to modify existing shapes instead of redrawing them.
"""

from typing import Dict, Any, Optional


class ObjectRegistry:
    """
    A registry that tracks all visual objects currently on the canvas.

    Each object is stored with a unique ID and can be retrieved, updated, or destroyed.
    """

    def __init__(self):
        """Initialize an empty registry."""
        self.objects: Dict[str, Any] = {}
        self.metadata: Dict[str, Dict[str, Any]] = {}  # Store metadata for objects

    def register(self, obj_id: str, obj: Any) -> None:
        """
        Register a new visual object.

        Args:
            obj_id: Unique identifier for the object.
            obj: The visual object to register (Manim VMobject or other).

        Raises:
            ValueError: If the ID already exists.
        """
        if obj_id in self.objects:
            raise ValueError(f"Object with ID '{obj_id}' already exists in registry.")
        self.objects[obj_id] = obj

    def get(self, obj_id: str) -> Any:
        """
        Retrieve a visual object by ID.

        Args:
            obj_id: Unique identifier for the object.

        Returns:
            The visual object.

        Raises:
            KeyError: If the object does not exist.
        """
        if obj_id not in self.objects:
            raise KeyError(f"Object with ID '{obj_id}' not found in registry.")
        return self.objects[obj_id]

    def has(self, obj_id: str) -> bool:
        """
        Check if an object exists in the registry.

        Args:
            obj_id: Unique identifier for the object.

        Returns:
            True if the object exists, False otherwise.
        """
        return obj_id in self.objects

    def update(self, obj_id: str, obj: Any) -> None:
        """
        Update an existing object.

        Args:
            obj_id: Unique identifier for the object.
            obj: The new visual object.

        Raises:
            KeyError: If the object does not exist.
        """
        if obj_id not in self.objects:
            raise KeyError(f"Object with ID '{obj_id}' not found in registry.")
        self.objects[obj_id] = obj

    def destroy(self, obj_id: str) -> Any:
        """
        Remove and return an object from the registry.

        Args:
            obj_id: Unique identifier for the object.

        Returns:
            The removed object.

        Raises:
            KeyError: If the object does not exist.
        """
        if obj_id not in self.objects:
            raise KeyError(f"Object with ID '{obj_id}' not found in registry.")
        return self.objects.pop(obj_id)

    def list_all(self) -> Dict[str, Any]:
        """
        Get all registered objects.

        Returns:
            Dictionary of all objects indexed by their IDs.
        """
        return self.objects.copy()

    def clear(self) -> None:
        """Clear all objects from the registry."""
        self.objects.clear()

    def set_metadata(self, obj_id: str, key: str, value: Any) -> None:
        """
        Set metadata for an object.

        Args:
            obj_id: Unique identifier for the object.
            key: Metadata key.
            value: Metadata value.
        """
        if obj_id not in self.metadata:
            self.metadata[obj_id] = {}
        self.metadata[obj_id][key] = value

    def get_metadata(self, obj_id: str, key: str) -> Any:
        """
        Get metadata for an object.

        Args:
            obj_id: Unique identifier for the object.
            key: Metadata key.

        Returns:
            The metadata value.

        Raises:
            KeyError: If the object or key does not exist.
        """
        if obj_id not in self.metadata or key not in self.metadata[obj_id]:
            raise KeyError(f"Metadata '{key}' for object '{obj_id}' not found.")
        return self.metadata[obj_id][key]

    def __repr__(self) -> str:
        """Return a string representation of the registry."""
        return f"ObjectRegistry({list(self.objects.keys())})"

