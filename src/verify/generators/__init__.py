"""Generator registry — maps generator IDs to concrete implementations."""

from verify.generators.base import BaseGenerator, GeneratedFiles

_REGISTRY: dict[str, type[BaseGenerator]] = {}


def register(generator_id: str):
    """Decorator to register a generator class."""
    def decorator(cls):
        _REGISTRY[generator_id] = cls
        return cls
    return decorator


def get_generator(generator_id: str) -> BaseGenerator:
    """Look up and instantiate a generator by ID."""
    cls = _REGISTRY.get(generator_id)
    if cls is None:
        available = ", ".join(_REGISTRY.keys()) or "(none)"
        raise ValueError(f"Unknown generator '{generator_id}'. Available: {available}")
    return cls()


def list_generators() -> list[str]:
    return list(_REGISTRY.keys())


# Import generators to trigger registration
from verify.generators import cucumber_java  # noqa: F401, E402
