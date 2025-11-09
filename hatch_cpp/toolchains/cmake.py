from __future__ import annotations

from os import environ
from pathlib import Path
from sys import version_info
from typing import Any, Dict, Optional, Union

from pydantic import BaseModel, Field

from .common import Platform

__all__ = ("HatchCppCmakeConfiguration",)

DefaultMSVCGenerator = {
    "12": "Visual Studio 12 2013",
    "14": "Visual Studio 14 2015",
    "14.0": "Visual Studio 14 2015",
    "14.1": "Visual Studio 15 2017",
    "14.2": "Visual Studio 16 2019",
    "14.3": "Visual Studio 17 2022",
    "14.4": "Visual Studio 17 2022",
}


class HatchCppCmakeConfiguration(BaseModel):
    root: Optional[Path] = None
    build: Path = Field(default_factory=lambda: Path("build"))
    install: Optional[Path] = Field(default=None)

    cmake_arg_prefix: Optional[str] = Field(default=None)
    cmake_args: Dict[str, str] = Field(default_factory=dict)
    cmake_env_args: Dict[Platform, Dict[str, str]] = Field(default_factory=dict)

    include_flags: Optional[Dict[str, Union[str, int, float, bool]]] = Field(default=None)

    def generate(self, config) -> Dict[str, Any]:
        commands = []

        # Derive prefix
        if self.cmake_arg_prefix is None:
            self.cmake_arg_prefix = f"{config.name.replace('.', '_').replace('-', '_').upper()}_"

        # Append base command
        commands.append(f"cmake {Path(self.root).parent} -DCMAKE_BUILD_TYPE={config.build_type} -B {self.build}")

        # Hook in to vcpkg if active
        if "vcpkg" in config._active_toolchains:
            commands[-1] += f" -DCMAKE_TOOLCHAIN_FILE={Path(config.vcpkg.vcpkg_root) / 'scripts' / 'buildsystems' / 'vcpkg.cmake'}"

        # Setup install path
        if self.install:
            commands[-1] += f" -DCMAKE_INSTALL_PREFIX={self.install}"
        else:
            commands[-1] += f" -DCMAKE_INSTALL_PREFIX={Path(self.root).parent}"

        # TODO: CMAKE_CXX_COMPILER
        if config.platform.platform == "win32":
            # TODO: prefix?
            commands[-1] += f' -G "{environ.get("CMAKE_GENERATOR", "Visual Studio 17 2022")}"'

        # Put in CMake flags
        args = self.cmake_args.copy()
        for platform, env_args in self.cmake_env_args.items():
            if platform == config.platform.platform:
                for key, value in env_args.items():
                    args[key] = value
        for key, value in args.items():
            commands[-1] += f" -D{self.cmake_arg_prefix}{key.upper()}={value}"

        # Include customs
        if self.include_flags:
            if self.include_flags.get("python_version", False):
                commands[-1] += f" -D{self.cmake_arg_prefix}PYTHON_VERSION={version_info.major}.{version_info.minor}"
            if self.include_flags.get("manylinux", False) and config.platform.platform == "linux":
                commands[-1] += f" -D{self.cmake_arg_prefix}MANYLINUX=ON"

        # Include mac deployment target
        if config.platform.platform == "darwin":
            commands[-1] += f" -DCMAKE_OSX_DEPLOYMENT_TARGET={environ.get('OSX_DEPLOYMENT_TARGET', '11')}"

        # Append build command
        commands.append(f"cmake --build {self.build} --config {config.build_type}")

        # Append install command
        commands.append(f"cmake --install {self.build} --config {config.build_type}")

        return commands
