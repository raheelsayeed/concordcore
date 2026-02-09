#!/usr/bin/env python3
"""Expression function registry for ConcordCore.

This module provides a registry for custom functions that can be used in
CPG expressions. Built-in functions for common operations are included,
and users can register their own functions.

Example usage:
    from concordcore.core.expression_registry import registry, register_function

    # Register a custom function
    @register_function('my_calc')
    def my_calculation(x, y):
        return x + y

    # Use in expressions via the registry
    functions = registry.get_functions()
    # Pass to simpleeval: simple_eval(expr, functions=functions)

Built-in functions:
    - date_diff_days(date1, date2): Days between two dates
    - date_diff_years(date1, date2): Years between two dates
    - days_since(date): Days since the given date
    - years_since(date): Years since the given date
    - min_value(*values): Minimum of values
    - max_value(*values): Maximum of values
    - avg_value(*values): Average of values
    - count(items): Count of items
    - any_true(*values): True if any value is truthy
    - all_true(*values): True if all values are truthy
    - in_range(value, min, max): True if value is in range [min, max]
    - code_in(code, *codes): True if code is in the list
"""

import logging
from datetime import datetime, date
from typing import Any, Callable
from functools import wraps

log = logging.getLogger(__name__)


class ExpressionFunctionRegistry:
    """Registry for expression functions.

    Manages a collection of functions that can be used in CPG expressions.
    Provides both built-in functions and the ability to register custom ones.

    Example:
        registry = ExpressionFunctionRegistry()

        # Register with decorator
        @registry.register('my_func')
        def my_function(x):
            return x * 2

        # Register directly
        registry.register_function('other_func', lambda x: x + 1)

        # Get all functions for simpleeval
        functions = registry.get_functions()
    """

    def __init__(self):
        """Initialize the registry with built-in functions."""
        self._functions: dict[str, Callable] = {}
        self._register_builtins()

    def _register_builtins(self) -> None:
        """Register built-in functions."""
        # Date functions
        self._functions['date_diff_days'] = date_diff_days
        self._functions['date_diff_years'] = date_diff_years
        self._functions['days_since'] = days_since
        self._functions['years_since'] = years_since

        # Aggregate functions
        self._functions['min_value'] = min_value
        self._functions['max_value'] = max_value
        self._functions['avg_value'] = avg_value
        self._functions['count'] = count

        # Boolean functions
        self._functions['any_true'] = any_true
        self._functions['all_true'] = all_true

        # Range/membership functions
        self._functions['in_range'] = in_range
        self._functions['code_in'] = code_in

        # Utility functions
        self._functions['coalesce'] = coalesce
        self._functions['if_then_else'] = if_then_else

    def register(self, name: str) -> Callable:
        """Decorator to register a function.

        Args:
            name: The name to register the function under

        Returns:
            Decorator function

        Example:
            @registry.register('my_func')
            def my_function(x):
                return x * 2
        """
        def decorator(func: Callable) -> Callable:
            self.register_function(name, func)
            return func
        return decorator

    def register_function(self, name: str, func: Callable) -> None:
        """Register a function directly.

        Args:
            name: The name to register the function under
            func: The function to register
        """
        if name in self._functions:
            log.warning(f"Overwriting existing function: {name}")

        self._functions[name] = func
        log.debug(f"Registered function: {name}")

    def unregister(self, name: str) -> None:
        """Unregister a function.

        Args:
            name: The name of the function to unregister
        """
        if name in self._functions:
            del self._functions[name]
            log.debug(f"Unregistered function: {name}")

    def get_function(self, name: str) -> Callable | None:
        """Get a function by name.

        Args:
            name: The function name

        Returns:
            The function if found, None otherwise.
        """
        return self._functions.get(name)

    def get_functions(self) -> dict[str, Callable]:
        """Get all registered functions.

        Returns:
            Dictionary mapping function names to callables.
            Suitable for passing to simpleeval.
        """
        return self._functions.copy()

    def list_functions(self) -> list[str]:
        """List all registered function names.

        Returns:
            List of registered function names.
        """
        return list(self._functions.keys())


# =============================================================================
# Built-in Functions
# =============================================================================

