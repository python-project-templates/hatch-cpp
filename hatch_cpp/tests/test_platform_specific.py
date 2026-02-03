"""Tests for platform-specific library configuration fields."""

from hatch_cpp import HatchCppLibrary, HatchCppPlatform


class TestPlatformSpecificFields:
    """Test suite for platform-specific field handling in HatchCppLibrary."""

    def test_effective_include_dirs(self):
        """Test that include_dirs are properly merged with platform-specific dirs."""
        library = HatchCppLibrary(
            name="test",
            sources=["test.cpp"],
            include_dirs=["common/include"],
            include_dirs_linux=["linux/include"],
            include_dirs_darwin=["darwin/include"],
            include_dirs_win32=["win32/include"],
        )

        linux_dirs = library.get_effective_include_dirs("linux")
        assert "common/include" in linux_dirs
        assert "linux/include" in linux_dirs
        assert "darwin/include" not in linux_dirs
        assert "win32/include" not in linux_dirs

        darwin_dirs = library.get_effective_include_dirs("darwin")
        assert "common/include" in darwin_dirs
        assert "darwin/include" in darwin_dirs
        assert "linux/include" not in darwin_dirs

        win32_dirs = library.get_effective_include_dirs("win32")
        assert "common/include" in win32_dirs
        assert "win32/include" in win32_dirs
        assert "linux/include" not in win32_dirs

    def test_effective_library_dirs(self):
        """Test that library_dirs are properly merged with platform-specific dirs."""
        library = HatchCppLibrary(
            name="test",
            sources=["test.cpp"],
            library_dirs=["common/lib"],
            library_dirs_linux=["linux/lib"],
            library_dirs_darwin=["darwin/lib"],
            library_dirs_win32=["win32/lib"],
        )

        linux_dirs = library.get_effective_library_dirs("linux")
        assert "common/lib" in linux_dirs
        assert "linux/lib" in linux_dirs
        assert "darwin/lib" not in linux_dirs

        darwin_dirs = library.get_effective_library_dirs("darwin")
        assert "common/lib" in darwin_dirs
        assert "darwin/lib" in darwin_dirs

        win32_dirs = library.get_effective_library_dirs("win32")
        assert "common/lib" in win32_dirs
        assert "win32/lib" in win32_dirs

    def test_effective_libraries(self):
        """Test that libraries are properly merged with platform-specific libraries."""
        library = HatchCppLibrary(
            name="test",
            sources=["test.cpp"],
            libraries=["common"],
            libraries_linux=["pthread", "dl"],
            libraries_darwin=["objc"],
            libraries_win32=["kernel32", "user32"],
        )

        linux_libs = library.get_effective_libraries("linux")
        assert "common" in linux_libs
        assert "pthread" in linux_libs
        assert "dl" in linux_libs
        assert "objc" not in linux_libs

        darwin_libs = library.get_effective_libraries("darwin")
        assert "common" in darwin_libs
        assert "objc" in darwin_libs
        assert "pthread" not in darwin_libs

        win32_libs = library.get_effective_libraries("win32")
        assert "common" in win32_libs
        assert "kernel32" in win32_libs
        assert "user32" in win32_libs
        assert "pthread" not in win32_libs

    def test_effective_compile_args(self):
        """Test that extra_compile_args are properly merged with platform-specific args."""
        library = HatchCppLibrary(
            name="test",
            sources=["test.cpp"],
            extra_compile_args=["-O2"],
            extra_compile_args_linux=["-march=native"],
            extra_compile_args_darwin=["-mmacosx-version-min=11"],
            extra_compile_args_win32=["/O2"],
        )

        linux_args = library.get_effective_compile_args("linux")
        assert "-O2" in linux_args
        assert "-march=native" in linux_args
        assert "-mmacosx-version-min=11" not in linux_args

        darwin_args = library.get_effective_compile_args("darwin")
        assert "-O2" in darwin_args
        assert "-mmacosx-version-min=11" in darwin_args

        win32_args = library.get_effective_compile_args("win32")
        assert "-O2" in win32_args
        assert "/O2" in win32_args

    def test_effective_link_args(self):
        """Test that extra_link_args are properly merged with platform-specific args."""
        library = HatchCppLibrary(
            name="test",
            sources=["test.cpp"],
            extra_link_args=["-shared"],
            extra_link_args_linux=["-Wl,-rpath,$ORIGIN/lib"],
            extra_link_args_darwin=["-Wl,-rpath,@loader_path/lib"],
            extra_link_args_win32=["/NODEFAULTLIB"],
        )

        linux_args = library.get_effective_link_args("linux")
        assert "-shared" in linux_args
        assert "-Wl,-rpath,$ORIGIN/lib" in linux_args
        assert "-Wl,-rpath,@loader_path/lib" not in linux_args

        darwin_args = library.get_effective_link_args("darwin")
        assert "-shared" in darwin_args
        assert "-Wl,-rpath,@loader_path/lib" in darwin_args

        win32_args = library.get_effective_link_args("win32")
        assert "-shared" in win32_args
        assert "/NODEFAULTLIB" in win32_args

    def test_effective_extra_objects(self):
        """Test that extra_objects are properly merged with platform-specific objects."""
        library = HatchCppLibrary(
            name="test",
            sources=["test.cpp"],
            extra_objects=["common.o"],
            extra_objects_linux=["linux.o"],
            extra_objects_darwin=["darwin.o"],
            extra_objects_win32=["win32.obj"],
        )

        linux_objs = library.get_effective_extra_objects("linux")
        assert "common.o" in linux_objs
        assert "linux.o" in linux_objs
        assert "darwin.o" not in linux_objs

        darwin_objs = library.get_effective_extra_objects("darwin")
        assert "common.o" in darwin_objs
        assert "darwin.o" in darwin_objs

        win32_objs = library.get_effective_extra_objects("win32")
        assert "common.o" in win32_objs
        assert "win32.obj" in win32_objs

    def test_effective_define_macros(self):
        """Test that define_macros are properly merged with platform-specific macros."""
        library = HatchCppLibrary(
            name="test",
            sources=["test.cpp"],
            define_macros=["COMMON=1"],
            define_macros_linux=["LINUX=1", "_GNU_SOURCE"],
            define_macros_darwin=["DARWIN=1", "__APPLE__"],
            define_macros_win32=["WIN32=1", "_WINDOWS"],
        )

        linux_macros = library.get_effective_define_macros("linux")
        assert "COMMON=1" in linux_macros
        assert "LINUX=1" in linux_macros
        assert "_GNU_SOURCE" in linux_macros
        assert "DARWIN=1" not in linux_macros

        darwin_macros = library.get_effective_define_macros("darwin")
        assert "COMMON=1" in darwin_macros
        assert "DARWIN=1" in darwin_macros
        assert "__APPLE__" in darwin_macros

        win32_macros = library.get_effective_define_macros("win32")
        assert "COMMON=1" in win32_macros
        assert "WIN32=1" in win32_macros
        assert "_WINDOWS" in win32_macros

    def test_effective_undef_macros(self):
        """Test that undef_macros are properly merged with platform-specific macros."""
        library = HatchCppLibrary(
            name="test",
            sources=["test.cpp"],
            undef_macros=["COMMON_UNDEF"],
            undef_macros_linux=["LINUX_UNDEF"],
            undef_macros_darwin=["DARWIN_UNDEF"],
            undef_macros_win32=["WIN32_UNDEF"],
        )

        linux_macros = library.get_effective_undef_macros("linux")
        assert "COMMON_UNDEF" in linux_macros
        assert "LINUX_UNDEF" in linux_macros
        assert "DARWIN_UNDEF" not in linux_macros

        darwin_macros = library.get_effective_undef_macros("darwin")
        assert "COMMON_UNDEF" in darwin_macros
        assert "DARWIN_UNDEF" in darwin_macros

        win32_macros = library.get_effective_undef_macros("win32")
        assert "COMMON_UNDEF" in win32_macros
        assert "WIN32_UNDEF" in win32_macros

    def test_empty_platform_specific_fields(self):
        """Test that empty platform-specific fields don't cause issues."""
        library = HatchCppLibrary(
            name="test",
            sources=["test.cpp"],
            include_dirs=["common/include"],
            # No platform-specific fields set
        )

        linux_dirs = library.get_effective_include_dirs("linux")
        assert linux_dirs == ["common/include"]

        darwin_dirs = library.get_effective_include_dirs("darwin")
        assert darwin_dirs == ["common/include"]

        win32_dirs = library.get_effective_include_dirs("win32")
        assert win32_dirs == ["common/include"]

    def test_only_platform_specific_fields(self):
        """Test that only platform-specific fields work without common fields."""
        library = HatchCppLibrary(
            name="test",
            sources=["test.cpp"],
            # No common include_dirs
            include_dirs_linux=["linux/include"],
            include_dirs_darwin=["darwin/include"],
        )

        linux_dirs = library.get_effective_include_dirs("linux")
        assert linux_dirs == ["linux/include"]

        darwin_dirs = library.get_effective_include_dirs("darwin")
        assert darwin_dirs == ["darwin/include"]

        win32_dirs = library.get_effective_include_dirs("win32")
        assert win32_dirs == []

    def test_alias_hyphenated_names(self):
        """Test that hyphenated field names work as aliases."""
        library = HatchCppLibrary(
            name="test",
            sources=["test.cpp"],
            **{
                "include-dirs": ["common/include"],
                "include-dirs-linux": ["linux/include"],
                "library-dirs-darwin": ["darwin/lib"],
                "extra-compile-args-win32": ["/O2"],
                "extra-link-args-linux": ["-Wl,-rpath,$ORIGIN"],
                "define-macros-darwin": ["DARWIN=1"],
                "undef-macros-win32": ["NDEBUG"],
            },
        )

        assert library.include_dirs == ["common/include"]
        assert library.include_dirs_linux == ["linux/include"]
        assert library.library_dirs_darwin == ["darwin/lib"]
        assert library.extra_compile_args_win32 == ["/O2"]
        assert library.extra_link_args_linux == ["-Wl,-rpath,$ORIGIN"]
        assert library.define_macros_darwin == ["DARWIN=1"]
        assert library.undef_macros_win32 == ["NDEBUG"]


