"""The main plugin for hatch_cpp."""

from __future__ import annotations

import os
import typing as t
import warnings
from dataclasses import dataclass, field, fields

from hatchling.builders.config import BuilderConfig
from hatchling.builders.hooks.plugin.interface import BuildHookInterface

from .utils import (
    _get_log,
    ensure_targets,
    get_build_func,
    install_pre_commit_hook,
    normalize_kwargs,
    should_skip,
)


@dataclass
class HatchCppBuildConfig(BuilderConfig):
    """Build config values for Hatch Jupyter Builder."""

    install_pre_commit_hook: str = ""
    build_function: str | None = None
    build_kwargs: t.Mapping[str, str] = field(default_factory=dict)
    editable_build_kwargs: t.Mapping[str, str] = field(default_factory=dict)
    ensured_targets: list[str] = field(default_factory=list)
    skip_if_exists: list[str] = field(default_factory=list)
    optional_editable_build: str = ""


class HatchCppBuildHook(BuildHookInterface[HatchCppBuildConfig]):
    """The hatch-cpp build hook."""

    PLUGIN_NAME = "hatch-cpp"
    _skipped = False

    def initialize(self, version: str, _: dict[str, t.Any]) -> None:
        """Initialize the plugin."""
        self._skipped = False
        log = _get_log()
        log.info("Running hatch-cpp")
        if self.target_name not in ["wheel", "sdist"]:
            log.info("ignoring target name %s", self.target_name)
            self._skipped = True
            return

        if os.getenv("SKIP_HATCH_CPP"):
            log.info("Skipping the build hook since SKIP_HATCH_CPP was set")
            self._skipped = True
            return

        kwargs = normalize_kwargs(self.config)
        available_fields = [f.name for f in fields(HatchCppBuildConfig)]
        for key in list(kwargs):
            if key not in available_fields:
                del kwargs[key]
        config = HatchCppBuildConfig(**kwargs)

        should_install_hook = config.install_pre_commit_hook.lower() == "true"

        if version == "editable" and should_install_hook:
            install_pre_commit_hook()

        build_kwargs = config.build_kwargs
        if version == "editable":
            build_kwargs = config.editable_build_kwargs or build_kwargs

        should_skip_build = False
        if not config.build_function:
            log.warning("No build function found")
            should_skip_build = True

        elif config.skip_if_exists and version == "standard":
            should_skip_build = should_skip(config.skip_if_exists)
            if should_skip_build:
                log.info("Skip-if-exists file(s) found")

        # Get build function and call it with normalized parameter names.
        if not should_skip_build and config.build_function:
            build_func = get_build_func(config.build_function)
            build_kwargs = normalize_kwargs(build_kwargs)
            log.info("Building with %s", config.build_function)
            log.info("With kwargs: %s", build_kwargs)
            try:
                build_func(self.target_name, version, **build_kwargs)
            except Exception as e:
                if version == "editable" and config.optional_editable_build.lower() == "true":
                    warnings.warn(f"Encountered build error:\n{e}", stacklevel=2)
                else:
                    raise e
        else:
            log.info("Skipping build")

        # Ensure targets in distributable dists.
        if version == "standard":
            ensure_targets(config.ensured_targets)

        log.info("Finished running hatch-cpp")
        return
