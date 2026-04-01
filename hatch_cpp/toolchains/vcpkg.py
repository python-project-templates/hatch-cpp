from __future__ import annotations

import configparser
import subprocess
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

    def _bootstrap_script_path(self) -> Path:
        return self.vcpkg_root / ("bootstrap-vcpkg.bat" if sys_platform == "win32" else "bootstrap-vcpkg.sh")

    def _vcpkg_executable_path(self) -> Path:
        if sys_platform == "win32":
            return self.vcpkg_root / "vcpkg.exe"
        return self.vcpkg_root / "vcpkg"

    def _delete_dir_command(self, path: Path) -> str:
        if sys_platform == "win32":
            return f'rmdir /s /q "{path}"'
        return f'rm -rf "{path}"'

    def _is_vcpkg_working(self) -> bool:
        vcpkg_executable = self._vcpkg_executable_path()
        if not vcpkg_executable.exists():
            return False
        try:
            result = subprocess.run([str(vcpkg_executable), "version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
            return result.returncode == 0
        except OSError:
            return False

    def _clone_checkout_bootstrap_commands(self) -> list[str]:
        commands = [f"git clone {self.vcpkg_repo} {self.vcpkg_root}"]

        ref = self._resolve_vcpkg_ref()
        if ref is not None:
            commands.append(f"git -C {self.vcpkg_root} checkout {ref}")

        commands.append(f"./{self._bootstrap_script_path()}")
        return commands

    def generate(self, config):
        commands = []

        if self.vcpkg_triplet is None:
            self.vcpkg_triplet = VcpkgPlatformDefaults.get((sys_platform, platform_machine()))
            if self.vcpkg_triplet is None:
                raise ValueError(f"Could not determine vcpkg triplet for platform {sys_platform} and architecture {platform_machine()}")

        if self.vcpkg and Path(self.vcpkg).exists():
            vcpkg_root = Path(self.vcpkg_root)
            bootstrap_script = self._bootstrap_script_path()

            if not vcpkg_root.exists():
                commands.extend(self._clone_checkout_bootstrap_commands())
            else:
                is_empty_dir = vcpkg_root.is_dir() and not any(vcpkg_root.iterdir())
                if is_empty_dir:
                    commands.append(self._delete_dir_command(vcpkg_root))
                    commands.extend(self._clone_checkout_bootstrap_commands())
                else:
                    vcpkg_executable = self._vcpkg_executable_path()
                    if not vcpkg_executable.exists():
                        commands.append(f"./{bootstrap_script}")
                    elif not self._is_vcpkg_working():
                        commands.append(self._delete_dir_command(vcpkg_root))
                        commands.extend(self._clone_checkout_bootstrap_commands())

            commands.append(f"./{self.vcpkg_root / 'vcpkg'} install --triplet {self.vcpkg_triplet}")

        return commands
