"""MonsoonDelta — src/monsoon package init."""
from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("monsoon")
except PackageNotFoundError:
    __version__ = "0.0.0-dev"
