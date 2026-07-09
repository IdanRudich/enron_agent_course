"""Reference solution agent package for the Enron Challenge course."""

from enron_reference.agent import ReferenceAgent
from enron_reference.indexer import INDEX_DB_NAME, build_index, open_index

__all__ = [
    "INDEX_DB_NAME",
    "ReferenceAgent",
    "build_index",
    "open_index",
]
