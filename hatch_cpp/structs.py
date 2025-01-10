from __future__ import annotations

from os import environ, system
from pathlib import Path
from shutil import which
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

BuildType = Literal["debug", "release"]
CompilerToolchain = Literal["gcc", "clang", "msvc"]
Language = Literal["c", "c++"]
Binding = Literal["cpython", "pybind11", "nanobind"]
Platform = Literal["linux", "darwin", "win32"]
PlatformDefaults = {
    "linux": {"CC": "gcc", "CXX": "g++", "LD": "ld"},
    "darwin": {"CC": "clang", "CXX": "clang++", "LD": "ld"},
    "win32": {"CC": "cl", "CXX": "cl", "LD": "link"},
}


class HatchCppLibrary(BaseModel):
    """A C++ library."""

    name: str
    sources: List[str]
    language: Language = "c++"

    binding: Binding = "cpython"
    std: Optional[str] = None

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
    ld: str
    platform: Platform
    toolchain: CompilerToolchain

    @staticmethod
    def default() -> HatchCppPlatform:
        platform = environ.get("HATCH_CPP_PLATFORM", sys_platform)
        CC = environ.get("CC", PlatformDefaults[platform]["CC"])
        CXX = environ.get("CXX", PlatformDefaults[platform]["CXX"])
        LD = environ.get("LD", PlatformDefaults[platform]["LD"])
        if "gcc" in CC and "g++" in CXX:
            toolchain = "gcc"
        elif "clang" in CC and "clang++" in CXX:
            toolchain = "clang"
        elif "cl" in CC and "cl" in CXX:
            toolchain = "msvc"
        else:
            raise Exception(f"Unrecognized toolchain: {CC}, {CXX}")

        # Customizations
        if which("ccache") and not environ.get("HATCH_CPP_DISABLE_CCACHE"):
            CC = f"ccache {CC}"
            CXX = f"ccache {CXX}"

        # https://github.com/rui314/mold/issues/647
        # if which("ld.mold"):
        #     LD = which("ld.mold")
        # elif which("ld.lld"):
        #     LD = which("ld.lld")
        return HatchCppPlatform(cc=CC, cxx=CXX, ld=LD, platform=platform, toolchain=toolchain)

    def get_compile_flags(self, library: HatchCppLibrary, build_type: BuildType = "release") -> str:
        flags = ""

        # Python.h
        library.include_dirs.append(get_path("include"))

        if library.binding == "pybind11":
            import pybind11

            library.include_dirs.append(pybind11.get_include())
            if not library.std:
                library.std = "c++11"
        elif library.binding == "nanobind":
            import nanobind

            library.include_dirs.append(nanobind.include_dir())
            if not library.std:
                library.std = "c++17"
            library.sources.append(str(Path(nanobind.include_dir()).parent / "src" / "nb_combined.cpp"))
            library.include_dirs.append(str((Path(nanobind.include_dir()).parent / "ext" / "robin_map" / "include")))

        if self.toolchain == "gcc":
            flags += " " + " ".join(f"-I{d}" for d in library.include_dirs)
            flags += " -fPIC"
            flags += " " + " ".join(library.extra_compile_args)
            flags += " " + " ".join(f"-D{macro}" for macro in library.define_macros)
            flags += " " + " ".join(f"-U{macro}" for macro in library.undef_macros)
            if library.std:
                flags += f" -std={library.std}"
        elif self.toolchain == "clang":
            flags += " ".join(f"-I{d}" for d in library.include_dirs)
            flags += " -fPIC"
            flags += " " + " ".join(library.extra_compile_args)
            flags += " " + " ".join(f"-D{macro}" for macro in library.define_macros)
            flags += " " + " ".join(f"-U{macro}" for macro in library.undef_macros)
            if library.std:
                flags += f" -std={library.std}"
        elif self.toolchain == "msvc":
            flags += " ".join(f"/I{d}" for d in library.include_dirs)
            flags += " " + " ".join(library.extra_compile_args)
            flags += " " + " ".join(library.extra_link_args)
            flags += " " + " ".join(library.extra_objects)
            flags += " " + " ".join(f"/D{macro}" for macro in library.define_macros)
            flags += " " + " ".join(f"/U{macro}" for macro in library.undef_macros)
            flags += " /EHsc /DWIN32"
            if library.std:
                flags += f" /std:{library.std}"
        # clean
        while flags.count("  "):
            flags = flags.replace("  ", " ")
        return flags

    def get_link_flags(self, library: HatchCppLibrary, build_type: BuildType = "release") -> str:
        flags = ""
        if self.toolchain == "gcc":
            flags += " -shared"
            flags += " " + " ".join(library.extra_link_args)
            flags += " " + " ".join(library.extra_objects)
            flags += " " + " ".join(f"-l{lib}" for lib in library.libraries)
            flags += " " + " ".join(f"-L{lib}" for lib in library.library_dirs)
            flags += f" -o {library.name}.so"
            if self.platform == "darwin":
                flags += " -undefined dynamic_lookup"
            if "mold" in self.ld:
                flags += f" -fuse-ld={self.ld}"
            elif "lld" in self.ld:
                flags += " -fuse-ld=lld"
        elif self.toolchain == "clang":
            flags += " -shared"
            flags += " " + " ".join(library.extra_link_args)
            flags += " " + " ".join(library.extra_objects)
            flags += " " + " ".join(f"-l{lib}" for lib in library.libraries)
            flags += " " + " ".join(f"-L{lib}" for lib in library.library_dirs)
            flags += f" -o {library.name}.so"
            if self.platform == "darwin":
                flags += " -undefined dynamic_lookup"
            if "mold" in self.ld:
                flags += f" -fuse-ld={self.ld}"
            elif "lld" in self.ld:
                flags += " -fuse-ld=lld"
        elif self.toolchain == "msvc":
            flags += " " + " ".join(library.extra_link_args)
            flags += " " + " ".join(library.extra_objects)
            flags += " /LD"
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


class HatchCppBuildPlan(BaseModel):
    build_type: BuildType = "release"
    libraries: List[HatchCppLibrary] = Field(default_factory=list)
    platform: HatchCppPlatform = Field(default_factory=HatchCppPlatform.default)
    commands: List[str] = Field(default_factory=list)

    def generate(self):
        self.commands = []
        for library in self.libraries:
            compile_flags = self.platform.get_compile_flags(library, self.build_type)
            link_flags = self.platform.get_link_flags(library, self.build_type)
            self.commands.append(
                f"{self.platform.cc if library.language == 'c' else self.platform.cxx} {' '.join(library.sources)} {compile_flags} {link_flags}"
            )
        return self.commands

    def execute(self):
        for command in self.commands:
            system(command)
        return self.commands

    def cleanup(self):
        if self.platform.platform == "win32":
            for temp_obj in Path(".").glob("*.obj"):
                temp_obj.unlink()


class HatchCppBuildConfig(BaseModel):
    """Build config values for Hatch C++ Builder."""

    verbose: Optional[bool] = Field(default=False)
    libraries: List[HatchCppLibrary] = Field(default_factory=list)
    platform: Optional[HatchCppPlatform] = Field(default_factory=HatchCppPlatform.default)
