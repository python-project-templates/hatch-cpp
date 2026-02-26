"""Tests for vcpkg ref/branch checkout support."""

from __future__ import annotations

from pathlib import Path

from hatch_cpp.toolchains.vcpkg import (
    HatchCppVcpkgConfiguration,
    _read_vcpkg_ref_from_gitmodules,
)


class TestReadVcpkgRefFromGitmodules:
    """Tests for the _read_vcpkg_ref_from_gitmodules helper."""

    def test_no_gitmodules_file(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        assert _read_vcpkg_ref_from_gitmodules(Path("vcpkg")) is None

    def test_gitmodules_without_vcpkg_submodule(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".gitmodules").write_text('[submodule "other"]\n\tpath = other\n\turl = https://github.com/example/other.git\n')
        assert _read_vcpkg_ref_from_gitmodules(Path("vcpkg")) is None

    def test_gitmodules_vcpkg_without_branch(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".gitmodules").write_text('[submodule "vcpkg"]\n\tpath = vcpkg\n\turl = https://github.com/microsoft/vcpkg.git\n')
        assert _read_vcpkg_ref_from_gitmodules(Path("vcpkg")) is None

    def test_gitmodules_vcpkg_with_branch(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".gitmodules").write_text(
            '[submodule "vcpkg"]\n\tpath = vcpkg\n\turl = https://github.com/microsoft/vcpkg.git\n\tbranch = 2024.01.12\n'
        )
        assert _read_vcpkg_ref_from_gitmodules(Path("vcpkg")) == "2024.01.12"

    def test_gitmodules_vcpkg_with_commit_sha_branch(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        sha = "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2"
        (tmp_path / ".gitmodules").write_text(
            f'[submodule "vcpkg"]\n\tpath = vcpkg\n\turl = https://github.com/microsoft/vcpkg.git\n\tbranch = {sha}\n'
        )
        assert _read_vcpkg_ref_from_gitmodules(Path("vcpkg")) == sha

    def test_gitmodules_custom_vcpkg_root(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".gitmodules").write_text(
            '[submodule "deps/vcpkg"]\n\tpath = deps/vcpkg\n\turl = https://github.com/microsoft/vcpkg.git\n\tbranch = 2024.06.15\n'
        )
        # Default vcpkg root won't match
        assert _read_vcpkg_ref_from_gitmodules(Path("vcpkg")) is None
        # Custom root matches
        assert _read_vcpkg_ref_from_gitmodules(Path("deps/vcpkg")) == "2024.06.15"

    def test_gitmodules_multiple_submodules(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".gitmodules").write_text(
            '[submodule "other"]\n'
            "\tpath = other\n"
            "\turl = https://github.com/example/other.git\n"
            "\tbranch = main\n"
            '[submodule "vcpkg"]\n'
            "\tpath = vcpkg\n"
            "\turl = https://github.com/microsoft/vcpkg.git\n"
            "\tbranch = 2024.01.12\n"
        )
        assert _read_vcpkg_ref_from_gitmodules(Path("vcpkg")) == "2024.01.12"


class TestVcpkgRefConfig:
    """Tests for vcpkg_ref configuration field."""

    def test_default_vcpkg_ref_is_none(self):
        cfg = HatchCppVcpkgConfiguration()
        assert cfg.vcpkg_ref is None

    def test_explicit_vcpkg_ref(self):
        cfg = HatchCppVcpkgConfiguration(vcpkg_ref="2024.01.12")
        assert cfg.vcpkg_ref == "2024.01.12"

    def test_explicit_vcpkg_ref_commit_sha(self):
        sha = "a1b2c3d4e5f6"
        cfg = HatchCppVcpkgConfiguration(vcpkg_ref=sha)
        assert cfg.vcpkg_ref == sha


class TestResolveVcpkgRef:
    """Tests for _resolve_vcpkg_ref priority logic."""

    def test_explicit_ref_takes_priority_over_gitmodules(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".gitmodules").write_text(
            '[submodule "vcpkg"]\n\tpath = vcpkg\n\turl = https://github.com/microsoft/vcpkg.git\n\tbranch = 2024.01.12\n'
        )
        cfg = HatchCppVcpkgConfiguration(vcpkg_ref="my-custom-tag")
        assert cfg._resolve_vcpkg_ref() == "my-custom-tag"

    def test_falls_back_to_gitmodules(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".gitmodules").write_text(
            '[submodule "vcpkg"]\n\tpath = vcpkg\n\turl = https://github.com/microsoft/vcpkg.git\n\tbranch = 2024.01.12\n'
        )
        cfg = HatchCppVcpkgConfiguration()
        assert cfg._resolve_vcpkg_ref() == "2024.01.12"

    def test_returns_none_when_no_ref(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        cfg = HatchCppVcpkgConfiguration()
        assert cfg._resolve_vcpkg_ref() is None


class TestVcpkgGenerate:
    """Tests that generate() includes the checkout command when a ref is set."""

    def _make_vcpkg_env(self, tmp_path):
        """Create a minimal vcpkg.json so generate() produces commands."""
        (tmp_path / "vcpkg.json").write_text("{}")

    def test_generate_with_explicit_ref(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        self._make_vcpkg_env(tmp_path)

        cfg = HatchCppVcpkgConfiguration(vcpkg_ref="2024.01.12")
        commands = cfg.generate(None)

        assert any("git clone" in cmd for cmd in commands)
        assert any("git -C vcpkg checkout 2024.01.12" in cmd for cmd in commands)
        # checkout must come after clone but before bootstrap
        clone_idx = next(i for i, c in enumerate(commands) if "git clone" in c)
        checkout_idx = next(i for i, c in enumerate(commands) if "checkout" in c)
        bootstrap_idx = next(i for i, c in enumerate(commands) if "bootstrap" in c)
        assert clone_idx < checkout_idx < bootstrap_idx

    def test_generate_with_gitmodules_ref(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        self._make_vcpkg_env(tmp_path)
        (tmp_path / ".gitmodules").write_text(
            '[submodule "vcpkg"]\n\tpath = vcpkg\n\turl = https://github.com/microsoft/vcpkg.git\n\tbranch = 2024.06.15\n'
        )

        cfg = HatchCppVcpkgConfiguration()
        commands = cfg.generate(None)

        assert any("git -C vcpkg checkout 2024.06.15" in cmd for cmd in commands)

    def test_generate_without_ref(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        self._make_vcpkg_env(tmp_path)

        cfg = HatchCppVcpkgConfiguration()
        commands = cfg.generate(None)

        assert not any("checkout" in cmd for cmd in commands)
        assert any("git clone" in cmd for cmd in commands)

    def test_generate_skips_clone_when_vcpkg_root_exists(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        self._make_vcpkg_env(tmp_path)
        (tmp_path / "vcpkg").mkdir()

        cfg = HatchCppVcpkgConfiguration(vcpkg_ref="2024.01.12")
        commands = cfg.generate(None)

        # When vcpkg_root already exists, no clone or checkout happens
        assert not any("git clone" in cmd for cmd in commands)
        assert not any("checkout" in cmd for cmd in commands)
        assert any("vcpkg" in cmd and "install" in cmd for cmd in commands)

    def test_generate_no_vcpkg_json(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        # No vcpkg.json => no commands at all
        cfg = HatchCppVcpkgConfiguration(vcpkg_ref="2024.01.12")
        commands = cfg.generate(None)
        assert commands == []
