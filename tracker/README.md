# AI Code Contribution Tracker

[![PyPI Version](https://img.shields.io/pypi/v/ai-tracker.svg)](https://pypi.org/project/ai-tracker/)
[![Python Versions](https://img.shields.io/pypi/pyversions/ai-tracker.svg)](https://pypi.org/project/ai-tracker/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

一个用于追踪 Claude Code AI 代码贡献的工具，可以记录 AI 修改的代码行，并在 push 时分析哪些内容是 AI 生成的，哪些是人工修改的。

## 功能特性

- **实时记录**: 自动记录 Claude Code 的 Write/Edit/MultiEdit 操作
- **智能分析**: 通过相似度匹配识别 AI 生成的代码行
- **Git 集成**: pre-push hook 自动分析提交内容
- **报告生成**: 终端、JSON、Markdown 格式的报告
- **后端同步**: 支持推送到服务器进行集中存储和分析

## 安装

### 1. 安装依赖

```bash
# 使用 pip 安装
pip install -e .

# 或使用 poetry
poetry install
```

### 2. 安装 Hooks

在项目根目录运行：

```bash
python -m ai_tracker install

# 可选：指定 Python 命令和服务器 URL
python -m ai_tracker install --python python3 --server http://localhost:8000
```

这会自动：
- 安装 Git pre-push hook
- 配置 Claude Code hooks
- 更新 .gitignore

## 使用方法

### 记录 AI 操作

安装 hooks 后，Claude Code 的所有 Write/Edit/MultiEdit 操作都会自动记录到 `.ai-contributions/events.jsonl`。

### 手动分析

```bash
# 分析当前分支的变更
python -m ai_tracker analyze

# 指定基准分支
python -m ai_tracker analyze --base origin/main

# 生成 JSON 报告
python -m ai_tracker analyze --json report.json

# 生成 Markdown 报告
python -m ai_tracker analyze --markdown

# 推送到服务器
python -m ai_tracker analyze --push http://localhost:8000 --project myproject
```

### Pre-Push 分析

Git push 时会自动运行分析并显示报告：

```bash
git push
```

### 查询报告

```bash
# 从服务器查询报告
python -m ai_tracker report --server http://localhost:8000

# 按项目过滤
python -m ai_tracker report --server http://localhost:8000 --project myproject

# 按作者过滤
python -m ai_tracker report --server http://localhost:8000 --author "John Doe"

# 按日期范围过滤
python -m ai_tracker report --server http://localhost:8000 --from 2026-01-01 --to 2026-01-31
```

## 报告指标

### AI 生成率
AI 写的行 / session 总变更行

### AI 存活率
留在 push 中的 AI 行 / AI 写的总数

### AI 净贡献
最终 push 中可归因 AI 行 / 总行数

### 代码分类
- **纯 AI**: AI 生成且未修改的代码
- **AI 原作**: AI 生成但被人工修改的代码
- **混合贡献**: AI 和人工共同贡献的代码
- **人工编写**: 纯人工编写的代码
- **已删除**: AI 生成但最终被删除的代码

## 配置

### 相似度阈值

在 `ai_tracker/config.py` 中可以调整相似度阈值：

```python
THRESHOLD_AI_PURE = 0.95        # > 95% 相似 → 纯 AI
THRESHOLD_AI_MODIFIED = 0.60    # > 60% 相似 → AI 修改版
THRESHOLD_MIXED = 0.30          # > 30% 相似 → 混合贡献
```

### 环境变量

- `AI_TRACKER_SERVER`: 后端服务器 URL
- `AI_TRACKER_PROJECT`: 项目名称
- `CLAUDE_SESSION_ID`: Claude Code 会话 ID

## 后端服务器

追踪器可以与后端服务器配合使用，用于集中存储和分析数据。

### 启动服务器

```bash
cd ../server
python -m server
```

服务器默认运行在 `http://localhost:8000`。

### API 接口

- `POST /api/operation`: 保存操作记录
- `POST /api/analysis`: 保存分析结果
- `GET /api/operations`: 查询操作记录
- `GET /api/report`: 生成统计报告
- `GET /api/summary`: 获取汇总统计
- `GET /api/health`: 健康检查

## 文件结构

```
.ai-contributions/
├── events.jsonl          # AI 操作事件记录（JSONL 格式）
├── report.json           # 最新分析报告
└── snapshots/            # 文件快照目录
    └── {event_id}_{filename}
```

## 测试

```bash
# 运行测试
cd ai_tracker
pytest

# 运行测试并查看覆盖率
pytest --cov=ai_tracker --cov-report=term-missing
```

## 开发

### 项目结构

```
ai_tracker/
├── __main__.py           # CLI 入口
├── models.py             # 数据模型
├── event_store.py        # 事件存储
├── hook_handler.py       # Hook 处理
├── analyzer.py           # 分析引擎
├── reporter.py           # 报告生成
├── similarity.py         # 相似度计算
├── config.py             # 配置
├── installer.py          # 安装器
└── tests/                # 测试
    ├── test_models.py
    ├── test_similarity.py
    ├── test_config.py
    ├── test_event_store.py
    └── conftest.py
```

### 添加新功能

1. 在 `models.py` 中定义数据结构
2. 在 `event_store.py` 中实现存储逻辑
3. 在 `analyzer.py` 中实现分析逻辑
4. 在 `reporter.py` 中实现报告生成
5. 添加相应的测试

## 许可证

MIT License
