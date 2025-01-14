import pytest
from pydantic import ValidationError

from hatch_cpp.structs import HatchCppLibrary, HatchCppPlatform


class TestStructs:
    def test_validate_py_limited_api(self):
        with pytest.raises(ValidationError):
            library = HatchCppLibrary(
                name="test",
                sources=["test.cpp"],
                py_limited_api="42",
            )
        library = HatchCppLibrary(
            name="test",
            sources=["test.cpp"],
            py_limited_api="cp39",
        )
        assert library.py_limited_api == "cp39"
        platform = HatchCppPlatform.default()
        flags = platform.get_compile_flags(library)
        assert "-DPy_LIMITED_API=0x030900f0" in flags or "/DPy_LIMITED_API=0x030900f0" in flags

        with pytest.raises(ValidationError):
            library.binding = "pybind11"
