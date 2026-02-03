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
    include_dirs_linux: List[str] = Field(default_factory=list, alias=AliasChoices("include_dirs_linux", "include-dirs-linux"))
    include_dirs_darwin: List[str] = Field(default_factory=list, alias=AliasChoices("include_dirs_darwin", "include-dirs-darwin"))
    include_dirs_win32: List[str] = Field(default_factory=list, alias=AliasChoices("include_dirs_win32", "include-dirs-win32"))

    library_dirs: List[str] = Field(default_factory=list, alias=AliasChoices("library_dirs", "library-dirs"))
    library_dirs_linux: List[str] = Field(default_factory=list, alias=AliasChoices("library_dirs_linux", "library-dirs-linux"))
    library_dirs_darwin: List[str] = Field(default_factory=list, alias=AliasChoices("library_dirs_darwin", "library-dirs-darwin"))
    library_dirs_win32: List[str] = Field(default_factory=list, alias=AliasChoices("library_dirs_win32", "library-dirs-win32"))

    libraries: List[str] = Field(default_factory=list)
    libraries_linux: List[str] = Field(default_factory=list, alias=AliasChoices("libraries_linux", "libraries-linux"))
    libraries_darwin: List[str] = Field(default_factory=list, alias=AliasChoices("libraries_darwin", "libraries-darwin"))
    libraries_win32: List[str] = Field(default_factory=list, alias=AliasChoices("libraries_win32", "libraries-win32"))

    extra_compile_args: List[str] = Field(default_factory=list, alias=AliasChoices("extra_compile_args", "extra-compile-args"))
    extra_compile_args_linux: List[str] = Field(default_factory=list, alias=AliasChoices("extra_compile_args_linux", "extra-compile-args-linux"))
    extra_compile_args_darwin: List[str] = Field(default_factory=list, alias=AliasChoices("extra_compile_args_darwin", "extra-compile-args-darwin"))
    extra_compile_args_win32: List[str] = Field(default_factory=list, alias=AliasChoices("extra_compile_args_win32", "extra-compile-args-win32"))

    extra_link_args: List[str] = Field(default_factory=list, alias=AliasChoices("extra_link_args", "extra-link-args"))
    extra_link_args_linux: List[str] = Field(default_factory=list, alias=AliasChoices("extra_link_args_linux", "extra-link-args-linux"))
    extra_link_args_darwin: List[str] = Field(default_factory=list, alias=AliasChoices("extra_link_args_darwin", "extra-link-args-darwin"))
    extra_link_args_win32: List[str] = Field(default_factory=list, alias=AliasChoices("extra_link_args_win32", "extra-link-args-win32"))

    extra_objects: List[str] = Field(default_factory=list, alias=AliasChoices("extra_objects", "extra-objects"))
    extra_objects_linux: List[str] = Field(default_factory=list, alias=AliasChoices("extra_objects_linux", "extra-objects-linux"))
    extra_objects_darwin: List[str] = Field(default_factory=list, alias=AliasChoices("extra_objects_darwin", "extra-objects-darwin"))
    extra_objects_win32: List[str] = Field(default_factory=list, alias=AliasChoices("extra_objects_win32", "extra-objects-win32"))

    define_macros: List[str] = Field(default_factory=list, alias=AliasChoices("define_macros", "define-macros"))
    define_macros_linux: List[str] = Field(default_factory=list, alias=AliasChoices("define_macros_linux", "define-macros-linux"))
    define_macros_darwin: List[str] = Field(default_factory=list, alias=AliasChoices("define_macros_darwin", "define-macros-darwin"))
    define_macros_win32: List[str] = Field(default_factory=list, alias=AliasChoices("define_macros_win32", "define-macros-win32"))

    undef_macros: List[str] = Field(default_factory=list, alias=AliasChoices("undef_macros", "undef-macros"))
    undef_macros_linux: List[str] = Field(default_factory=list, alias=AliasChoices("undef_macros_linux", "undef-macros-linux"))
    undef_macros_darwin: List[str] = Field(default_factory=list, alias=AliasChoices("undef_macros_darwin", "undef-macros-darwin"))
    undef_macros_win32: List[str] = Field(default_factory=list, alias=AliasChoices("undef_macros_win32", "undef-macros-win32"))

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

    def get_effective_link_args(self, platform: Platform) -> List[str]:
        """Get link args merged with platform-specific link args."""
        args = list(self.extra_link_args)
        if platform == "linux":
            args.extend(self.extra_link_args_linux)
        elif platform == "darwin":
            args.extend(self.extra_link_args_darwin)
        elif platform == "win32":
            args.extend(self.extra_link_args_win32)
        return args

    def get_effective_include_dirs(self, platform: Platform) -> List[str]:
        """Get include dirs merged with platform-specific include dirs."""
        dirs = list(self.include_dirs)
        if platform == "linux":
            dirs.extend(self.include_dirs_linux)
        elif platform == "darwin":
            dirs.extend(self.include_dirs_darwin)
        elif platform == "win32":
            dirs.extend(self.include_dirs_win32)
        return dirs

    def get_effective_library_dirs(self, platform: Platform) -> List[str]:
        """Get library dirs merged with platform-specific library dirs."""
        dirs = list(self.library_dirs)
        if platform == "linux":
            dirs.extend(self.library_dirs_linux)
        elif platform == "darwin":
            dirs.extend(self.library_dirs_darwin)
        elif platform == "win32":
            dirs.extend(self.library_dirs_win32)
        return dirs

    def get_effective_libraries(self, platform: Platform) -> List[str]:
        """Get libraries merged with platform-specific libraries."""
        libs = list(self.libraries)
        if platform == "linux":
            libs.extend(self.libraries_linux)
        elif platform == "darwin":
            libs.extend(self.libraries_darwin)
        elif platform == "win32":
            libs.extend(self.libraries_win32)
        return libs

    def get_effective_compile_args(self, platform: Platform) -> List[str]:
        """Get compile args merged with platform-specific compile args."""
        args = list(self.extra_compile_args)
        if platform == "linux":
            args.extend(self.extra_compile_args_linux)
        elif platform == "darwin":
            args.extend(self.extra_compile_args_darwin)
        elif platform == "win32":
            args.extend(self.extra_compile_args_win32)
        return args

    def get_effective_extra_objects(self, platform: Platform) -> List[str]:
        """Get extra objects merged with platform-specific extra objects."""
        objs = list(self.extra_objects)
        if platform == "linux":
            objs.extend(self.extra_objects_linux)
        elif platform == "darwin":
            objs.extend(self.extra_objects_darwin)
        elif platform == "win32":
            objs.extend(self.extra_objects_win32)
        return objs

    def get_effective_define_macros(self, platform: Platform) -> List[str]:
        """Get define macros merged with platform-specific define macros."""
        macros = list(self.define_macros)
        if platform == "linux":
            macros.extend(self.define_macros_linux)
        elif platform == "darwin":
            macros.extend(self.define_macros_darwin)
        elif platform == "win32":
            macros.extend(self.define_macros_win32)
        return macros

    def get_effective_undef_macros(self, platform: Platform) -> List[str]:
        """Get undef macros merged with platform-specific undef macros."""
        macros = list(self.undef_macros)
        if platform == "linux":
            macros.extend(self.undef_macros_linux)
        elif platform == "darwin":
            macros.extend(self.undef_macros_darwin)
        elif platform == "win32":
            macros.extend(self.undef_macros_win32)
        return macros


