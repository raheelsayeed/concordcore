#!/usr/bin/env python3
"""LLM Adapter registry for clinical notes extraction.

This module provides a registry for managing LLM adapters and provides
functions for registering and retrieving adapters by name.

Example usage:
    from concordcore.ai.adapters import get_adapter, register_adapter

    # Get a registered adapter
    adapter = get_adapter('anthropic', api_key='...')

    # Register a custom adapter
    register_adapter('my_llm', MyCustomAdapter)
"""

import logging
from typing import Any

from concordcore.ai.llm_provider import LLMProvider

log = logging.getLogger(__name__)

# Registry of adapter classes
_adapters: dict[str, type] = {}


def register_adapter(name: str, adapter_class: type) -> None:
    """Register an LLM adapter class.

    Args:
        name: Unique identifier for this adapter (e.g., 'anthropic', 'openai')
        adapter_class: The adapter class to register

    Raises:
        ValueError: If an adapter with this name is already registered
    """
    if name in _adapters:
        log.warning(f"Overwriting existing adapter: {name}")

    _adapters[name] = adapter_class
    log.debug(f"Registered LLM adapter: {name}")


def unregister_adapter(name: str) -> None:
    """Unregister an LLM adapter.

    Args:
        name: The adapter name to unregister
    """
    if name in _adapters:
        del _adapters[name]
        log.debug(f"Unregistered LLM adapter: {name}")


def get_adapter(name: str, **kwargs) -> LLMProvider:
    """Get an instantiated LLM adapter by name.

    Args:
        name: The adapter name to retrieve
        **kwargs: Arguments to pass to the adapter constructor

    Returns:
        An instance of the requested adapter

    Raises:
        ValueError: If the adapter is not registered
    """
    if name not in _adapters:
        available = list(_adapters.keys())
        raise ValueError(f"Unknown LLM adapter: {name}. Available: {available}")

    return _adapters[name](**kwargs)


def list_adapters() -> list[str]:
    """List all registered adapter names.

    Returns:
        List of registered adapter names
    """
    return list(_adapters.keys())


def is_registered(name: str) -> bool:
    """Check if an adapter is registered.

    Args:
        name: The adapter name to check

    Returns:
        True if the adapter is registered, False otherwise
    """
    return name in _adapters


# Auto-register built-in adapters on import
def _register_builtin_adapters():
    """Register built-in adapters if their dependencies are available."""
    try:
        from concordcore.ai.adapters.anthropic_adapter import AnthropicAdapter
        register_adapter('anthropic', AnthropicAdapter)
    except ImportError:
        log.debug("Anthropic adapter not available (anthropic package not installed)")

    try:
        from concordcore.ai.adapters.openai_adapter import OpenAIAdapter
        register_adapter('openai', OpenAIAdapter)
    except ImportError:
        log.debug("OpenAI adapter not available (openai package not installed)")


_register_builtin_adapters()
