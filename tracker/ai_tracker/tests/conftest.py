"""Pytest 配置"""

import pytest


@pytest.fixture
def tmp_path(tmp_path):
    """提供临时目录路径"""
    return tmp_path
