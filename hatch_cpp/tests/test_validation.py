from json import loads
from pathlib import Path
from shutil import copytree
from subprocess import check_call
from sys import platform

import pytest
from pydantic import ValidationError

from hatch_cpp import HatchCppBuildPlan
from hatch_cpp.config import _artifact_role

FIXTURE = Path(__file__).parent / "test_project_c_abi_library"
LIBRARY = {
    "name": "project/lib/libdemo",
    "sources": ["cpp/demo.c"],
    "language": "c",
    "binding": "generic",
    "include-dirs": ["cpp/include"],
}


def _plan(**config):
    return HatchCppBuildPlan(name="demo", **config)


def test_c_abi_library_is_validated_and_recorded(tmp_path):
    project = copytree(FIXTURE, tmp_path / "project_root")
    check_call(["hatch-build", "--hooks-only"], cwd=project)

    suffix = {"win32": "dll", "darwin": "dylib"}.get(platform, "so")
    assert (project / f"project/lib/libdemo.{suffix}").is_file()
    manifest = loads((project / "project/lib/hatch-cpp-artifacts.json").read_text())
    assert manifest["version"] == 1
    assert manifest["artifacts"][0]["destination"] == f"project/lib/libdemo.{suffix}"
    assert manifest["artifacts"][0]["role"] == "library"


def test_validation_fails_on_unexported_header_function(tmp_path, monkeypatch):
    monkeypatch.setattr("hatch_native.validation.exported_symbols", lambda path: {"demo_answer"})
    library = {**LIBRARY, "expected-headers": ["include/demo/demo.h"], "header-symbol-prefix": "demo_"}
    (tmp_path / "include/demo").mkdir(parents=True)
    (tmp_path / "include/demo/demo.h").write_text("int demo_answer(void);\nint demo_abi_version(void);\n")
    plan = _plan(libraries=[library])
    output = tmp_path / plan.libraries[0].get_qualified_name(plan.platform.platform)
    output.parent.mkdir(parents=True)
    output.write_bytes(b"")

    with pytest.raises(RuntimeError, match="expected symbol was not exported: demo_abi_version"):
        plan.validate(tmp_path, [])


def test_validation_fails_on_missing_abi_string(tmp_path):
    library = {**LIBRARY, "expected-headers": ["demo.h"], "expected-abi-strings": ["DEMO_ABI_VERSION 2"]}
    (tmp_path / "demo.h").write_text("#define DEMO_ABI_VERSION 1\n")
    plan = _plan(libraries=[library])
    output = tmp_path / plan.libraries[0].get_qualified_name(plan.platform.platform)
    output.parent.mkdir(parents=True)
    output.write_bytes(b"")

    with pytest.raises(RuntimeError, match="ABI string was not found"):
        plan.validate(tmp_path, [])


def test_libraries_without_validation_fields_are_not_targets():
    assert _plan(libraries=[LIBRARY]).validation_targets([]) == []


def test_artifact_targets_resolve_by_path_library_and_packaged_name():
    plan = _plan(
        libraries=[LIBRARY],
        artifacts=[
            {"name": "explicit", "path": "somewhere/libexplicit.so"},
            {"name": "project/lib/libdemo", "expected-symbols": ["demo_answer"]},
            {"name": "installed", "expected-symbols": ["installed_answer"]},
        ],
    )
    installed = {"win32": "installed.dll", "darwin": "libinstalled.dylib"}.get(plan.platform.platform, "libinstalled.so")
    paths = [path for _, _, path in plan.validation_targets([f"project/lib/{installed}", "project/extension.so"])]
    assert paths == ["somewhere/libexplicit.so", plan.libraries[0].get_qualified_name(plan.platform.platform), f"project/lib/{installed}"]


def test_artifact_without_unique_packaged_match_needs_a_path():
    plan = _plan(artifacts=[{"name": "missing"}])
    with pytest.raises(FileNotFoundError, match="Artifact 'missing' needs a path"):
        plan.validation_targets([])


def test_artifact_manifest_requires_destination():
    with pytest.raises(ValidationError, match="artifact-manifest requires artifact-manifest-destination"):
        _plan(**{"artifact-manifest": True})


@pytest.mark.parametrize(
    "path,target_platform,role",
    [
        ("project/extension.cpython-312-x86_64-linux-gnu.so", "linux", "python-extension"),
        ("project/extension.abi3.so", "darwin", "python-extension"),
        ("project/extension.so", "linux", "python-extension"),
        ("project/extension.pyd", "win32", "python-extension"),
        ("project/lib/libdemo.so", "linux", "library"),
        ("project/lib/libdemo.dylib", "darwin", "library"),
        ("project/lib/demo.dll", "win32", "library"),
    ],
)
def test_artifact_role(path, target_platform, role):
    assert _artifact_role(path, target_platform) == role
