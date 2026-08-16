from __future__ import annotations

from os import environ
from pathlib import Path
from platform import machine as platform_machine
from sys import version_info
from typing import Any

from hatch_build import parse_extra_args_model
from hatchling.builders.hooks.plugin.interface import BuildHookInterface

from .config import HatchCppBuildConfig, HatchCppBuildPlan, log
from .utils import import_string

__all__ = ("HatchCppBuildHook",)


def _wheel_tag(platform: str, machine: str, version_major: int, version_minor: int, abi3: bool) -> str:
    if platform == "emscripten":
        abi_version = environ.get("PYODIDE_ABI_VERSION")
        if not abi_version:
            raise ValueError("PYODIDE_ABI_VERSION is required for Emscripten wheel tags.")
        return f"cp{version_major}{version_minor}-cp{version_major}{version_minor}-pyemscripten_{abi_version}_wasm32"

    if platform == "darwin":
        os_name = "macosx_11_0"
    elif platform == "linux":
        os_name = "linux"
    else:
        os_name = "win"
    abi = "abi3" if abi3 else f"cp{version_major}{version_minor}"
    return f"cp{version_major}{version_minor}-{abi}-{os_name}_{machine}"


class HatchCppBuildHook(BuildHookInterface[HatchCppBuildConfig]):
    """The hatch-cpp build hook."""

    PLUGIN_NAME = "hatch-cpp"
    _logger = log

    def initialize(self, version: str, build_data: dict[str, Any]) -> None:
        """Initialize the plugin."""
        # Log some basic information
        project_name = self.metadata.config["project"]["name"]
        self._logger.info("Initializing hatch-cpp plugin version %s", version)
        self._logger.info(f"Running hatch-cpp: {project_name}")

        # Only run if creating wheel
        # TODO: Add support for specify sdist-plan
        if self.target_name != "wheel":
            self._logger.info("ignoring target name %s", self.target_name)
            return

        # Get build config class or use default
        build_config_class = import_string(self.config["build-config-class"]) if "build-config-class" in self.config else HatchCppBuildConfig

        # Instantiate build config
        config = build_config_class(name=project_name, **self.config)

        # Get build plan class or use default
        build_plan_class = import_string(self.config["build-plan-class"]) if "build-plan-class" in self.config else HatchCppBuildPlan

        # Instantiate builder
        build_plan = build_plan_class(**config.model_dump())

        # Parse override args
        parse_extra_args_model(build_plan)

        # Generate commands
        build_plan.generate()

        # Log commands if in verbose mode
        if build_plan.verbose:
            for command in build_plan.commands:
                self._logger.warning(command)

        if build_plan.skip:
            self._logger.warning("Skipping build")
            return

        # Execute build plan
        build_plan.execute()

        # Perform any cleanup actions
        build_plan.cleanup()

        if build_plan.libraries:
            # force include libraries
            for library in build_plan.libraries:
                name = library.get_qualified_name(build_plan.platform.platform)
                build_data["force_include"][name] = name

            build_data["pure_python"] = False
            machine = platform_machine()
            version_major = version_info.major
            version_minor = version_info.minor
            build_data["tag"] = _wheel_tag(
                build_plan.platform.platform,
                machine,
                version_major,
                version_minor,
                all(lib.py_limited_api for lib in build_plan.libraries),
            )
        else:
            build_data["pure_python"] = False
            machine = platform_machine()
            version_major = version_info.major
            version_minor = version_info.minor
            build_data["tag"] = _wheel_tag(build_plan.platform.platform, machine, version_major, version_minor, False)

            # force include libraries
            for path in Path(".").rglob("*"):
                if path.is_dir():
                    continue
                if str(path).startswith(str(build_plan.cmake.build)) or str(path).startswith("dist"):
                    continue
                if path.suffix in (".pyd", ".dll", ".so", ".dylib"):
                    build_data["force_include"][str(path)] = str(path)

        for path in build_data["force_include"]:
            self._logger.info(f"Force include: {path}")
