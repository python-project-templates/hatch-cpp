from __future__ import annotations

from importlib.machinery import EXTENSION_SUFFIXES
from os import environ, system as system_call
from pathlib import Path

from hatch_native import (
    LibraryValidationConfig,
    check_exports,
    check_headers,
    prefixed_header_symbols,
    run_validation_command,
    shared_library_name,
    write_artifact_manifest,
)
from pkn import getSimpleLogger
from pydantic import AliasChoices, BaseModel, Field, model_validator

from .toolchains import (
    BuildType,
    HatchCppArtifact,
    HatchCppCmakeConfiguration,
    HatchCppLibrary,
    HatchCppPlatform,
    HatchCppVcpkgConfiguration,
    Toolchain,
)

__all__ = (
    "HatchCppBuildConfig",
    "HatchCppBuildPlan",
)


log = getSimpleLogger("hatch_cpp")


class HatchCppBuildConfig(BaseModel):
    """Build config values for Hatch C++ Builder."""

    verbose: bool | None = Field(default=False)
    skip: bool | None = Field(default=False)
    name: str | None = Field(default=None)
    libraries: list[HatchCppLibrary] = Field(default_factory=list)
    cmake: HatchCppCmakeConfiguration | None = Field(default=None)
    platform: HatchCppPlatform = Field(default_factory=HatchCppPlatform.default)
    vcpkg: HatchCppVcpkgConfiguration | None = Field(default_factory=HatchCppVcpkgConfiguration)
    artifacts: list[HatchCppArtifact] = Field(default_factory=list)
    artifact_manifest: bool = Field(default=False, validation_alias=AliasChoices("artifact-manifest", "artifact_manifest"))
    artifact_manifest_destination: str | None = Field(
        default=None,
        validation_alias=AliasChoices("artifact-manifest-destination", "artifact_manifest_destination"),
        description="Wheel-relative path of the artifact manifest JSON, such as project/lib/hatch-cpp-artifacts.json.",
    )

    @model_validator(mode="wrap")
    @classmethod
    def validate_model(cls, data, handler):
        if "toolchain" in data:
            data["platform"] = HatchCppPlatform.platform_for_toolchain(data["toolchain"])
            data.pop("toolchain")
        elif "platform" not in data:
            data["platform"] = HatchCppPlatform.default()
        if "cc" in data:
            data["platform"].cc = data["cc"]
            data.pop("cc")
        if "cxx" in data:
            data["platform"].cxx = data["cxx"]
            data.pop("cxx")
        if "ld" in data:
            data["platform"].ld = data["ld"]
            data.pop("ld")
        if "vcpkg" in data and data["vcpkg"] == "false":
            data["vcpkg"] = None
        model = handler(data)
        if model.cmake and model.libraries:
            raise ValueError("Must not provide libraries when using cmake toolchain.")
        declared: dict[str, HatchCppLibrary] = {}
        for library in model.libraries:
            for name in library.depends:
                if name not in declared or declared[name].binding != "generic":
                    raise ValueError(f"Library '{library.name}' depends on '{name}', which must be a generic library declared before it.")
            declared[library.name] = library
        if model.artifact_manifest and not model.artifact_manifest_destination:
            raise ValueError("artifact-manifest requires artifact-manifest-destination.")
        return model


