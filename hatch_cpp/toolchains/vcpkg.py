from __future__ import annotations

import configparser
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
    ("win32", "AMD64"): "x64-windows-static-md",
    ("win32", "arm64"): "arm64-windows-static-md",
}


def _read_vcpkg_ref_from_gitmodules(vcpkg_root: Path) -> Optional[str]:
    """Read the branch/ref for vcpkg from .gitmodules if it exists.

    Looks for a submodule whose path matches ``vcpkg_root`` and returns
    its ``branch`` value when present.
    """
    gitmodules_path = Path(".gitmodules")
    if not gitmodules_path.exists():
        return None

    parser = configparser.ConfigParser()
    parser.read(str(gitmodules_path))

    for section in parser.sections():
        if parser.get(section, "path", fallback=None) == str(vcpkg_root):
            return parser.get(section, "branch", fallback=None)

    return None


class HatchCppVcpkgConfiguration(BaseModel):
    vcpkg: Optional[str] = Field(default="vcpkg.json")
    vcpkg_root: Optional[Path] = Field(default=Path("vcpkg"))
    vcpkg_repo: Optional[str] = Field(default="https://github.com/microsoft/vcpkg.git")
    vcpkg_triplet: Optional[VcpkgTriplet] = Field(default=None)
    vcpkg_ref: Optional[str] = Field(
        default=None,
        description="Branch, tag, or commit SHA to checkout after cloning vcpkg. "
        "If not set, falls back to the branch specified in .gitmodules for the vcpkg submodule.",
    )

    # TODO: overlay

    def _resolve_vcpkg_ref(self) -> Optional[str]:
        """Return the ref to checkout: explicit config takes priority, then .gitmodules."""
        if self.vcpkg_ref is not None:
            return self.vcpkg_ref
        return _read_vcpkg_ref_from_gitmodules(self.vcpkg_root)

    def generate(self, config):
        commands = []

        if self.vcpkg_triplet is None:
            self.vcpkg_triplet = VcpkgPlatformDefaults.get((sys_platform, platform_machine()))
            if self.vcpkg_triplet is None:
                raise ValueError(f"Could not determine vcpkg triplet for platform {sys_platform} and architecture {platform_machine()}")

        if self.vcpkg and Path(self.vcpkg).exists():
            if not Path(self.vcpkg_root).exists():
                commands.append(f"git clone {self.vcpkg_repo} {self.vcpkg_root}")

                ref = self._resolve_vcpkg_ref()
                if ref is not None:
                    commands.append(f"git -C {self.vcpkg_root} checkout {ref}")

                commands.append(f"./{self.vcpkg_root / 'bootstrap-vcpkg.sh' if sys_platform != 'win32' else self.vcpkg_root / 'bootstrap-vcpkg.bat'}")
            commands.append(f"./{self.vcpkg_root / 'vcpkg'} install --triplet {self.vcpkg_triplet}")

        return commands
