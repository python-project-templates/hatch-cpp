from __future__ import annotations

from logging import getLogger
from os import system as system_call
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field, model_validator

from .toolchains import BuildType, HatchCppCmakeConfiguration, HatchCppLibrary, HatchCppPlatform, HatchCppVcpkgConfiguration, Toolchain

__all__ = (
    "HatchCppBuildConfig",
    "HatchCppBuildPlan",
)


_log = getLogger(__name__)


class HatchCppBuildConfig(BaseModel):
    """Build config values for Hatch C++ Builder."""

    verbose: Optional[bool] = Field(default=False)
    name: Optional[str] = Field(default=None)
    libraries: List[HatchCppLibrary] = Field(default_factory=list)
    cmake: Optional[HatchCppCmakeConfiguration] = Field(default=None)
    platform: Optional[HatchCppPlatform] = Field(default_factory=HatchCppPlatform.default)
    vcpkg: Optional[HatchCppVcpkgConfiguration] = Field(default_factory=HatchCppVcpkgConfiguration)

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
    commands: List[str] = Field(default_factory=list)

    _active_toolchains: List[Toolchain] = []

    def generate(self):
        self.commands = []

        # Evaluate toolchains
        if self.vcpkg and Path(self.vcpkg.vcpkg).exists():
            self._active_toolchains.append("vcpkg")
        if self.libraries:
            self._active_toolchains.append("vanilla")
        elif self.cmake:
            self._active_toolchains.append("cmake")

        # Collect toolchain commands
        if "vcpkg" in self._active_toolchains:
            self.commands.extend(self.vcpkg.generate(self))

        if "vanilla" in self._active_toolchains:
            if "vcpkg" in self._active_toolchains:
                _log.warning("vcpkg toolchain is active; ensure that your compiler is configured to use vcpkg includes and libs.")

            for library in self.libraries:
                compile_flags = self.platform.get_compile_flags(library, self.build_type)
                link_flags = self.platform.get_link_flags(library, self.build_type)
                self.commands.append(
                    f"{self.platform.cc if library.language == 'c' else self.platform.cxx} {' '.join(library.sources)} {compile_flags} {link_flags}"
                )

        if "cmake" in self._active_toolchains:
            self.commands.extend(self.cmake.generate(self))

        return self.commands

    def execute(self):
        for command in self.commands:
            system_call(command)
        return self.commands

    def cleanup(self):
        if self.platform.platform == "win32":
            for temp_obj in Path(".").glob("*.obj"):
                temp_obj.unlink()
