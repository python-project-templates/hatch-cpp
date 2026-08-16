from __future__ import annotations

from os import environ, system as system_call
from pathlib import Path

from pkn import getSimpleLogger
from pydantic import BaseModel, Field, model_validator

from .toolchains import BuildType, HatchCppCmakeConfiguration, HatchCppLibrary, HatchCppPlatform, HatchCppVcpkgConfiguration, Toolchain

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
    platform: HatchCppPlatform | None = Field(default_factory=HatchCppPlatform.default)
    vcpkg: HatchCppVcpkgConfiguration | None = Field(default_factory=HatchCppVcpkgConfiguration)

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
        elif vcpkg_override != "0" and self.vcpkg and Path(self.vcpkg.vcpkg).exists():
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
            self.commands.extend(self.vcpkg.generate(self))

        if "vanilla" in self._active_toolchains:
            if "vcpkg" in self._active_toolchains:
                log.warning("vcpkg toolchain is active; ensure that your compiler is configured to use vcpkg includes and libs.")

            for library_index, library in enumerate(self.libraries):
                compile_flags = self.platform.get_compile_flags(library, self.build_type)
                link_flags = self.platform.get_link_flags(library, self.build_type)
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
            self.commands.extend(self.cmake.generate(self))

        return self.commands

    def execute(self):
        if self.platform.platform == "emscripten" and "vanilla" in self._active_toolchains:
            Path("build/hatch-cpp").mkdir(parents=True, exist_ok=True)
        for command in self.commands:
            ret = system_call(command)
            if ret != 0:
                raise RuntimeError(f"hatch-cpp build command failed with exit code {ret}: {command}")
        return self.commands

    def cleanup(self):
        if self.platform.platform == "win32":
            for temp_obj in Path(".").glob("*.obj"):
                temp_obj.unlink()
