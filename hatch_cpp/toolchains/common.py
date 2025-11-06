from __future__ import annotations

from os import environ
from pathlib import Path
from re import match
from shutil import which
from sys import executable, platform as sys_platform
from sysconfig import get_path
from typing import Any, List, Literal, Optional

from pydantic import AliasChoices, BaseModel, Field, field_validator, model_validator

__all__ = (
    "BuildType",
    "CompilerToolchain",
    "Toolchain",
    "Language",
    "Binding",
    "Platform",
    "PlatformDefaults",
    "HatchCppLibrary",
    "HatchCppPlatform",
)


BuildType = Literal["debug", "release"]
CompilerToolchain = Literal["gcc", "clang", "msvc"]
Toolchain = Literal["vcpkg", "cmake", "vanilla"]
Language = Literal["c", "c++"]
Binding = Literal["cpython", "pybind11", "nanobind", "generic"]
Platform = Literal["linux", "darwin", "win32"]
PlatformDefaults = {
    "linux": {"CC": "gcc", "CXX": "g++", "LD": "ld"},
    "darwin": {"CC": "clang", "CXX": "clang++", "LD": "ld"},
    "win32": {"CC": "cl", "CXX": "cl", "LD": "link"},
}


class HatchCppLibrary(BaseModel, validate_assignment=True):
    """A C++ library."""

    name: str
    sources: List[str]
    language: Language = "c++"

    binding: Binding = "cpython"
    std: Optional[str] = None

    include_dirs: List[str] = Field(default_factory=list, alias=AliasChoices("include_dirs", "include-dirs"))
    library_dirs: List[str] = Field(default_factory=list, alias=AliasChoices("library_dirs", "library-dirs"))
    libraries: List[str] = Field(default_factory=list)

    extra_compile_args: List[str] = Field(default_factory=list, alias=AliasChoices("extra_compile_args", "extra-compile-args"))
    extra_link_args: List[str] = Field(default_factory=list, alias=AliasChoices("extra_link_args", "extra-link-args"))
    extra_objects: List[str] = Field(default_factory=list, alias=AliasChoices("extra_objects", "extra-objects"))

    define_macros: List[str] = Field(default_factory=list, alias=AliasChoices("define_macros", "define-macros"))
    undef_macros: List[str] = Field(default_factory=list, alias=AliasChoices("undef_macros", "undef-macros"))

    export_symbols: List[str] = Field(default_factory=list, alias=AliasChoices("export_symbols", "export-symbols"))
    depends: List[str] = Field(default_factory=list)

    py_limited_api: Optional[str] = Field(default="", alias=AliasChoices("py_limited_api", "py-limited-api"))

    @field_validator("py_limited_api", mode="before")
    @classmethod
    def check_py_limited_api(cls, value: Any) -> Any:
        if value:
            if not match(r"cp3\d", value):
                raise ValueError("py-limited-api must be in the form of cp3X")
        return value

    def get_qualified_name(self, platform):
        if platform == "win32":
            suffix = "dll" if self.binding == "generic" else "pyd"
        elif platform == "darwin":
            suffix = "dylib" if self.binding == "generic" else "so"
        else:
            suffix = "so"
        if self.py_limited_api and platform != "win32":
            return f"{self.name}.abi3.{suffix}"
        return f"{self.name}.{suffix}"

    @model_validator(mode="after")
    def check_binding_and_py_limited_api(self):
        if self.binding == "pybind11" and self.py_limited_api:
            raise ValueError("pybind11 does not support Py_LIMITED_API")
        if self.binding == "generic" and self.py_limited_api:
            raise ValueError("Generic binding can not support Py_LIMITED_API")
        return self


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
        # Fallback to platform defaults
        elif platform == "linux":
            toolchain = "gcc"
        elif platform == "darwin":
            toolchain = "clang"
        elif platform == "win32":
            toolchain = "msvc"
        else:
            toolchain = "gcc"

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

    @staticmethod
    def platform_for_toolchain(toolchain: CompilerToolchain) -> HatchCppPlatform:
        platform = HatchCppPlatform.default()
        platform.toolchain = toolchain
        return platform

    def get_compile_flags(self, library: HatchCppLibrary, build_type: BuildType = "release") -> str:
        flags = ""

        # Python.h
        if library.binding != "generic":
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

        if library.py_limited_api:
            if library.binding == "pybind11":
                raise ValueError("pybind11 does not support Py_LIMITED_API")
            library.define_macros.append(f"Py_LIMITED_API=0x0{library.py_limited_api[2]}0{hex(int(library.py_limited_api[3:]))[2:]}00f0")

        # Toolchain-specific flags
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
            flags += f" -o {library.get_qualified_name(self.platform)}"
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
            flags += f" -o {library.get_qualified_name(self.platform)}"
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
            flags += f" /Fe:{library.get_qualified_name(self.platform)}"
            flags += " /link /DLL"
            if (Path(executable).parent / "libs").exists():
                flags += f" /LIBPATH:{str(Path(executable).parent / 'libs')}"
            flags += " " + " ".join(f"{lib}.lib" for lib in library.libraries)
            flags += " " + " ".join(f"/LIBPATH:{lib}" for lib in library.library_dirs)
        # clean
        while flags.count("  "):
            flags = flags.replace("  ", " ")
        return flags
