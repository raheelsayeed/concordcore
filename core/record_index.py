#!/usr/bin/env python3
"""Record indexing utilities for fast O(1) lookups.

This module provides the RecordIndex class for efficient record lookup
instead of O(n) filter() operations.

Example usage:
    from core.record_index import RecordIndex

    index = RecordIndex(records)
    record = index.get_by_id('LDL')
    record = index.get_by_var_id('cholesterol')
"""

from typing import TypeVar, Generic, Iterator, Callable, Any
import logging

log = logging.getLogger(__name__)

T = TypeVar('T')


class RecordIndex(Generic[T]):
    """Fast O(1) lookup index for records.

    Builds hash indexes on common lookup keys (id, var.id) for
    efficient retrieval instead of linear filtering.

    Attributes:
        _by_id: Dict mapping record.id to record
        _by_var_id: Dict mapping record.var.id to record (if applicable)
        _items: Original list of items

    Example:
        records = [record1, record2, record3]
        index = RecordIndex(records)

        # O(1) lookup by id
        ldl_record = index.get_by_id('LDL')

        # O(1) lookup by var.id
        ldl_record = index.get_by_var_id('LDL')

        # Iterate all
        for record in index:
            print(record)
    """

    def __init__(self, items: list[T] | None = None):
        """Initialize index with optional items.

        Args:
            items: List of items to index. Items should have 'id' attribute.
        """
        self._items: list[T] = []
        self._by_id: dict[str, T] = {}
        self._by_var_id: dict[str, T] = {}

        if items:
            self.build(items)

    def build(self, items: list[T]) -> 'RecordIndex[T]':
        """Build indexes from item list.

        Args:
            items: List of items to index

        Returns:
            Self for method chaining
        """
        self._items = list(items)
        self._by_id.clear()
        self._by_var_id.clear()

        for item in self._items:
            # Index by id attribute
            if hasattr(item, 'id') and item.id:
                self._by_id[item.id] = item

            # Index by var.id if item has var attribute
            if hasattr(item, 'var') and item.var and hasattr(item.var, 'id'):
                self._by_var_id[item.var.id] = item

            # Index by record.id if item has record attribute (EvaluatedRecord)
            if hasattr(item, 'record') and item.record:
                if hasattr(item.record, 'id') and item.record.id:
                    self._by_id[item.record.id] = item
                if hasattr(item.record, 'var') and item.record.var:
                    self._by_var_id[item.record.var.id] = item

        return self

    def get_by_id(self, identifier: str) -> T | None:
        """Get item by its id attribute.

        Args:
            identifier: The id to look up

        Returns:
            The item if found, None otherwise
        """
        return self._by_id.get(identifier)

    def get_by_var_id(self, var_id: str) -> T | None:
        """Get item by its var.id attribute.

        Args:
            var_id: The var.id to look up

        Returns:
            The item if found, None otherwise
        """
        return self._by_var_id.get(var_id)

    def get(self, identifier: str) -> T | None:
        """Get item by id, trying both id and var.id.

        Args:
            identifier: The identifier to look up

        Returns:
            The item if found, None otherwise
        """
        return self._by_id.get(identifier) or self._by_var_id.get(identifier)

    def contains(self, identifier: str) -> bool:
        """Check if identifier exists in index.

        Args:
            identifier: The identifier to check

        Returns:
            True if found, False otherwise
        """
        return identifier in self._by_id or identifier in self._by_var_id

    def add(self, item: T) -> None:
        """Add a single item to the index.

        Args:
            item: Item to add
        """
        self._items.append(item)

        if hasattr(item, 'id') and item.id:
            self._by_id[item.id] = item

        if hasattr(item, 'var') and item.var and hasattr(item.var, 'id'):
            self._by_var_id[item.var.id] = item

        if hasattr(item, 'record') and item.record:
            if hasattr(item.record, 'id') and item.record.id:
                self._by_id[item.record.id] = item
            if hasattr(item.record, 'var') and item.record.var:
                self._by_var_id[item.record.var.id] = item

    def all(self) -> list[T]:
        """Get all items.

        Returns:
            List of all indexed items
        """
        return self._items

    def filter(self, predicate: Callable[[T], bool]) -> list[T]:
        """Filter items by predicate.

        Args:
            predicate: Function that returns True for items to include

        Returns:
            List of matching items
        """
        return [item for item in self._items if predicate(item)]

    def __iter__(self) -> Iterator[T]:
        """Iterate over all items."""
        return iter(self._items)

    def __len__(self) -> int:
        """Return number of items."""
        return len(self._items)

    def __contains__(self, identifier: str) -> bool:
        """Check if identifier in index."""
        return self.contains(identifier)

    def __getitem__(self, identifier: str) -> T | None:
        """Get item by identifier."""
        return self.get(identifier)


def build_record_dict(records: list) -> dict[str, Any]:
    """Build a dictionary mapping record ids to their values.

    This is a convenience function for expression evaluation.

    Args:
        records: List of records with id and value attributes

    Returns:
        Dict mapping id to value.value (or None if no value)
    """
    return {
        r.id: (r.value.value if r.value else None)
        for r in records
        if hasattr(r, 'id')
    }
