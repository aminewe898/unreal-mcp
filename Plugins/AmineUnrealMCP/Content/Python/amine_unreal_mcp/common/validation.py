"""Pure validation, usable outside Unreal for unit tests."""
import math
import re


class ToolError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def limit(value: int, maximum: int = 500) -> int:
    if isinstance(value, bool) or not 1 <= value <= maximum:
        raise ToolError("invalid_limit", f"Limit must be between 1 and {maximum}.")
    return value


def asset_path(path: str, writable: bool = False) -> str:
    root = r"/Game/" if writable else r"/[A-Za-z0-9_]+/"
    if not re.fullmatch(root + r"[A-Za-z0-9_/]+(?:\.[A-Za-z0-9_]+)?", path) or "//" in path or path.endswith("/"):
        raise ToolError("invalid_asset_path", "Use an exact Unreal asset path; writes are restricted to /Game/.")
    if "." in path and path.rsplit("/", 1)[-1].split(".")[0] != path.rsplit(".", 1)[-1]:
        raise ToolError("invalid_asset_path", "Object name must match the package asset name.")
    return path.split(".")[0]


def name(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):
        raise ToolError("invalid_name", "Use letters, digits and underscores; start with a letter or underscore.")
    return value


def finite(values) -> None:
    if any(not math.isfinite(float(value)) for value in values):
        raise ToolError("invalid_number", "NaN and infinity are not accepted.")


def resolve_match(objects, reference: str, exact_only: bool = False):
    exact = [obj for obj in objects if obj.get_path_name() == reference]
    if len(exact) == 1:
        return exact[0]
    if exact_only:
        raise ToolError("actor_not_found", f"No live editor actor exists at {reference}; deletion requires an exact object path.")
    matches = [obj for obj in objects if obj.get_actor_label() == reference or obj.get_name() == reference]
    if len(matches) > 1:
        raise ToolError("ambiguous_actor", f"Actor reference {reference!r} matched {len(matches)} actors. Use an exact object path.")
    if not matches:
        raise ToolError("actor_not_found", f"No live editor actor matches {reference!r}.")
    return matches[0]
