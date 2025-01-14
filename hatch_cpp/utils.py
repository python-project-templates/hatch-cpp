from __future__ import annotations

from functools import lru_cache

from pydantic import ImportString, TypeAdapter

_import_string_adapter = TypeAdapter(ImportString)


@lru_cache(maxsize=None)
def import_string(input_string: str):
    return _import_string_adapter.validate_python(input_string)
