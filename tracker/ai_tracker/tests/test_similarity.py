"""测试相似度计算"""

import pytest
from ai_tracker.similarity import line_similarity, find_best_match


class TestLineSimilarity:
    def test_identical_lines(self):
        """测试完全相同的行"""
        line1 = "print('hello world')"
        line2 = "print('hello world')"
        assert line_similarity(line1, line2) == 1.0

    def test_different_lines(self):
        """测试完全不同的行"""
        line1 = "print('hello')"
        line2 = "x = 1"
        assert line_similarity(line1, line2) < 0.3

    def test_similar_lines(self):
        """测试相似的行"""
        line1 = "print('hello world')"
        line2 = "print('hello universe')"
        similarity = line_similarity(line1, line2)
        assert similarity > 0.5
        assert similarity < 1.0

    def test_empty_lines(self):
        """测试空行"""
        assert line_similarity("", "") == 1.0
        assert line_similarity("", "x = 1") == 0.0

    def test_whitespace_differences(self):
        """测试空白字符差异"""
        line1 = "x = 1"
        line2 = "x  =  1"
        # 应该忽略多余空白
        similarity = line_similarity(line1, line2)
        assert similarity > 0.8


class TestFindBestMatch:
    def test_exact_match(self):
        """测试精确匹配"""
        content = "print('hello')"
        pool = [
            ("print('hello')", "event1"),
            ("x = 1", "event2"),
        ]
        result = find_best_match(content, pool, threshold=0.3)
        assert result is not None
        assert result[1] == "event1"
        assert result[2] == 1.0  # 相似度

    def test_no_match_below_threshold(self):
        """测试低于阈值无匹配"""
        content = "completely different line"
        pool = [
            ("print('hello')", "event1"),
            ("x = 1", "event2"),
        ]
        result = find_best_match(content, pool, threshold=0.9)
        assert result is None

    def test_empty_pool(self):
        """测试空池"""
        content = "print('hello')"
        pool = []
        result = find_best_match(content, pool, threshold=0.3)
        assert result is None

    def test_best_match_selection(self):
        """测试选择最佳匹配"""
        content = "print('hello')"
        pool = [
            ("print('hello world')", "event1"),  # 相似度较低
            ("print('hello')", "event2"),        # 相似度最高
            ("x = 1", "event3"),                 # 相似度很低
        ]
        result = find_best_match(content, pool, threshold=0.3)
        assert result is not None
        assert result[1] == "event2"  # 应该选择最相似的
