"""Process-singleton accessor for the electoral data source.

All Sankalp tools import `get_data_source()` instead of constructing
MockElectoralDataSource themselves — keeps cold-start work to once per
process and makes it trivial to swap a real ECI partner backend later.
See docs/DATA.md §8.
"""
from __future__ import annotations

from threading import Lock
from typing import Optional

from tools.electoral_data import ElectoralDataSource, MockElectoralDataSource

_lock = Lock()
_instance: Optional[ElectoralDataSource] = None


def get_data_source() -> ElectoralDataSource:
    global _instance
    if _instance is None:
        with _lock:
            if _instance is None:
                _instance = MockElectoralDataSource()
    return _instance


def set_data_source(src: ElectoralDataSource) -> None:
    """Test-only: substitute a different source."""
    global _instance
    with _lock:
        _instance = src
