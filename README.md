# AI Code Contributions

AI 代码贡献追踪系统，用于记录和分析 AI 生成的代码贡献。

## 项目结构

```
ai-code-contributions/
├── tracker/              # AI 代码追踪器（Python 包）
│   ├── ai_tracker/       # 核心模块
│   ├── tests/            # 测试
│   ├── README.md         # 使用文档
│   ├── CHANGES.md        # 更新日志
│   ├── pyproject.toml    # Poetry 配置
│   ├── setup.py          # Setup 脚本
│   └── requirements.txt  # 依赖
│
└── server/               # 后端服务（FastAPI）
    ├── server/           # 服务代码
    ├── README.md         # 使用文档
    └── requirements.txt  # 依赖
```

## 快速开始

### 1. 安装追踪器

```bash
cd tracker
pip install -e .
```

### 2. 在项目中安装 hooks

```bash
# 在你的项目目录中
ai-tracker install

# 可选：指定服务器 URL
ai-tracker install --server http://localhost:8000
```

### 3. 启动后端服务

```bash
cd server
python -m server
```

## 功能特性

### 追踪器 (tracker)

- **实时记录**: 自动记录 Claude Code 的 Write/Edit/MultiEdit 操作
- **智能分析**: 通过相似度匹配识别 AI 生成的代码行
- **Git 集成**: pre-push hook 自动分析提交内容
- **报告生成**: 终端、JSON、Markdown 格式的报告

### 后端服务 (server)

- **操作记录**: 存储 Claude Code 的实时操作记录
- **提交分析**: 存储 pre-push 分析结果
- **统计报告**: 按项目、作者、日期生成统计报告
- **快照存储**: 保存文件快照用于后续分析

## 使用示例

### 记录 AI 操作

安装 hooks 后，Claude Code 的所有操作都会自动记录。

### 手动分析

```bash
# 分析当前分支的变更
ai-tracker analyze

# 生成 JSON 报告
ai-tracker analyze --json report.json

# 推送到服务器
ai-tracker analyze --push http://localhost:8000 --project myproject
```

### 查询报告

```bash
# 从服务器查询报告
ai-tracker report --server http://localhost:8000

# 按项目过滤
ai-tracker report --server http://localhost:8000 --project myproject
```

## 文档

- [追踪器文档](tracker/README.md)
- [后端服务文档](server/README.md)

## 开发

### 运行测试

```bash
cd tracker
pytest
```

### 启动开发服务器

```bash
cd server
uvicorn server.api:app --reload --host 0.0.0.0 --port 8000
```

## 许可证

MIT License