def date_diff_days(date1: date | datetime, date2: date | datetime) -> int:
    """Calculate the number of days between two dates.

    Args:
        date1: First date
        date2: Second date

    Returns:
        Number of days (positive if date1 > date2)
    """
    if isinstance(date1, datetime):
        date1 = date1.date()
    if isinstance(date2, datetime):
        date2 = date2.date()

    return (date1 - date2).days


def date_diff_years(date1: date | datetime, date2: date | datetime) -> float:
    """Calculate the number of years between two dates.

    Args:
        date1: First date
        date2: Second date

    Returns:
        Number of years (approximate, based on 365.25 days/year)
    """
    days = date_diff_days(date1, date2)
    return days / 365.25


def days_since(d: date | datetime) -> int:
    """Calculate days since the given date.

    Args:
        d: The date to measure from

    Returns:
        Number of days since the date (positive if in the past)
    """
    return date_diff_days(date.today(), d)


def years_since(d: date | datetime) -> float:
    """Calculate years since the given date.

    Args:
        d: The date to measure from

    Returns:
        Number of years since the date
    """
    return date_diff_years(date.today(), d)


def min_value(*values: Any) -> Any:
    """Get the minimum of the provided values.

    Filters out None values before comparison.

    Args:
        *values: Values to compare

    Returns:
        The minimum value, or None if no valid values
    """
    valid_values = [v for v in values if v is not None]
    return min(valid_values) if valid_values else None


def max_value(*values: Any) -> Any:
    """Get the maximum of the provided values.

    Filters out None values before comparison.

    Args:
        *values: Values to compare

    Returns:
        The maximum value, or None if no valid values
    """
    valid_values = [v for v in values if v is not None]
    return max(valid_values) if valid_values else None


def avg_value(*values: Any) -> float | None:
    """Calculate the average of the provided values.

    Filters out None values before calculation.

    Args:
        *values: Values to average

    Returns:
        The average value, or None if no valid values
    """
    valid_values = [v for v in values if v is not None]
    if not valid_values:
        return None
    return sum(valid_values) / len(valid_values)


def count(items: Any) -> int:
    """Count the number of items.

    Args:
        items: A collection or value to count

    Returns:
        The count of items (0 if None, 1 if scalar)
    """
    if items is None:
        return 0
    try:
        return len(items)
    except TypeError:
        return 1


def any_true(*values: Any) -> bool:
    """Check if any of the values are truthy.

    Args:
        *values: Values to check

    Returns:
        True if any value is truthy
    """
    return any(values)


def all_true(*values: Any) -> bool:
    """Check if all of the values are truthy.

    Args:
        *values: Values to check

    Returns:
        True if all values are truthy
    """
    return all(values)


def in_range(value: Any, min_val: Any, max_val: Any) -> bool:
    """Check if a value is within a range (inclusive).

    Args:
        value: The value to check
        min_val: Minimum of range
        max_val: Maximum of range

    Returns:
        True if min_val <= value <= max_val
    """
    if value is None:
        return False
    return min_val <= value <= max_val


def code_in(code: Any, *codes: Any) -> bool:
    """Check if a code is in a list of codes.

    Args:
        code: The code to check
        *codes: The codes to check against

    Returns:
        True if code is in codes
    """
    if code is None:
        return False

    # Handle Code objects
    code_str = str(code)
    code_strs = [str(c) for c in codes]

    return code_str in code_strs


def coalesce(*values: Any) -> Any:
    """Return the first non-None value.

    Args:
        *values: Values to check

    Returns:
        First non-None value, or None if all are None
    """
    for value in values:
        if value is not None:
            return value
    return None


def if_then_else(condition: bool, then_value: Any, else_value: Any) -> Any:
    """Conditional expression.

    Args:
        condition: The condition to evaluate
        then_value: Value to return if condition is True
        else_value: Value to return if condition is False

    Returns:
        then_value if condition else else_value
    """
    return then_value if condition else else_value


# =============================================================================
# Module-level registry and convenience functions
# =============================================================================

# Default registry instance
registry = ExpressionFunctionRegistry()


def register_function(name: str) -> Callable:
    """Decorator to register a function with the default registry.

    Args:
        name: The name to register the function under

    Returns:
        Decorator function

    Example:
        @register_function('my_func')
        def my_function(x):
            return x * 2
    """
    return registry.register(name)


def get_functions() -> dict[str, Callable]:
    """Get all functions from the default registry.

    Returns:
        Dictionary of registered functions.
    """
    return registry.get_functions()
