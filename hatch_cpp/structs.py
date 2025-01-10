from __future__ import annotations

from os import environ, system
from pathlib import Path
from sys import executable, platform as sys_platform
from sysconfig import get_path
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

__all__ = (
    "HatchCppBuildConfig",
    "HatchCppLibrary",
    "HatchCppPlatform",
    "HatchCppBuildPlan",
)

Platform = Literal["linux", "darwin", "win32"]
CompilerToolchain = Literal["gcc", "clang", "msvc"]
PlatformDefaults = {
    "linux": {"CC": "gcc", "CXX": "g++"},
    "darwin": {"CC": "clang", "CXX": "clang++"},
    "win32": {"CC": "cl", "CXX": "cl"},
}


class HatchCppLibrary(BaseModel):
    """A C++ library."""

    name: str
    sources: List[str]

    include_dirs: List[str] = Field(default_factory=list, alias="include-dirs")
    library_dirs: List[str] = Field(default_factory=list, alias="library-dirs")
    libraries: List[str] = Field(default_factory=list)
    extra_compile_args: List[str] = Field(default_factory=list, alias="extra-compile-args")
    extra_link_args: List[str] = Field(default_factory=list, alias="extra-link-args")
    extra_objects: List[str] = Field(default_factory=list, alias="extra-objects")
    define_macros: List[str] = Field(default_factory=list, alias="define-macros")
    undef_macros: List[str] = Field(default_factory=list, alias="undef-macros")

    export_symbols: List[str] = Field(default_factory=list, alias="export-symbols")
    depends: List[str] = Field(default_factory=list)


class HatchCppPlatform(BaseModel):
    cc: str
    cxx: str
    platform: Platform
    toolchain: CompilerToolchain

    @staticmethod
    def default() -> HatchCppPlatform:
        platform = environ.get("HATCH_CPP_PLATFORM", sys_platform)
        CC = environ.get("CC", PlatformDefaults[platform]["CC"])
        CXX = environ.get("CXX", PlatformDefaults[platform]["CXX"])
        if "gcc" in CC and "g++" in CXX:
            toolchain = "gcc"
        elif "clang" in CC and "clang++" in CXX:
            toolchain = "clang"
        elif "cl" in CC and "cl" in CXX:
            toolchain = "msvc"
        else:
            raise Exception(f"Unrecognized toolchain: {CC}, {CXX}")
        return HatchCppPlatform(cc=CC, cxx=CXX, platform=platform, toolchain=toolchain)

    def get_compile_flags(self, library: HatchCppLibrary) -> str:
        flags = ""
        if self.toolchain == "gcc":
            flags = f"-I{get_path('include')}"
            flags += " " + " ".join(f"-I{d}" for d in library.include_dirs)
            flags += " -fPIC -shared"
            flags += " " + " ".join(library.extra_compile_args)
            flags += " " + " ".join(library.extra_link_args)
            flags += " " + " ".join(library.extra_objects)
            flags += " " + " ".join(f"-l{lib}" for lib in library.libraries)
            flags += " " + " ".join(f"-L{lib}" for lib in library.library_dirs)
            flags += " " + " ".join(f"-D{macro}" for macro in library.define_macros)
            flags += " " + " ".join(f"-U{macro}" for macro in library.undef_macros)
            flags += f" -o {library.name}.so"
        elif self.toolchain == "clang":
            flags = f"-I{get_path('include')} "
            flags += " ".join(f"-I{d}" for d in library.include_dirs)
            flags += " -undefined dynamic_lookup -fPIC -shared"
            flags += " " + " ".join(library.extra_compile_args)
            flags += " " + " ".join(library.extra_link_args)
            flags += " " + " ".join(library.extra_objects)
            flags += " " + " ".join(f"-l{lib}" for lib in library.libraries)
            flags += " " + " ".join(f"-L{lib}" for lib in library.library_dirs)
            flags += " " + " ".join(f"-D{macro}" for macro in library.define_macros)
            flags += " " + " ".join(f"-U{macro}" for macro in library.undef_macros)
            flags += f" -o {library.name}.so"
        elif self.toolchain == "msvc":
            flags = f"/I{get_path('include')} "
            flags += " ".join(f"/I{d}" for d in library.include_dirs)
            flags += " " + " ".join(library.extra_compile_args)
            flags += " " + " ".join(library.extra_link_args)
            flags += " " + " ".join(library.extra_objects)
            flags += " " + " ".join(f"/D{macro}" for macro in library.define_macros)
            flags += " " + " ".join(f"/U{macro}" for macro in library.undef_macros)
            flags += " /EHsc /DWIN32 /LD"
            flags += f" /Fo:{library.name}.obj"
            flags += f" /Fe:{library.name}.pyd"
            flags += " /link /DLL"
            if (Path(executable).parent / "libs").exists():
                flags += f" /LIBPATH:{str(Path(executable).parent / 'libs')}"
            flags += " " + " ".join(f"{lib}.lib" for lib in library.libraries)
            flags += " " + " ".join(f"/LIBPATH:{lib}" for lib in library.library_dirs)
        # clean
        while flags.count("  "):
            flags = flags.replace("  ", " ")
        return flags

    def get_link_flags(self, library: HatchCppLibrary) -> str:
        # TODO
        flags = ""
        return flags


class HatchCppBuildPlan(BaseModel):
    libraries: List[HatchCppLibrary] = Field(default_factory=list)
    platform: HatchCppPlatform = Field(default_factory=HatchCppPlatform.default)
    commands: List[str] = Field(default_factory=list)

    def generate(self):
        self.commands = []
        for library in self.libraries:
            flags = self.platform.get_compile_flags(library)
            self.commands.append(f"{self.platform.cc} {' '.join(library.sources)} {flags}")
        return self.commands

    def execute(self):
        for command in self.commands:
            system(command)
        return self.commands

    def cleanup(self):
        if self.platform.platform == "win32":
            for library in self.libraries:
                temp_obj = Path(f"{library.name}.obj")
                if temp_obj.exists():
                    temp_obj.unlink()


class HatchCppBuildConfig(BaseModel):
    """Build config values for Hatch C++ Builder."""

    verbose: Optional[bool] = Field(default=False)
    libraries: List[HatchCppLibrary] = Field(default_factory=list)
    platform: Optional[HatchCppPlatform] = Field(default_factory=HatchCppPlatform.default)

    # build_function: str | None = None
    # build_kwargs: t.Mapping[str, str] = field(default_factory=dict)
    # editable_build_kwargs: t.Mapping[str, str] = field(default_factory=dict)
    # ensured_targets: list[str] = field(default_factory=list)
    # skip_if_exists: list[str] = field(default_factory=list)
