"""测试配置模块"""

import pytest
import os
from pathlib import Path
from ai_tracker import config


class TestFindRepoRoot:
    def test_find_repo_root_from_inside(self, tmp_path):
        """测试从仓库内部查找根目录"""
        # 创建模拟的 git 仓库
        repo_root = tmp_path / "my_repo"
        repo_root.mkdir()
        (repo_root / ".git").mkdir()

        # 从子目录查找
        subdir = repo_root / "subdir"
        subdir.mkdir()

        found = config.find_repo_root(subdir)
        assert found == repo_root

    def test_find_repo_root_from_root(self, tmp_path):
        """测试从仓库根目录查找"""
        repo_root = tmp_path / "my_repo"
        repo_root.mkdir()
        (repo_root / ".git").mkdir()

        found = config.find_repo_root(repo_root)
        assert found == repo_root

    def test_find_repo_root_not_in_repo(self, tmp_path):
        """测试不在仓库中时抛出异常"""
        not_a_repo = tmp_path / "not_a_repo"
        not_a_repo.mkdir()

        with pytest.raises(RuntimeError, match="Not inside a git repository"):
            config.find_repo_root(not_a_repo)


class TestGetContribDir:
    def test_get_contrib_dir_creates_directory(self, tmp_path):
        """测试获取贡献目录（自动创建）"""
        repo_root = tmp_path / "my_repo"
        repo_root.mkdir()
        (repo_root / ".git").mkdir()

        contrib_dir = config.get_contrib_dir(repo_root)
        assert contrib_dir == repo_root / ".ai-contributions"
        assert contrib_dir.exists()
        assert (contrib_dir / "snapshots").exists()


class TestInitPaths:
    def test_init_paths(self, tmp_path):
        """测试初始化路径"""
        repo_root = tmp_path / "my_repo"
        repo_root.mkdir()
        (repo_root / ".git").mkdir()

        config.init_paths(repo_root)

        assert config.REPO_ROOT == repo_root
        assert config.CONTRIB_DIR == repo_root / ".ai-contributions"
        assert config.EVENTS_FILE == repo_root / ".ai-contributions" / "events.jsonl"
        assert config.REPORT_FILE == repo_root / ".ai-contributions" / "report.json"


class TestThresholds:
    def test_threshold_values(self):
        """测试阈值配置"""
        assert config.THRESHOLD_AI_PURE == 0.95
        assert config.THRESHOLD_AI_MODIFIED == 0.60
        assert config.THRESHOLD_MIXED == 0.30


class TestSessionId:
    def test_session_id_from_env(self):
        """测试从环境变量获取 session ID"""
        os.environ["CLAUDE_SESSION_ID"] = "test-session-123"
        # 需要重新导入以获取新的环境变量
        import importlib
        import ai_tracker.config as cfg
        importlib.reload(cfg)
        assert cfg.SESSION_ID == "test-session-123"
        # 清理
        del os.environ["CLAUDE_SESSION_ID"]
