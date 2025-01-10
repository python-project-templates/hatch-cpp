from os import listdir
from pathlib import Path
from shutil import rmtree
from subprocess import check_call
from sys import path, platform


class TestProject:
    def test_basic(self):
        rmtree("hatch_cpp/tests/test_project_basic/basic_project/extension.so", ignore_errors=True)
        rmtree("hatch_cpp/tests/test_project_basic/basic_project/extension.pyd", ignore_errors=True)
        check_call(
            [
                "hatchling",
                "build",
                "--hooks-only",
            ],
            cwd="hatch_cpp/tests/test_project_basic",
        )
        if platform == "win32":
            assert "extension.pyd" in listdir("hatch_cpp/tests/test_project_basic/basic_project")
        else:
            assert "extension.so" in listdir("hatch_cpp/tests/test_project_basic/basic_project")
        here = Path(__file__).parent / "test_project_basic"
        path.insert(0, str(here))
        import basic_project.extension

        assert basic_project.extension.hello() == "A string"

    def test_override_classes(self):
        rmtree("hatch_cpp/tests/test_project_override_classes/basic_project/extension.so", ignore_errors=True)
        rmtree("hatch_cpp/tests/test_project_override_classes/basic_project/extension.pyd", ignore_errors=True)
        check_call(
            [
                "hatchling",
                "build",
                "--hooks-only",
            ],
            cwd="hatch_cpp/tests/test_project_override_classes",
        )
        if platform == "win32":
            assert "extension.pyd" in listdir("hatch_cpp/tests/test_project_override_classes/basic_project")
        else:
            assert "extension.so" in listdir("hatch_cpp/tests/test_project_override_classes/basic_project")
        here = Path(__file__).parent / "test_project_override_classes"
        path.insert(0, str(here))
        import basic_project.extension

        assert basic_project.extension.hello() == "A string"
