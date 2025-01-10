# hatch-cpp

Hatch plugin for C++ builds

[![Build Status](https://github.com/python-project-templates/hatch-cpp/actions/workflows/build.yml/badge.svg?branch=main&event=push)](https://github.com/python-project-templates/hatch-cpp/actions/workflows/build.yml)
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

## Environment Variables
| Name | Default | Description |
|:-----|:--------|:------------|
|`CC`| | |
|`CXX`| | |
|`LD`| | |
|`HATCH_CPP_PLATFORM`| | |
|`HATCH_CPP_DISABLE_CCACHE`| | |

> [!NOTE]
> This library was generated using [copier](https://copier.readthedocs.io/en/stable/) from the [Base Python Project Template repository](https://github.com/python-project-templates/base).
