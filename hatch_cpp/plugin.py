from __future__ import annotations

import logging
import os
import typing as t

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

from .structs import HatchCppBuildConfig, HatchCppBuildPlan
from .utils import import_string

__all__ = ("HatchCppBuildHook",)


class HatchCppBuildHook(BuildHookInterface[HatchCppBuildConfig]):
    """The hatch-cpp build hook."""

    PLUGIN_NAME = "hatch-cpp"
    _logger = logging.getLogger(__name__)

    def initialize(self, version: str, _: dict[str, t.Any]) -> None:
        """Initialize the plugin."""
        # Log some basic information
        self._logger.info("Initializing hatch-cpp plugin version %s", version)
        self._logger.info("Running hatch-cpp")

        # Only run if creating wheel
        # TODO: Add support for specify sdist-plan
        if self.target_name != "wheel":
            self._logger.info("ignoring target name %s", self.target_name)
            return

        # Skip if SKIP_HATCH_CPP is set
        # TODO: Support CLI once https://github.com/pypa/hatch/pull/1743
        if os.getenv("SKIP_HATCH_CPP"):
            self._logger.info("Skipping the build hook since SKIP_HATCH_CPP was set")
            return

        # Get build config class or use default
        build_config_class = import_string(self.config["build-config-class"]) if "build-config-class" in self.config else HatchCppBuildConfig

        # Instantiate build config
        config = build_config_class(**self.config)

        # Grab libraries and platform
        libraries = config.libraries
        platform = config.platform

        # Get build plan class or use default
        build_plan_class = import_string(self.config["build-plan-class"]) if "build-plan-class" in self.config else HatchCppBuildPlan

        # Instantiate builder
        build_plan = build_plan_class(libraries=libraries, platform=platform)

        # Generate commands
        build_plan.generate()

        # Log commands if in verbose mode
        if config.verbose:
            for command in build_plan.commands:
                self._logger.warning(command)

        # Execute build plan
        build_plan.execute()

        # Perform any cleanup actions
        build_plan.cleanup()
