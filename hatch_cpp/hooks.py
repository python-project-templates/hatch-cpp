from hatchling.plugin import hookimpl

from .plugin import HatchCppBuildHook


@hookimpl
def hatch_register_build_hook() -> type[HatchCppBuildHook]:
    return HatchCppBuildHook