class HatchCppPlatform(BaseModel):
    cc: str
    cxx: str
    ld: str
    platform: Platform
    toolchain: CompilerToolchain
    disable_ccache: bool = False

    @staticmethod
    def default() -> HatchCppPlatform:
        CC = environ.get("CC", PlatformDefaults[sys_platform]["CC"])
        CXX = environ.get("CXX", PlatformDefaults[sys_platform]["CXX"])
        LD = environ.get("LD", PlatformDefaults[sys_platform]["LD"])
        if "gcc" in CC and "g++" in CXX:
            toolchain = "gcc"
        elif "clang" in CC and "clang++" in CXX:
            toolchain = "clang"
        elif "cl" in CC and "cl" in CXX:
            toolchain = "msvc"
        # Fallback to platform defaults
        elif sys_platform == "linux":
            toolchain = "gcc"
        elif sys_platform == "darwin":
            toolchain = "clang"
        elif sys_platform == "win32":
            toolchain = "msvc"
        else:
            toolchain = "gcc"

        # TODO:
        # https://github.com/rui314/mold/issues/647
        # if which("ld.mold"):
        #     LD = which("ld.mold")
        # elif which("ld.lld"):
        #     LD = which("ld.lld")
        return HatchCppPlatform(cc=CC, cxx=CXX, ld=LD, platform=sys_platform, toolchain=toolchain)

    @model_validator(mode="wrap")
    @classmethod
    def validate_model(cls, data, handler):
        model = handler(data)
        if which("ccache") and not model.disable_ccache:
            if model.toolchain in ["gcc", "clang"]:
                if not model.cc.startswith("ccache "):
                    model.cc = f"ccache {model.cc}"
                if not model.cxx.startswith("ccache "):
                    model.cxx = f"ccache {model.cxx}"
        return model

    @staticmethod
    def platform_for_toolchain(toolchain: CompilerToolchain) -> HatchCppPlatform:
        platform = HatchCppPlatform.default()
        platform.toolchain = toolchain
        return platform

    def get_compile_flags(self, library: HatchCppLibrary, build_type: BuildType = "release") -> str:
        flags = ""

        # Get effective platform-specific values
        effective_include_dirs = library.get_effective_include_dirs(self.platform)
        effective_compile_args = library.get_effective_compile_args(self.platform)
        effective_define_macros = library.get_effective_define_macros(self.platform)
        effective_undef_macros = library.get_effective_undef_macros(self.platform)
        effective_extra_objects = library.get_effective_extra_objects(self.platform)
        effective_link_args = library.get_effective_link_args(self.platform)

        # Python.h
        if library.binding != "generic":
            effective_include_dirs.append(get_path("include"))

        if library.binding == "pybind11":
            import pybind11

            effective_include_dirs.append(pybind11.get_include())
            if not library.std:
                library.std = "c++11"
        elif library.binding == "nanobind":
            import nanobind

            effective_include_dirs.append(nanobind.include_dir())
            if not library.std:
                library.std = "c++17"
            library.sources.append(str(Path(nanobind.include_dir()).parent / "src" / "nb_combined.cpp"))
            effective_include_dirs.append(str((Path(nanobind.include_dir()).parent / "ext" / "robin_map" / "include")))

        if library.py_limited_api:
            if library.binding == "pybind11":
                raise ValueError("pybind11 does not support Py_LIMITED_API")
            effective_define_macros.append(f"Py_LIMITED_API=0x0{library.py_limited_api[2]}0{hex(int(library.py_limited_api[3:]))[2:]}00f0")

        # Toolchain-specific flags
        if self.toolchain == "gcc":
            flags += " " + " ".join(f"-I{d}" for d in effective_include_dirs)
            flags += " -fPIC"
            flags += " " + " ".join(effective_compile_args)
            flags += " " + " ".join(f"-D{macro}" for macro in effective_define_macros)
            flags += " " + " ".join(f"-U{macro}" for macro in effective_undef_macros)
            if library.std:
                flags += f" -std={library.std}"
        elif self.toolchain == "clang":
            flags += " ".join(f"-I{d}" for d in effective_include_dirs)
            flags += " -fPIC"
            flags += " " + " ".join(effective_compile_args)
            flags += " " + " ".join(f"-D{macro}" for macro in effective_define_macros)
            flags += " " + " ".join(f"-U{macro}" for macro in effective_undef_macros)
            if library.std:
                flags += f" -std={library.std}"
        elif self.toolchain == "msvc":
            flags += " ".join(f"/I{d}" for d in effective_include_dirs)
            flags += " " + " ".join(effective_compile_args)
            flags += " " + " ".join(effective_link_args)
            flags += " " + " ".join(effective_extra_objects)
            flags += " " + " ".join(f"/D{macro}" for macro in effective_define_macros)
            flags += " " + " ".join(f"/U{macro}" for macro in effective_undef_macros)
            flags += " /EHsc /DWIN32"
            if library.std:
                flags += f" /std:{library.std}"
        # clean
        while flags.count("  "):
            flags = flags.replace("  ", " ")
        return flags

    def get_link_flags(self, library: HatchCppLibrary, build_type: BuildType = "release") -> str:
        flags = ""
        effective_link_args = library.get_effective_link_args(self.platform)
        effective_extra_objects = library.get_effective_extra_objects(self.platform)
        effective_libraries = library.get_effective_libraries(self.platform)
        effective_library_dirs = library.get_effective_library_dirs(self.platform)

        if self.toolchain == "gcc":
            flags += " -shared"
            flags += " " + " ".join(effective_link_args)
            flags += " " + " ".join(effective_extra_objects)
            flags += " " + " ".join(f"-l{lib}" for lib in effective_libraries)
            flags += " " + " ".join(f"-L{lib}" for lib in effective_library_dirs)
            flags += f" -o {library.get_qualified_name(self.platform)}"
            if self.platform == "darwin":
                flags += " -undefined dynamic_lookup"
            if "mold" in self.ld:
                flags += f" -fuse-ld={self.ld}"
            elif "lld" in self.ld:
                flags += " -fuse-ld=lld"
        elif self.toolchain == "clang":
            flags += " -shared"
            flags += " " + " ".join(effective_link_args)
            flags += " " + " ".join(effective_extra_objects)
            flags += " " + " ".join(f"-l{lib}" for lib in effective_libraries)
            flags += " " + " ".join(f"-L{lib}" for lib in effective_library_dirs)
            flags += f" -o {library.get_qualified_name(self.platform)}"
            if self.platform == "darwin":
                flags += " -undefined dynamic_lookup"
            if "mold" in self.ld:
                flags += f" -fuse-ld={self.ld}"
            elif "lld" in self.ld:
                flags += " -fuse-ld=lld"
        elif self.toolchain == "msvc":
            flags += " " + " ".join(effective_link_args)
            flags += " " + " ".join(effective_extra_objects)
            flags += " /LD"
            flags += f" /Fe:{library.get_qualified_name(self.platform)}"
            flags += " /link /DLL"
            if (Path(executable).parent / "libs").exists():
                flags += f" /LIBPATH:{str(Path(executable).parent / 'libs')}"
            flags += " " + " ".join(f"{lib}.lib" for lib in effective_libraries)
            flags += " " + " ".join(f"/LIBPATH:{lib}" for lib in effective_library_dirs)
        # clean
        while flags.count("  "):
            flags = flags.replace("  ", " ")
        return flags
