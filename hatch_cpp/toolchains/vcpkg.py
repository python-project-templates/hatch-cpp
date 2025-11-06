from __future__ import annotations

from pathlib import Path
from platform import machine as platform_machine
from sys import platform as sys_platform
from typing import Literal, Optional

from pydantic import BaseModel, Field

__all__ = ("HatchCppVcpkgConfiguration",)


VcpkgTriplet = Literal[
    "x64-android",
    "x64-osx",
    "x64-linux",
    "x64-uwp",
    "x64-windows",
    "x64-windows-release",
    "x64-windows-static",
    "x64-windows-static-md",
    "x86-windows",
    "arm-neon-android",
    "arm64-android",
    "arm64-osx",
    "arm64-uwp",
    "arm64-windows",
    "arm64-windows-static-md",
]
VcpkgPlatformDefaults = {
    ("linux", "x86_64"): "x64-linux",
    # ("linux", "arm64"): "",
    ("darwin", "x86_64"): "x64-osx",
    ("darwin", "arm64"): "arm64-osx",
    ("win32", "x86_64"): "x64-windows-static-md",
    ("win32", "arm64"): "arm64-windows-static-md",
}


class HatchCppVcpkgConfiguration(BaseModel):
    vcpkg: Optional[str] = Field(default="vcpkg.json")
    vcpkg_root: Optional[Path] = Field(default=Path("vcpkg"))
    vcpkg_repo: Optional[str] = Field(default="https://github.com/microsoft/vcpkg.git")
    vcpkg_triplet: Optional[VcpkgTriplet] = Field(default=None)

    # TODO: overlay

    def generate(self, config):
        commands = []

        if self.vcpkg_triplet is None:
            self.vcpkg_triplet = VcpkgPlatformDefaults.get((sys_platform, platform_machine()))
            if self.vcpkg_triplet is None:
                raise ValueError(f"Could not determine vcpkg triplet for platform {sys_platform} and architecture {platform_machine()}")

        if self.vcpkg and Path(self.vcpkg).exists():
            if not Path(self.vcpkg_root).exists():
                commands.append(f"git clone {self.vcpkg_repo} {self.vcpkg_root}")
                commands.append(
                    f"./{self.vcpkg_root / 'bootstrap-vcpkg.sh' if sys_platform != 'win32' else self.vcpkg_root / 'sbootstrap-vcpkg.bat'}"
                )
            commands.append(f"./{self.vcpkg_root / 'vcpkg'} install --triplet {self.vcpkg_triplet}")

        return commands