class HatchCppBuildPlan(HatchCppBuildConfig):
    build_type: BuildType = "release"
    commands: list[str] = Field(default_factory=list)

    _active_toolchains: list[Toolchain] = []

    def generate(self):
        self.commands = []

        # Check for env var overrides
        vcpkg_override = environ.get("HATCH_CPP_VCPKG")
        cmake_override = environ.get("HATCH_CPP_CMAKE")

        # Evaluate toolchains
        if vcpkg_override == "1":
            if self.vcpkg:
                self._active_toolchains.append("vcpkg")
            else:
                log.warning("HATCH_CPP_VCPKG=1 set but no vcpkg configuration found; ignoring.")
        elif vcpkg_override != "0" and self.vcpkg and self.vcpkg.vcpkg and Path(self.vcpkg.vcpkg).exists():
            self._active_toolchains.append("vcpkg")

        if self.libraries:
            self._active_toolchains.append("vanilla")
        elif cmake_override == "1":
            if self.cmake:
                self._active_toolchains.append("cmake")
            else:
                log.warning("HATCH_CPP_CMAKE=1 set but no cmake configuration found; ignoring.")
        elif cmake_override != "0" and self.cmake:
            self._active_toolchains.append("cmake")

        # Collect toolchain commands
        if "vcpkg" in self._active_toolchains:
            assert self.vcpkg is not None
            self.commands.extend(self.vcpkg.generate(self))

        if "vanilla" in self._active_toolchains:
            if "vcpkg" in self._active_toolchains:
                log.warning("vcpkg toolchain is active; ensure that your compiler is configured to use vcpkg includes and libs.")

            for library_index, library in enumerate(self.libraries):
                compile_flags = self.platform.get_compile_flags(library, self.build_type)
                dependencies = [next(other for other in self.libraries if other.name == name) for name in library.depends]
                link_flags = self.platform.get_link_flags(library, self.build_type, dependencies)
                compiler = self.platform.cc if library.language == "c" else self.platform.cxx
                if self.platform.platform == "emscripten":
                    objects = []
                    for source_index, source in enumerate(library.sources):
                        obj = Path("build/hatch-cpp") / f"{library_index}-{source_index}-{Path(source).stem}.o"
                        objects.append(str(obj))
                        self.commands.append(f"{compiler} -c {source} {compile_flags} -o {obj}")
                    self.commands.append(f"{compiler} {' '.join(objects)} {link_flags}")
                else:
                    self.commands.append(f"{compiler} {' '.join(library.sources)} {compile_flags} {link_flags}")

        if "cmake" in self._active_toolchains:
            assert self.cmake is not None
            self.commands.extend(self.cmake.generate(self))

        return self.commands

    def execute(self):
        if self.platform.platform == "emscripten" and "vanilla" in self._active_toolchains:
            Path("build/hatch-cpp").mkdir(parents=True, exist_ok=True)
        if "vanilla" in self._active_toolchains:
            for library in self.libraries:
                Path(self._library_output(library)).parent.mkdir(parents=True, exist_ok=True)
        for command in self.commands:
            ret = system_call(command)
            if ret != 0:
                raise RuntimeError(f"hatch-cpp build command failed with exit code {ret}: {command}")
        return self.commands

    def cleanup(self):
        if self.platform.platform == "win32":
            for temp_obj in Path(".").glob("*.obj"):
                temp_obj.unlink()

    def _library_output(self, library: HatchCppLibrary) -> str:
        return library.get_qualified_name(self.platform.platform)

    def _artifact_path(self, artifact: HatchCppArtifact, packaged: list[str]) -> str:
        if artifact.path:
            return artifact.path
        library = next((library for library in self.libraries if library.name == artifact.name), None)
        if library is not None:
            return self._library_output(library)
        filename = shared_library_name(Path(artifact.name).name, platform=self.platform.platform)
        matches = [path for path in packaged if Path(path).name == filename]
        if len(matches) != 1:
            found = ", ".join(matches) if matches else "none"
            raise FileNotFoundError(f"Artifact '{artifact.name}' needs a path: expected one packaged '{filename}', found {found}.")
        return matches[0]

    def validation_targets(self, packaged: list[str]) -> list[tuple[str, LibraryValidationConfig, str]]:
        """Libraries with validation fields set, plus every `artifacts` entry, as (label, config, project-relative path)."""
        targets: list[tuple[str, LibraryValidationConfig, str]] = [
            (library.name, library, self._library_output(library)) for library in self.libraries if _has_validation(library)
        ]
        targets.extend((artifact.name, artifact, self._artifact_path(artifact, packaged)) for artifact in self.artifacts)
        return targets

    def validate(self, root: Path, packaged: list[str]) -> None:
        """Check headers, ABI strings, and exports of each validation target, then run its validation commands."""
        for label, config, relative in self.validation_targets(packaged):
            library = root / relative
            if not library.is_file():
                raise FileNotFoundError(f"Artifact '{label}' library was not built: {relative}")
            headers = check_headers(config.expected_headers, config.expected_abi_strings, base=root, label=label)
            expected = list(dict.fromkeys([*config.expected_symbols, *prefixed_header_symbols(headers, config.header_symbol_prefix, label=label)]))
            check_exports(library, expected=expected, load=config.validate_artifact, label=label, display_path=relative)
            tokens = {"name": label, "path": str(library), "header": str(headers[0]) if headers else ""}
            for command in config.validation_commands:
                env = {**environ, **{key: value.format(**tokens) for key, value in command.env.items()}}
                env.update({"HATCH_CPP_ARTIFACT_NAME": label, "HATCH_CPP_ARTIFACT_PATH": str(library)})
                cwd = root / command.working_directory if command.working_directory else root
                run_validation_command([value.format(**tokens) for value in command.command], cwd=cwd, env=env, label=label)

    def write_manifest(self, root: Path, packaged: list[str]) -> str | None:
        """Write the manifest of packaged binaries under the project root and return its relative path."""
        if not self.artifact_manifest:
            return None
        assert self.artifact_manifest_destination is not None
        records = [
            {
                "name": Path(path).name,
                "role": _artifact_role(path, self.platform.platform),
                "platform": self.platform.platform,
                "profile": self.build_type,
                "destination": Path(path).as_posix(),
            }
            for path in sorted(packaged)
        ]
        write_artifact_manifest(root / self.artifact_manifest_destination, module=self.name or "", records=records)
        return self.artifact_manifest_destination


def _has_validation(config: LibraryValidationConfig) -> bool:
    return bool(
        config.expected_symbols
        or config.expected_headers
        or config.expected_abi_strings
        or config.header_symbol_prefix
        or config.validate_artifact
        or config.validation_commands
    )


def _artifact_role(path: str, platform: str) -> str:
    """Classify a packaged binary: a Python extension module or a plain shared library."""
    filename = Path(path).name
    if filename.endswith(".pyd"):
        return "python-extension"
    if platform != "win32" and filename.startswith("lib"):
        return "library"
    if any(filename.endswith(suffix) for suffix in EXTENSION_SUFFIXES if suffix != ".so") or ".abi3." in filename:
        return "python-extension"
    if filename.endswith(".so") and platform in ("linux", "darwin", "emscripten"):
        return "python-extension"
    return "library"