class TestPlatformFlagsIntegration:
    """Integration tests for platform-specific fields in compile/link flags."""

    def test_compile_flags_include_platform_specific_include_dirs(self):
        """Test that get_compile_flags includes platform-specific include dirs."""
        library = HatchCppLibrary(
            name="test",
            sources=["test.cpp"],
            binding="generic",
            include_dirs=["common/include"],
            include_dirs_linux=["linux/include"],
        )

        # Create a mock linux platform
        platform = HatchCppPlatform(cc="gcc", cxx="g++", ld="ld", platform="linux", toolchain="gcc", disable_ccache=True)

        flags = platform.get_compile_flags(library)
        assert "-Icommon/include" in flags
        assert "-Ilinux/include" in flags

    def test_compile_flags_include_platform_specific_macros(self):
        """Test that get_compile_flags includes platform-specific define/undef macros."""
        library = HatchCppLibrary(
            name="test",
            sources=["test.cpp"],
            binding="generic",
            define_macros=["COMMON=1"],
            define_macros_linux=["LINUX_SPECIFIC=1"],
            undef_macros=["OLD_MACRO"],
            undef_macros_linux=["LINUX_OLD"],
        )

        platform = HatchCppPlatform(cc="gcc", cxx="g++", ld="ld", platform="linux", toolchain="gcc", disable_ccache=True)

        flags = platform.get_compile_flags(library)
        assert "-DCOMMON=1" in flags
        assert "-DLINUX_SPECIFIC=1" in flags
        assert "-UOLD_MACRO" in flags
        assert "-ULINUX_OLD" in flags

    def test_link_flags_include_platform_specific_libraries(self):
        """Test that get_link_flags includes platform-specific libraries."""
        library = HatchCppLibrary(
            name="test",
            sources=["test.cpp"],
            binding="generic",
            libraries=["common"],
            libraries_linux=["pthread", "dl"],
            library_dirs=["common/lib"],
            library_dirs_linux=["linux/lib"],
        )

        platform = HatchCppPlatform(cc="gcc", cxx="g++", ld="ld", platform="linux", toolchain="gcc", disable_ccache=True)

        flags = platform.get_link_flags(library)
        assert "-lcommon" in flags
        assert "-lpthread" in flags
        assert "-ldl" in flags
        assert "-Lcommon/lib" in flags
        assert "-Llinux/lib" in flags

    def test_link_flags_include_platform_specific_link_args(self):
        """Test that get_link_flags includes platform-specific extra_link_args."""
        library = HatchCppLibrary(
            name="test",
            sources=["test.cpp"],
            binding="generic",
            extra_link_args=["-shared"],
            extra_link_args_linux=["-Wl,-rpath,$ORIGIN/lib"],
        )

        platform = HatchCppPlatform(cc="gcc", cxx="g++", ld="ld", platform="linux", toolchain="gcc", disable_ccache=True)

        flags = platform.get_link_flags(library)
        assert "-shared" in flags
        assert "-Wl,-rpath,$ORIGIN/lib" in flags

    def test_darwin_platform_uses_darwin_specific_fields(self):
        """Test that darwin platform uses darwin-specific fields."""
        library = HatchCppLibrary(
            name="test",
            sources=["test.cpp"],
            binding="generic",
            libraries_linux=["pthread"],
            libraries_darwin=["objc"],
            extra_link_args_darwin=["-Wl,-rpath,@loader_path/lib"],
        )

        platform = HatchCppPlatform(cc="clang", cxx="clang++", ld="ld", platform="darwin", toolchain="clang", disable_ccache=True)

        flags = platform.get_link_flags(library)
        assert "-lobjc" in flags
        assert "-lpthread" not in flags
        assert "-Wl,-rpath,@loader_path/lib" in flags

    def test_win32_platform_uses_win32_specific_fields(self):
        """Test that win32 platform uses win32-specific fields."""
        library = HatchCppLibrary(
            name="test",
            sources=["test.cpp"],
            binding="generic",
            libraries=["common"],
            libraries_win32=["kernel32"],
            library_dirs=["common/lib"],
            library_dirs_win32=["win32/lib"],
        )

        platform = HatchCppPlatform(cc="cl", cxx="cl", ld="link", platform="win32", toolchain="msvc", disable_ccache=True)

        flags = platform.get_link_flags(library)
        assert "common.lib" in flags
        assert "kernel32.lib" in flags
        assert "/LIBPATH:common/lib" in flags
        assert "/LIBPATH:win32/lib" in flags

    def test_msvc_compile_flags_use_platform_specific_fields(self):
        """Test that MSVC compile flags include platform-specific fields."""
        library = HatchCppLibrary(
            name="test",
            sources=["test.cpp"],
            binding="generic",
            include_dirs=["common/include"],
            include_dirs_win32=["win32/include"],
            define_macros=["COMMON=1"],
            define_macros_win32=["_WINDOWS"],
            extra_compile_args_win32=["/W4"],
        )

        platform = HatchCppPlatform(cc="cl", cxx="cl", ld="link", platform="win32", toolchain="msvc", disable_ccache=True)

        flags = platform.get_compile_flags(library)
        assert "/Icommon/include" in flags
        assert "/Iwin32/include" in flags
        assert "/DCOMMON=1" in flags
        assert "/D_WINDOWS" in flags
        assert "/W4" in flags


