from os import environ
from pathlib import Path
from sys import version_info
from unittest.mock import patch

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

    def test_cmake_args_env_variable(self):
        """Test that CMAKE_ARGS environment variable is respected."""
        txt = (Path(__file__).parent / "test_project_cmake" / "pyproject.toml").read_text()
        toml_data = loads(txt)
        hatch_build_config = HatchCppBuildConfig(name=toml_data["project"]["name"], **toml_data["tool"]["hatch"]["build"]["hooks"]["hatch-cpp"])
        hatch_build_plan = HatchCppBuildPlan(**hatch_build_config.model_dump())

        with patch.dict(environ, {"CMAKE_ARGS": "-DFOO=bar -DBAZ=qux"}):
            hatch_build_plan.generate()
            assert "-DFOO=bar" in hatch_build_plan.commands[0]
            assert "-DBAZ=qux" in hatch_build_plan.commands[0]

    def test_cmake_args_env_variable_empty(self):
        """Test that an empty CMAKE_ARGS does not add extra whitespace."""
        txt = (Path(__file__).parent / "test_project_cmake" / "pyproject.toml").read_text()
        toml_data = loads(txt)
        hatch_build_config = HatchCppBuildConfig(name=toml_data["project"]["name"], **toml_data["tool"]["hatch"]["build"]["hooks"]["hatch-cpp"])
        hatch_build_plan = HatchCppBuildPlan(**hatch_build_config.model_dump())

        with patch.dict(environ, {"CMAKE_ARGS": ""}):
            hatch_build_plan.generate()
            # Should not have trailing whitespace from empty CMAKE_ARGS
            assert not hatch_build_plan.commands[0].endswith(" ")

    def test_cmake_generator_env_variable(self):
        """Test that CMAKE_GENERATOR environment variable is respected on non-Windows platforms."""
        txt = (Path(__file__).parent / "test_project_cmake" / "pyproject.toml").read_text()
        toml_data = loads(txt)
        hatch_build_config = HatchCppBuildConfig(name=toml_data["project"]["name"], **toml_data["tool"]["hatch"]["build"]["hooks"]["hatch-cpp"])
        hatch_build_plan = HatchCppBuildPlan(**hatch_build_config.model_dump())

        with patch.dict(environ, {"CMAKE_GENERATOR": "Ninja"}):
            hatch_build_plan.generate()
            assert '-G "Ninja"' in hatch_build_plan.commands[0]

    def test_cmake_generator_env_variable_unset(self):
        """Test that no -G flag is added on non-Windows when CMAKE_GENERATOR is not set."""
        txt = (Path(__file__).parent / "test_project_cmake" / "pyproject.toml").read_text()
        toml_data = loads(txt)
        hatch_build_config = HatchCppBuildConfig(name=toml_data["project"]["name"], **toml_data["tool"]["hatch"]["build"]["hooks"]["hatch-cpp"])
        hatch_build_plan = HatchCppBuildPlan(**hatch_build_config.model_dump())

        with patch.dict(environ, {}, clear=False):
            # Remove CMAKE_GENERATOR if present
            environ.pop("CMAKE_GENERATOR", None)
            hatch_build_plan.generate()
            if hatch_build_plan.platform.platform != "win32":
                assert "-G " not in hatch_build_plan.commands[0]

    def test_hatch_cpp_cmake_env_force_off(self):
        """Test that HATCH_CPP_CMAKE=0 disables cmake even when cmake config is present."""
        txt = (Path(__file__).parent / "test_project_cmake" / "pyproject.toml").read_text()
        toml_data = loads(txt)
        hatch_build_config = HatchCppBuildConfig(name=toml_data["project"]["name"], **toml_data["tool"]["hatch"]["build"]["hooks"]["hatch-cpp"])
        hatch_build_plan = HatchCppBuildPlan(**hatch_build_config.model_dump())

        assert hatch_build_plan.cmake is not None
        with patch.dict(environ, {"HATCH_CPP_CMAKE": "0"}):
            hatch_build_plan.generate()
            # cmake should not be active, so no cmake commands generated
            assert len(hatch_build_plan.commands) == 0
            assert "cmake" not in hatch_build_plan._active_toolchains

    def test_hatch_cpp_cmake_env_force_on(self):
        """Test that HATCH_CPP_CMAKE=1 enables cmake when cmake config is present."""
        txt = (Path(__file__).parent / "test_project_cmake" / "pyproject.toml").read_text()
        toml_data = loads(txt)
        hatch_build_config = HatchCppBuildConfig(name=toml_data["project"]["name"], **toml_data["tool"]["hatch"]["build"]["hooks"]["hatch-cpp"])
        hatch_build_plan = HatchCppBuildPlan(**hatch_build_config.model_dump())

        assert hatch_build_plan.cmake is not None
        with patch.dict(environ, {"HATCH_CPP_CMAKE": "1"}):
            hatch_build_plan.generate()
            assert "cmake" in hatch_build_plan._active_toolchains

    def test_hatch_cpp_cmake_env_force_on_no_config(self):
        """Test that HATCH_CPP_CMAKE=1 warns and skips when no cmake config exists."""
        txt = (Path(__file__).parent / "test_project_cmake" / "pyproject.toml").read_text()
        toml_data = loads(txt)
        config_data = toml_data["tool"]["hatch"]["build"]["hooks"]["hatch-cpp"].copy()
        config_data.pop("cmake", None)
        hatch_build_config = HatchCppBuildConfig(name=toml_data["project"]["name"], **config_data)
        hatch_build_plan = HatchCppBuildPlan(**hatch_build_config.model_dump())

        assert hatch_build_plan.cmake is None
        with patch.dict(environ, {"HATCH_CPP_CMAKE": "1"}):
            hatch_build_plan.generate()
            # cmake should NOT be activated when there's no config
            assert "cmake" not in hatch_build_plan._active_toolchains

    def test_hatch_cpp_vcpkg_env_force_off(self):
        """Test that HATCH_CPP_VCPKG=0 disables vcpkg even when vcpkg.json exists."""
        txt = (Path(__file__).parent / "test_project_cmake_vcpkg" / "pyproject.toml").read_text()
        toml_data = loads(txt)
        hatch_build_config = HatchCppBuildConfig(name=toml_data["project"]["name"], **toml_data["tool"]["hatch"]["build"]["hooks"]["hatch-cpp"])
        hatch_build_plan = HatchCppBuildPlan(**hatch_build_config.model_dump())

        with patch.dict(environ, {"HATCH_CPP_VCPKG": "0"}):
            hatch_build_plan.generate()
            assert "vcpkg" not in hatch_build_plan._active_toolchains

    def test_hatch_cpp_vcpkg_env_force_on(self):
        """Test that HATCH_CPP_VCPKG=1 enables vcpkg even when vcpkg.json doesn't exist."""
        txt = (Path(__file__).parent / "test_project_cmake" / "pyproject.toml").read_text()
        toml_data = loads(txt)
        hatch_build_config = HatchCppBuildConfig(name=toml_data["project"]["name"], **toml_data["tool"]["hatch"]["build"]["hooks"]["hatch-cpp"])
        hatch_build_plan = HatchCppBuildPlan(**hatch_build_config.model_dump())

        with patch.dict(environ, {"HATCH_CPP_VCPKG": "1"}):
            hatch_build_plan.generate()
            assert "vcpkg" in hatch_build_plan._active_toolchains
