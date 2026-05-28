"""测试数据模型"""

import pytest
from datetime import datetime, timezone
from ai_tracker.models import Event, LineDiff, LineAttribution, FileAttribution, AnalysisResult


class TestLineDiff:
    def test_line_diff_default(self):
        """测试 LineDiff 默认值"""
        diff = LineDiff()
        assert diff.added == {}
        assert diff.removed == {}


class TestEvent:
    def test_event_creation(self):
        """测试 Event 创建"""
        event = Event(
            session_id="test-session",
            operation="write",
            file_path="test.py",
            diff=LineDiff(added={1: "print('hello')"}),
        )
        assert event.operation == "write"
        assert event.file_path == "test.py"
        assert event.diff.added == {1: "print('hello')"}

    def test_event_to_dict(self):
        """测试 Event 转字典"""
        event = Event(
            session_id="test-session",
            operation="write",
            file_path="test.py",
            diff=LineDiff(added={1: "line1"}),
        )
        d = event.to_dict()
        assert d["operation"] == "write"
        assert d["file_path"] == "test.py"
        # to_dict() 将行号转换为字符串键
        assert d["diff"]["added"] == {"1": "line1"}

    def test_event_from_dict(self):
        """测试从字典创建 Event"""
        d = {
            "id": "test123",
            "timestamp": "2026-01-01T00:00:00+00:00",
            "session_id": "test-session",
            "operation": "write",
            "file_path": "test.py",
            "diff": {"added": {"1": "line1"}, "removed": {}},
            "snapshot_path": "",
            "file_hash_after": "",
        }
        event = Event.from_dict(d)
        assert event.id == "test123"
        assert event.operation == "write"
        assert event.file_path == "test.py"
        assert event.diff.added == {1: "line1"}


class TestLineAttribution:
    def test_line_attribution_creation(self):
        """测试 LineAttribution 创建"""
        la = LineAttribution(
            line_number=1,
            content="test line",
            source="ai_pure",
            ai_ratio=1.0,
        )
        assert la.line_number == 1
        assert la.source == "ai_pure"
        assert la.ai_ratio == 1.0


class TestFileAttribution:
    def test_file_attribution_creation(self):
        """测试 FileAttribution 创建"""
        fa = FileAttribution(file_path="test.py")
        assert fa.file_path == "test.py"
        assert fa.total_lines == 0

    def test_ai_contribution_ratio(self):
        """测试 AI 贡献率计算"""
        fa = FileAttribution(
            file_path="test.py",
            total_lines=10,
            ai_weighted_sum=5.0,
        )
        assert fa.ai_contribution_ratio == 0.5

    def test_ai_contribution_ratio_empty(self):
        """测试空文件的 AI 贡献率"""
        fa = FileAttribution(file_path="test.py")
        assert fa.ai_contribution_ratio == 0.0


class TestAnalysisResult:
    def test_analysis_result_creation(self):
        """测试 AnalysisResult 创建"""
        result = AnalysisResult()
        assert result.files == []
        assert result.ai_events_count == 0

    def test_analysis_result_properties(self):
        """测试 AnalysisResult 属性计算"""
        result = AnalysisResult()
        result.files = [
            FileAttribution(file_path="test1.py", ai_pure_lines=5, ai_modified_lines=3, mixed_lines=2, human_lines=10),
            FileAttribution(file_path="test2.py", ai_pure_lines=2, ai_modified_lines=1, mixed_lines=0, human_lines=5),
        ]
        result.deleted_ai = [None] * 3  # 3 个删除的 AI 行

        assert result.ai_pure_total == 7
        assert result.ai_modified_total == 4
        assert result.mixed_total == 2
        assert result.human_total == 15
        assert result.deleted_ai_total == 3

    def test_generation_rate(self):
        """测试 AI 生成率计算"""
        result = AnalysisResult()
        result.total_push_lines = 100
        result.files = [
            FileAttribution(file_path="test.py", ai_pure_lines=50, ai_modified_lines=20, mixed_lines=10, human_lines=20),
        ]
        # ai_generated = 50 + 20 + 10 = 80
        assert result.generation_rate == 0.8

    def test_generation_rate_empty(self):
        """测试空文件的生成率"""
        result = AnalysisResult()
        result.total_push_lines = 0
        assert result.generation_rate == 0.0

    def test_retention_rate(self):
        """测试 AI 存活率计算"""
        result = AnalysisResult()
        result.files = [
            FileAttribution(file_path="test.py", ai_pure_lines=10, ai_modified_lines=5, mixed_lines=5, human_lines=10),
        ]
        result.deleted_ai = [None] * 3  # 3 个删除的 AI 行
        # retained = 10 + 5 + 5 * 0.5 = 17.5
        # total_generated = 17.5 + 3 = 20.5
        # retention_rate = 17.5 / 20.5 ≈ 0.8537
        assert abs(result.retention_rate - 0.8537) < 0.01

    def test_net_contribution(self):
        """测试 AI 净贡献率计算"""
        result = AnalysisResult()
        result.total_push_lines = 100
        result.files = [
            FileAttribution(file_path="test.py", total_lines=100, ai_weighted_sum=60.0),
        ]
        assert result.net_contribution == 0.6

    def test_net_contribution_empty(self):
        """测试空文件的净贡献率"""
        result = AnalysisResult()
        result.total_push_lines = 0
        assert result.net_contribution == 0.0
