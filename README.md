# hatch-cpp

Hatch plugin for C++ builds

[![Build Status](https://github.com/python-project-templates/hatch-cpp/actions/workflows/build.yaml/badge.svg?branch=main&event=push)](https://github.com/python-project-templates/hatch-cpp/actions/workflows/build.yaml)
[![codecov](https://codecov.io/gh/python-project-templates/hatch-cpp/branch/main/graph/badge.svg)](https://codecov.io/gh/python-project-templates/hatch-cpp)
[![License](https://img.shields.io/github/license/python-project-templates/hatch-cpp)](https://github.com/python-project-templates/hatch-cpp)
[![PyPI](https://img.shields.io/pypi/v/hatch-cpp.svg)](https://pypi.python.org/pypi/hatch-cpp)

## Overview

A simple, extensible C++ build plugin for [hatch](https://hatch.pypa.io/latest/).

```toml
[tool.hatch.build.hooks.hatch-cpp]
libraries = [
    {name = "project/extension", sources = ["cpp/project/basic.cpp"], include-dirs = ["cpp"]}
]
```

For more complete systems, see:

- [scikit-build-core](https://github.com/scikit-build/scikit-build-core)
- [setuptools](https://setuptools.pypa.io/en/latest/userguide/ext_modules.html)

## Configuration

Configuration is driven from the `[tool.hatch.build.hooks.hatch-cpp]` hatch hook configuration field in a `pyproject.toml`.
It is designed to closely match existing Python/C/C++ packaging tools.

```toml
verbose = true
libraries = { Library Args }
cmake = { CMake Args }
platform = { Platform, either "linux", "darwin", or "win32" }
```

See the [test cases](./hatch_cpp/tests/) for more concrete examples.

`hatch-cpp` is driven by [pydantic](https://docs.pydantic.dev/latest/) models for configuration and execution of the build.
These models can themselves be overridden by setting `build-config-class` / `build-plan-class`.

### Library Arguments

```toml
name = "mylib"
sources = [
    "path/to/file.cpp",
]
language = "c++"

binding = "cpython" # or "pybind11", "nanobind", "generic"
std = "" # Passed to -std= or /std:

include_dirs = ["paths/to/add/to/-I"]
library_dirs = ["paths/to/add/to/-L"]
libraries = ["-llibraries_to_link"]

extra_compile_args = ["--extra-compile-args"]
extra_link_args = ["--extra-link-args"]
extra_objects = ["extra_objects"]

define_macros = ["-Ddefines_to_use"]
undef_macros = ["-Uundefines_to_use"]

py_limited_api = "cp39"  # limited API to use
```

### CMake Arguments

`hatch-cpp` has some convenience integration with CMake.
Though this is not designed to be as full-featured as e.g. `scikit-build`, it should be satisfactory for many small projects.

```toml
root = "path/to/cmake/root"
build = "path/to/cmake/build/folder"
install = "path/to/cmake/install/folder"

cmake_arg_prefix = "MYPROJECT_"
cmake_args = {}  # any other cmake args to pass
cmake_env_args = {} # env-specific cmake args to pass

include_flags = {} # include flags to pass -D
```

### CLI

`hatch-cpp` is integrated with [`hatch-build`](https://github.com/python-project-templates/hatch-build) to allow easy configuration of options via command line:

```bash
hatch-build \
    -- \
    --verbose \
    --platform linux \
    --vcpkg.vcpkg a/path/to/vcpkg.json \
    --libraries.0.binding pybind11 \
    --libraries.0.include-dirs cpp,another-dir
```

### Environment Variables

`hatch-cpp` will respect standard environment variables for compiler control.

| Name                       | Default | Description           |
| :------------------------- | :------ | :-------------------- |
| `CC`                       |         | C Compiler override   |
| `CXX`                      |         | C++ Compiler override |
| `LD`                       |         | Linker override       |
| `HATCH_CPP_PLATFORM`       |         | Platform to build     |
| `HATCH_CPP_DISABLE_CCACHE` |         | Disable CCache usage  |

> [!NOTE]
> This library was generated using [copier](https://copier.readthedocs.io/en/stable/) from the [Base Python Project Template repository](https://github.com/python-project-templates/base).
