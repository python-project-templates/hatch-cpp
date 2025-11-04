from os import listdir
from pathlib import Path
from shutil import rmtree
from subprocess import check_call
from sys import modules, path, platform

import pytest


class TestProject:
    @pytest.mark.parametrize(
        "project",
        [
            "test_project_basic",
            "test_project_override_classes",
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
        # cleanup
        rmtree(f"hatch_cpp/tests/{project}/project/extension.so", ignore_errors=True)
        rmtree(f"hatch_cpp/tests/{project}/project/extension.pyd", ignore_errors=True)
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

        if project == "test_project_limited_api" and platform != "win32":
            assert "extension.abi3.so" in listdir(f"hatch_cpp/tests/{project}/project")
        else:
            if platform == "win32":
                assert "extension.pyd" in listdir(f"hatch_cpp/tests/{project}/project")
            else:
                assert "extension.so" in listdir(f"hatch_cpp/tests/{project}/project")

        # import
        here = Path(__file__).parent / project
        path.insert(0, str(here))
        import project.extension

        assert project.extension.hello() == "A string"