class TestPlatformFieldOrdering:
    """Test that platform-specific fields are appended after common fields."""

    def test_include_dirs_ordering(self):
        """Test that platform-specific include dirs come after common dirs."""
        library = HatchCppLibrary(
            name="test",
            sources=["test.cpp"],
            include_dirs=["first", "second"],
            include_dirs_linux=["third", "fourth"],
        )

        dirs = library.get_effective_include_dirs("linux")
        assert dirs == ["first", "second", "third", "fourth"]

    def test_libraries_ordering(self):
        """Test that platform-specific libraries come after common libraries."""
        library = HatchCppLibrary(
            name="test",
            sources=["test.cpp"],
            libraries=["common1", "common2"],
            libraries_linux=["linux1", "linux2"],
        )

        libs = library.get_effective_libraries("linux")
        assert libs == ["common1", "common2", "linux1", "linux2"]

    def test_base_list_not_mutated(self):
        """Test that the base lists are not mutated when getting effective values."""
        library = HatchCppLibrary(
            name="test",
            sources=["test.cpp"],
            include_dirs=["common"],
            include_dirs_linux=["linux"],
        )

        # Get effective dirs multiple times
        dirs1 = library.get_effective_include_dirs("linux")
        dirs2 = library.get_effective_include_dirs("linux")

        # Both should be equal
        assert dirs1 == dirs2

        # Base list should not be modified
        assert library.include_dirs == ["common"]
        assert library.include_dirs_linux == ["linux"]
