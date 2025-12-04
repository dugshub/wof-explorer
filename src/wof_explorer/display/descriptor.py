"""
Display descriptor for adding .display property to classes.

This descriptor provides a clean, reusable way to add display capabilities
to any class without modifying its core functionality.
"""

from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .displays import BaseDisplay


class DisplayDescriptor:
    """
    Descriptor that adds .display property to any class.

    Usage:
        class MyClass:
            display = DisplayDescriptor()

    Then:
        obj.display.tree
        obj.display.table
        obj.display.summary
    """

    def __get__(self, obj, owner) -> Optional["BaseDisplay"]:
        """
        Get display object for the instance.

        Args:
            obj: Instance of the class (None for class attribute access)
            owner: The class that owns this descriptor

        Returns:
            Display wrapper for the object, or None for class access
        """
        if obj is None:
            return None

        # Cache the display object on the instance
        cache_attr = "_display_cache"
        if not hasattr(obj, cache_attr):
            setattr(obj, cache_attr, self._create_display(obj))
        return getattr(obj, cache_attr)

    def _create_display(self, obj) -> "BaseDisplay":
        """
        Create appropriate display type based on object.

        Args:
            obj: The object to create display for

        Returns:
            Appropriate display wrapper for the object type
        """
        from .displays import (
            CursorDisplay,
            HierarchyDisplay,
            CollectionDisplay,
            BatchDisplay,
            GenericDisplay,
            BaseDisplay,
        )

        # Type-based display selection
        type_name = type(obj).__name__

        # Map class names to their display implementations
        displays = {
            "WOFSearchCursor": CursorDisplay,
            "WOFHierarchyCursor": HierarchyDisplay,
            "WOFBatchCursor": BatchDisplay,
            "PlaceCollection": CollectionDisplay,
        }

        # Get the appropriate display class or use generic
        display_class = displays.get(type_name, GenericDisplay)

        # All display classes implement the required abstract methods
        # Use cast to tell mypy this is safe
        from typing import cast, Type

        concrete_display_class = cast(Type[BaseDisplay], display_class)
        return concrete_display_class(obj)
