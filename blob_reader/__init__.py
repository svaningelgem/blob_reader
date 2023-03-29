import importlib.metadata

from .block import Block

__all__ = ["Block", "__version__"]


__version__= importlib.metadata.version('blob_reader')
