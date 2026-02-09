"""ConcordCore — A Python framework for evaluating Clinical Practice Guidelines.

Top-level convenience imports. For full API, import from submodules directly:

    from concordcore.core.concord import Concord
    from concordcore.core.cpg import CPG
    from concordcore.core.cpg_registry import get_registry
    from concordcore.variables.var import Var
    from concordcore.primitives.types import Persona
"""

__version__ = "1.0.0"

# Lazy imports to avoid circular dependency issues
__all__ = [
    "Concord",
    "CPG",
    "get_registry",
    "CPGRegistry",
    "HealthContext",
    "NeedAttestationError",
    "PipelineResult",
]


def __getattr__(name):
    if name in ("Concord", "PipelineResult"):
        from concordcore.core.concord import Concord, PipelineResult
        return Concord if name == "Concord" else PipelineResult
    elif name == "CPG":
        from concordcore.core.cpg import CPG
        return CPG
    elif name in ("get_registry", "CPGRegistry"):
        from concordcore.core.cpg_registry import get_registry, CPGRegistry
        return get_registry if name == "get_registry" else CPGRegistry
    elif name == "HealthContext":
        from concordcore.core.healthcontext import HealthContext
        return HealthContext
    elif name == "NeedAttestationError":
        from concordcore.core.errors import NeedAttestationError
        return NeedAttestationError
    raise AttributeError(f"module 'concordcore' has no attribute '{name}'")
