"""跨平台路径与配置常量"""

import os
from pathlib import Path


def _load_env() -> dict:
    """
    从 .env 文件加载配置（零依赖，标准库实现）。
    优先级：环境变量 > .env 文件 > 默认值。
    """
    env = {}
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                env[key.strip()] = value.strip().strip('"').strip("'")
    return env


_ENV = _load_env()


def get_env(key: str, default: str = "") -> str:
    """获取配置值：环境变量 > .env 文件 > 默认值"""
    return os.environ.get(key) or _ENV.get(key, default)


def find_repo_root(start: Path = None) -> Path:
    """向上查找 .git 目录，确定仓库根目录"""
    current = (start or Path.cwd()).resolve()
    while current != current.parent:
        if (current / ".git").exists():
            return current
        current = current.parent
    raise RuntimeError("Not inside a git repository")


def get_contrib_dir(repo_root: Path = None) -> Path:
    """获取 .ai-contributions 目录路径（自动创建）"""
    root = repo_root or find_repo_root()
    contrib_dir = root / ".ai-contributions"
    contrib_dir.mkdir(exist_ok=True)
    (contrib_dir / "snapshots").mkdir(exist_ok=True)
    return contrib_dir


# 路径常量（延迟初始化）
REPO_ROOT = None
CONTRIB_DIR = None
EVENTS_FILE = None
REPORT_FILE = None


def init_paths(repo_root: Path = None):
    global REPO_ROOT, CONTRIB_DIR, EVENTS_FILE, REPORT_FILE
    REPO_ROOT = repo_root or find_repo_root()
    CONTRIB_DIR = get_contrib_dir(REPO_ROOT)
    EVENTS_FILE = CONTRIB_DIR / "events.jsonl"
    REPORT_FILE = CONTRIB_DIR / "report.json"


# 服务器地址（所有人共用同一个后端，零配置）
# 优先级：环境变量 > .env 文件 > 默认值
DEFAULT_SERVER_URL = get_env("AI_TRACKER_SERVER", "http://localhost:8000")

# 相似度阈值配置
THRESHOLD_AI_PURE = 0.95        # > 95% 相似 → 纯 AI
THRESHOLD_AI_MODIFIED = 0.60    # > 60% 相似 → AI 修改版
THRESHOLD_MIXED = 0.30          # > 30% 相似 → 混合贡献
# < 30% → 视为人工贡献

# Session ID（每次 Claude Code 启动时生成）
SESSION_ID = get_env("CLAUDE_SESSION_ID", "")
