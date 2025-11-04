from pathlib import Path
from sys import version_info

import pytest
from pydantic import ValidationError
from toml import loads

from hatch_cpp import HatchCppBuildConfig, HatchCppBuildPlan, HatchCppLibrary, HatchCppPlatform


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

    def test_cmake_args(self):
        txt = (Path(__file__).parent / "test_project_cmake" / "pyproject.toml").read_text()
        toml = loads(txt)
        hatch_build_config = HatchCppBuildConfig(name=toml["project"]["name"], **toml["tool"]["hatch"]["build"]["hooks"]["hatch-cpp"])
        hatch_build_plan = HatchCppBuildPlan(**hatch_build_config.model_dump())
        hatch_build_plan.generate()

        assert hatch_build_plan.commands[0].startswith("cmake .")
        assert hatch_build_plan.commands[1].startswith("cmake --build build")
        assert hatch_build_plan.commands[2].startswith("cmake --install build")

        assert "-DCMAKE_BUILD_TYPE=release" in hatch_build_plan.commands[0]
        assert "-B build" in hatch_build_plan.commands[0]
        assert "-DHATCH_CPP_TEST_PROJECT_BASIC_BUILD_TESTS=OFF" in hatch_build_plan.commands[0]
        assert f"-DHATCH_CPP_TEST_PROJECT_BASIC_PYTHON_VERSION=3.{version_info.minor}" in hatch_build_plan.commands[0]
        if hatch_build_plan.platform.platform == "darwin":
            assert "-DCMAKE_OSX_DEPLOYMENT_TARGET=11" in hatch_build_plan.commands[0]

    def test_platform_toolchain_override(self):
        txt = (Path(__file__).parent / "test_project_override_toolchain" / "pyproject.toml").read_text()
        toml = loads(txt)
        hatch_build_config = HatchCppBuildConfig(name=toml["project"]["name"], **toml["tool"]["hatch"]["build"]["hooks"]["hatch-cpp"])
        assert "clang" in hatch_build_config.platform.cc
        assert "clang++" in hatch_build_config.platform.cxx
        assert hatch_build_config.platform.toolchain == "gcc"
