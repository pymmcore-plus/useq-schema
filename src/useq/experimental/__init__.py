"""Experimental features for useq."""


def __getattr__(name: str) -> object:
    """Get an attribute from the module."""
    if name in {"MDARunner", "PMDAEngine"}:
        raise AttributeError(
            f"{name!r} is no longer available in {__name__}. "
            "Please depend on pymmcore-plus instead. (You can still use MDARunner "
            "and PMDAEngine without any other micro-manager dependencies.)"
        )
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
