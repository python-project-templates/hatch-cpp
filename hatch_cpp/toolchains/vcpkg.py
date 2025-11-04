from __future__ import annotations

from pathlib import Path
from sys import platform as sys_platform
from typing import Optional

from pydantic import BaseModel, Field

__all__ = ("HatchCppVcpkgConfiguration",)


class HatchCppVcpkgConfiguration(BaseModel):
    vcpkg: Optional[str] = Field(default="vcpkg.json")
    vcpkg_root: Optional[Path] = Field(default=Path("vcpkg"))
    vcpkg_repo: Optional[str] = Field(default="https://github.com/microsoft/vcpkg.git")

    def generate(self, config):
        commands = []

        if self.vcpkg and Path(self.vcpkg.vcpkg).exists():
            if not Path(self.vcpkg.vcpkg_root).exists():
                commands.append(f"git clone {self.vcpkg.vcpkg_repo} {self.vcpkg.vcpkg_root}")
                commands.append(
                    f"./{self.vcpkg.vcpkg_root / 'bootstrap-vcpkg.sh' if sys_platform != 'win32' else self.vcpkg.vcpkg_root / 'sbootstrap-vcpkg.bat'}"
                )
            commands.append(
                f"./{self.vcpkg.vcpkg_root / 'vcpkg'} install --triplet {config.platform.platform}-{config.platform.toolchain} --manifest-root {Path(self.vcpkg.vcpkg).parent}"
            )

        return commands
