import contextlib
from os import listdir, remove
from pathlib import Path
from subprocess import check_call
from sys import modules, path, platform
from sysconfig import get_config_var

import pytest


class TestProject:
    @pytest.mark.parametrize(
        "project",
        [
            "test_project_basic",
            "test_project_override_classes",
            "test_project_override_toolchain",
            "test_project_pybind",
            "test_project_pybind_vcpkg",
            "test_project_nanobind",
            "test_project_limited_api",
            "test_project_cmake",
            "test_project_cmake_vcpkg",
        ],
    )
    def test_basic(self, project):

        suffix_ext = get_config_var("EXT_SUFFIX")

        # cleanup
        with contextlib.suppress(FileNotFoundError):
            remove(f"hatch_cpp/tests/{project}/project/extension.so")
        with contextlib.suppress(FileNotFoundError):
            remove(f"hatch_cpp/tests/{project}/project/extension.pyd")
        with contextlib.suppress(FileNotFoundError):
            remove(f"hatch_cpp/tests/{project}/project/extension{suffix_ext}")

        modules.pop("project", None)
        modules.pop("project.extension", None)

        # compile
        check_call(
            [
                "hatch-build",
                "--hooks-only",
            ],
            cwd=f"hatch_cpp/tests/{project}",
        )

        # assert built
        project_dir_content = listdir(f"hatch_cpp/tests/{project}/project")
        if project == "test_project_limited_api" and platform != "win32":
            assert "extension.abi3.so" in project_dir_content
        else:
            if platform == "win32":
                assert "extension.pyd" in project_dir_content or f"extension{suffix_ext}" in project_dir_content
            else:
                assert "extension.so" in project_dir_content or f"extension{suffix_ext}" in project_dir_content

        # import
        here = Path(__file__).parent / project
        path.insert(0, str(here))
        import project.extension

        assert project.extension.hello() == "A string"
