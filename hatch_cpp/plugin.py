from __future__ import annotations

import logging
import os
import typing as t

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

from .structs import HatchCppBuildConfig, HatchCppBuildPlan

__all__ = ("HatchCppBuildHook",)


class HatchCppBuildHook(BuildHookInterface[HatchCppBuildConfig]):
    """The hatch-cpp build hook."""

    PLUGIN_NAME = "hatch-cpp"
    _logger = logging.getLogger(__name__)

    def initialize(self, version: str, _: dict[str, t.Any]) -> None:
        """Initialize the plugin."""
        self._logger.info("Running hatch-cpp")

        if self.target_name != "wheel":
            self._logger.info("ignoring target name %s", self.target_name)
            return

        if os.getenv("SKIP_HATCH_CPP"):
            self._logger.info("Skipping the build hook since SKIP_HATCH_CPP was set")
            return

        config = HatchCppBuildConfig(**self.config)

        libraries = config.libraries
        platform = config.platform
        if config.toolchain == "raw":
            build_plan = HatchCppBuildPlan(libraries=libraries, platform=platform)
            build_plan.generate()
            if config.verbose:
                for command in build_plan.commands:
                    self._logger.info(command)
            build_plan.execute()
            build_plan.cleanup()

        self._logger.info("Finished running hatch-cpp")
        return
