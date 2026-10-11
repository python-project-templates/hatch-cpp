from hatchling.builders.hooks.plugin.interface import BuildHookInterface
from hatchling.metadata.core import ProjectMetadata

from hatch_cpp.hooks import hatch_register_build_hook


def test_registered_build_hook_accepts_hatchling_configuration(tmp_path):
    hook_class = hatch_register_build_hook()
    config = {}
    hook = hook_class(
        root=str(tmp_path),
        config=config,
        build_config=None,
        metadata=ProjectMetadata(str(tmp_path), None, {"project": {"name": "project", "version": "0.1.0"}}),
        directory=str(tmp_path),
        target_name="wheel",
    )

    assert isinstance(hook, BuildHookInterface)
    assert hook.PLUGIN_NAME == "hatch-cpp"
    assert hook.config is config
    assert hook.target_name == "wheel"
