from __future__ import annotations

import logging
import os
import typing as t
from dataclasses import fields

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

from .structs import HatchCppBuildConfig, HatchCppBuildPlan, HatchCppLibrary, HatchCppPlatform

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

        kwargs = {k.replace("-", "_"): v if not isinstance(v, bool) else str(v) for k, v in self.config.items()}
        available_fields = [f.name for f in fields(HatchCppBuildConfig)]
        for key in list(kwargs):
            if key not in available_fields:
                del kwargs[key]
        config = HatchCppBuildConfig(**kwargs)

        library_kwargs = [
            {k.replace("-", "_"): v if not isinstance(v, bool) else str(v) for k, v in library_kwargs.items()} for library_kwargs in config.libraries
        ]
        libraries = [HatchCppLibrary(**library_kwargs) for library_kwargs in library_kwargs]
        platform = HatchCppPlatform.default()
        if config.toolchain == "raw":
            build_plan = HatchCppBuildPlan(libraries=libraries, platform=platform)
            build_plan.generate()
            if config.verbose:
                for command in build_plan.commands:
                    self._logger.info(command)
            build_plan.execute()
            build_plan.cleanup()

        # build_kwargs = config.build_kwargs
        # if version == "editable":
        #     build_kwargs = config.editable_build_kwargs or build_kwargs

        # should_skip_build = False
        # if not config.build_function:
        #     log.warning("No build function found")
        #     should_skip_build = True

        # elif config.skip_if_exists and version == "standard":
        #     should_skip_build = should_skip(config.skip_if_exists)
        #     if should_skip_build:
        #         log.info("Skip-if-exists file(s) found")

        # # Get build function and call it with normalized parameter names.
        # if not should_skip_build and config.build_function:
        #     build_func = get_build_func(config.build_function)
        #     build_kwargs = normalize_kwargs(build_kwargs)
        #     log.info("Building with %s", config.build_function)
        #     log.info("With kwargs: %s", build_kwargs)
        #     try:
        #         build_func(self.target_name, version, **build_kwargs)
        #     except Exception as e:
        #         if version == "editable" and config.optional_editable_build.lower() == "true":
        #             warnings.warn(f"Encountered build error:\n{e}", stacklevel=2)
        #         else:
        #             raise e
        # else:
        #     log.info("Skipping build")

        # # Ensure targets in distributable dists.
        # if version == "standard":
        #     ensure_targets(config.ensured_targets)

        self._logger.info("Finished running hatch-cpp")
        return
