"""测试事件存储模块"""

import pytest
import json
from pathlib import Path
from ai_tracker.models import Event, LineDiff
from ai_tracker import event_store, config


class TestNormalizeRelPath:
    def test_absolute_path(self, tmp_path):
        """测试绝对路径转换"""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        abs_path = repo_root / "src" / "test.py"
        abs_path.parent.mkdir(parents=True)

        rel_path = event_store._normalize_rel_path(str(abs_path), repo_root)
        assert rel_path == "src/test.py"

    def test_relative_path(self, tmp_path):
        """测试相对路径"""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()

        rel_path = event_store._normalize_rel_path("src/test.py", repo_root)
        assert rel_path == "src/test.py"


class TestComputeFileHash:
    def test_compute_hash_existing_file(self, tmp_path):
        """测试计算现有文件的哈希"""
        test_file = tmp_path / "test.txt"
        test_file.write_text("hello world")

        hash_value = event_store._compute_file_hash(test_file)
        assert len(hash_value) == 64  # SHA256 hex digest

    def test_compute_hash_nonexistent_file(self):
        """测试计算不存在文件的哈希"""
        nonexistent = Path("/nonexistent/file.txt")
        hash_value = event_store._compute_file_hash(nonexistent)
        assert hash_value == ""


class TestSaveEvent:
    def test_save_event(self, tmp_path, monkeypatch):
        """测试保存事件"""
        # 设置临时目录作为仓库根目录
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        (repo_root / ".git").mkdir()
        (repo_root / ".ai-contributions").mkdir()

        # 模拟配置
        monkeypatch.setattr(config, "REPO_ROOT", repo_root)
        monkeypatch.setattr(config, "CONTRIB_DIR", repo_root / ".ai-contributions")
        monkeypatch.setattr(config, "EVENTS_FILE", repo_root / ".ai-contributions" / "events.jsonl")

        event = Event(
            session_id="test-session",
            operation="write",
            file_path="test.py",
            diff=LineDiff(added={1: "print('hello')"}),
        )

        event_store.save_event(event, repo_root)

        # 验证事件已保存
        events_file = repo_root / ".ai-contributions" / "events.jsonl"
        assert events_file.exists()

        with open(events_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
            assert len(lines) == 1
            saved_event = json.loads(lines[0])
            assert saved_event["operation"] == "write"
            assert saved_event["file_path"] == "test.py"


class TestLoadEvents:
    def test_load_events_empty(self, tmp_path, monkeypatch):
        """测试加载空事件列表"""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        (repo_root / ".git").mkdir()
        (repo_root / ".ai-contributions").mkdir()

        monkeypatch.setattr(config, "REPO_ROOT", repo_root)
        monkeypatch.setattr(config, "CONTRIB_DIR", repo_root / ".ai-contributions")
        monkeypatch.setattr(config, "EVENTS_FILE", repo_root / ".ai-contributions" / "events.jsonl")

        events = event_store.load_events(repo_root)
        assert events == []

    def test_load_events_with_data(self, tmp_path, monkeypatch):
        """测试加载事件数据"""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        (repo_root / ".git").mkdir()
        contrib_dir = repo_root / ".ai-contributions"
        contrib_dir.mkdir()

        events_file = contrib_dir / "events.jsonl"
        event_data = {
            "id": "test123",
            "timestamp": "2026-01-01T00:00:00+00:00",
            "session_id": "test-session",
            "operation": "write",
            "file_path": "test.py",
            "diff": {"added": {"1": "line1"}, "removed": {}},
            "snapshot_path": "",
            "file_hash_after": "",
        }
        events_file.write_text(json.dumps(event_data) + "\n")

        monkeypatch.setattr(config, "REPO_ROOT", repo_root)
        monkeypatch.setattr(config, "CONTRIB_DIR", contrib_dir)
        monkeypatch.setattr(config, "EVENTS_FILE", events_file)

        events = event_store.load_events(repo_root)
        assert len(events) == 1
        assert events[0].id == "test123"
        assert events[0].operation == "write"


class TestSaveSnapshot:
    def test_save_snapshot(self, tmp_path, monkeypatch):
        """测试保存快照"""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        (repo_root / ".git").mkdir()
        contrib_dir = repo_root / ".ai-contributions"
        contrib_dir.mkdir()

        monkeypatch.setattr(config, "REPO_ROOT", repo_root)
        monkeypatch.setattr(config, "CONTRIB_DIR", contrib_dir)

        # 创建测试文件
        test_file = tmp_path / "test.txt"
        test_file.write_text("hello world")

        snapshot_path = event_store.save_snapshot(test_file, "event123", repo_root)

        assert snapshot_path.endswith("event123_test.txt")
        assert Path(snapshot_path).exists()
        assert Path(snapshot_path).read_text() == "hello world"


class TestLoadSnapshot:
    def test_load_snapshot(self, tmp_path):
        """测试加载快照"""
        snap_file = tmp_path / "snapshot.txt"
        snap_file.write_text("line1\nline2\nline3")

        lines = event_store.load_snapshot(str(snap_file))
        assert lines == ["line1", "line2", "line3"]

    def test_load_nonexistent_snapshot(self):
        """测试加载不存在的快照"""
        lines = event_store.load_snapshot("/nonexistent/snapshot.txt")
        assert lines is None
