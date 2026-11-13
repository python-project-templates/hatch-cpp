from json import loads
from os import environ
from pathlib import Path
from shutil import copy2, copytree
from subprocess import check_call, run
from sys import executable, platform

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


def test_c_abi_library_is_validated_linked_and_recorded(tmp_path):
    project = copytree(FIXTURE, tmp_path / "build_root")
    check_call(["hatch-build", "--hooks-only"], cwd=project)

    suffix = _library_suffix()
    manifest = loads((project / "project/lib/hatch-cpp-artifacts.json").read_text())
    roles = {record["destination"]: record["role"] for record in manifest["artifacts"]}
    assert roles[f"project/lib/libdemo.{suffix}"] == "library"
    assert [role for role in roles.values() if role == "python-extension"] == ["python-extension"]

    # The extension finds libdemo through a package-relative rpath, so the package still imports after it moves.
    installed = copytree(project / "project", tmp_path / "site" / "project")
    check_call([executable, "-c", "import project.extension as e; assert e.answer() == 42"], cwd=installed.parent)


def _library_suffix():
    return {"win32": "dll", "darwin": "dylib"}.get(platform, "so")


@pytest.mark.skipif(platform == "win32", reason="the external prefix is found through the loader path, which Windows does not have")
def test_external_mode_links_a_prebuilt_library(tmp_path):
    bundled = copytree(FIXTURE, tmp_path / "bundled")
    check_call(["hatch-build", "--hooks-only"], cwd=bundled)
    prefix = tmp_path / "prefix"
    (prefix / "lib").mkdir(parents=True)
    copy2(bundled / f"project/lib/libdemo.{_library_suffix()}", prefix / "lib")
    copytree(bundled / "cpp/include", prefix / "include")

    external = copytree(FIXTURE, tmp_path / "external")
    env = {**environ, "HATCH_CPP_LIBRARY_SOURCE": "external", "HATCH_CPP_LIBRARY_ROOT": str(prefix)}
    check_call(["hatch-build", "--hooks-only"], cwd=external, env=env)

    assert not (external / f"project/lib/libdemo.{_library_suffix()}").exists()
    manifest = loads((external / "project/lib/hatch-cpp-artifacts.json").read_text())
    assert [record["role"] for record in manifest["artifacts"]] == ["python-extension"]
    loader_path = "DYLD_LIBRARY_PATH" if platform == "darwin" else "LD_LIBRARY_PATH"
    check_call(
        [executable, "-c", "import project.extension as e; assert e.answer() == 42"],
        cwd=external,
        env={**environ, loader_path: str(prefix / "lib")},
    )


def test_direct_mode_compiles_the_library_into_the_extension(tmp_path):
    project = copytree(FIXTURE, tmp_path / "direct")
    check_call(["hatch-build", "--hooks-only"], cwd=project, env={**environ, "HATCH_CPP_LIBRARY_SOURCE": "direct"})

    assert not (project / f"project/lib/libdemo.{_library_suffix()}").exists()
    check_call([executable, "-c", "import project.extension as e; assert e.answer() == 42"], cwd=project)


def test_static_mode_is_rejected(monkeypatch):
    monkeypatch.setenv("HATCH_CPP_LIBRARY_SOURCE", "static")
    extension = {"name": "project/extension", "sources": ["ext.c"], "depends": ["project/lib/libdemo"]}
    with pytest.raises(ValueError, match="'static' is not supported"):
        _plan(libraries=[LIBRARY, extension]).generate()


def test_python_package_is_rejected():
    with pytest.raises(ValidationError, match="python-package, which hatch-cpp does not support yet"):
        _plan(libraries=[{**LIBRARY, "python-package": "other"}])


CMAKE_FIXTURE = Path(__file__).parent / "test_project_cmake_c_abi"


def test_cmake_library_is_validated_by_name(tmp_path):
    project = copytree(CMAKE_FIXTURE, tmp_path / "cmake")
    check_call(["hatch-build", "--hooks-only"], cwd=project)

    manifest = loads((project / "project/lib/hatch-cpp-artifacts.json").read_text())
    roles = sorted(record["role"] for record in manifest["artifacts"])
    assert roles == ["library", "python-extension"]
    installed = copytree(project / "project", tmp_path / "site" / "project")
    check_call([executable, "-c", "import project.extension as e; assert e.answer() == 42"], cwd=installed.parent)


def test_cmake_library_validation_failure_stops_the_build(tmp_path):
    project = copytree(CMAKE_FIXTURE, tmp_path / "cmake")
    pyproject = project / "pyproject.toml"
    pyproject.write_text(pyproject.read_text().replace("DEMO_ABI_VERSION 1", "DEMO_ABI_VERSION 2"))
    completed = run(["hatch-build", "--hooks-only"], check=False, cwd=project, capture_output=True, text=True)
    assert completed.returncode != 0
    assert "Artifact 'demo' expected ABI string was not found in headers: DEMO_ABI_VERSION 2" in completed.stderr + completed.stdout


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
        plan.validate_artifacts(tmp_path, [])


def test_validation_fails_on_missing_abi_string(tmp_path):
    library = {**LIBRARY, "expected-headers": ["demo.h"], "expected-abi-strings": ["DEMO_ABI_VERSION 2"]}
    (tmp_path / "demo.h").write_text("#define DEMO_ABI_VERSION 1\n")
    plan = _plan(libraries=[library])
    output = tmp_path / plan.libraries[0].get_qualified_name(plan.platform.platform)
    output.parent.mkdir(parents=True)
    output.write_bytes(b"")

    with pytest.raises(RuntimeError, match="ABI string was not found"):
        plan.validate_artifacts(tmp_path, [])


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


def test_depends_must_name_an_earlier_generic_library():
    with pytest.raises(ValidationError, match="must be a generic library declared before it"):
        _plan(libraries=[{"name": "project/extension", "sources": ["ext.c"], "depends": ["project/lib/libdemo"]}, LIBRARY])


def test_generic_library_gets_layout_neutral_identity():
    plan = _plan(libraries=[LIBRARY])
    library = plan.libraries[0]
    plan.platform.toolchain = "clang"
    plan.platform.platform = "darwin"
    assert "-Wl,-install_name,@rpath/libdemo.dylib" in plan.platform.get_link_flags(library)
    plan.platform.platform = "linux"
    assert "-Wl,-soname,libdemo.so" in plan.platform.get_link_flags(library)
    library.extra_link_args = ["-Wl,-soname,libdemo.so.1"]
    assert "-Wl,-soname,libdemo.so " not in plan.platform.get_link_flags(library)


def test_depends_links_output_and_sets_rpath():
    extension = {"name": "project/extension", "sources": ["ext.c"], "depends": ["project/lib/libdemo"]}
    plan = _plan(libraries=[LIBRARY, extension])
    producer, consumer = plan.libraries
    plan.platform.toolchain = "gcc"
    plan.platform.platform = "linux"
    flags = plan.platform.get_link_flags(consumer, dependencies=[producer])
    assert "project/lib/libdemo.so -Wl,-rpath,\\$ORIGIN/lib" in flags
    plan.platform.toolchain = "msvc"
    plan.platform.platform = "win32"
    assert "project/lib/libdemo.lib" in plan.platform.get_link_flags(consumer, dependencies=[producer]).replace("\\", "/")
    plan.platform.toolchain = "clang"
    plan.platform.platform = "emscripten"
    with pytest.raises(ValueError, match="not supported for Emscripten"):
        plan.platform.get_link_flags(consumer, dependencies=[producer])


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
