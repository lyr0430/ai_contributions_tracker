# AI Code Contributions 项目结构

## 目录结构

```
ai-code-contributions/
├── README.md                 # 项目总文档
├── PROJECT_STRUCTURE.md      # 项目结构说明
├── install.sh                # 安装脚本
├── .gitignore               # Git 忽略文件
│
├── tracker/                  # AI 代码追踪器（Python 包）
│   ├── ai_tracker/          # 核心模块
│   │   ├── __init__.py
│   │   ├── __main__.py      # CLI 入口
│   │   ├── models.py        # 数据模型
│   │   ├── event_store.py   # 事件存储
│   │   ├── hook_handler.py  # Hook 处理
│   │   ├── analyzer.py      # 分析引擎
│   │   ├── reporter.py      # 报告生成
│   │   ├── similarity.py    # 相似度计算
│   │   ├── config.py        # 配置
│   │   └── installer.py     # 安装器
│   ├── ai_tracker/tests/    # 测试
│   │   ├── test_models.py
│   │   ├── test_similarity.py
│   │   ├── test_config.py
│   │   ├── test_event_store.py
│   │   └── conftest.py
│   ├── README.md            # 使用文档
│   ├── CHANGES.md           # 更新日志
│   ├── pyproject.toml       # Poetry 配置
│   ├── setup.py             # Setup 脚本
│   └── requirements.txt     # 依赖
│
└── server/                   # 后端服务（FastAPI）
    ├── server/              # 服务代码
    │   ├── __init__.py
    │   ├── __main__.py      # 启动脚本
    │   ├── api.py           # FastAPI 接口
    │   ├── db.py            # 数据库操作
    │   ├── models.py        # 数据模型
    │   └── snapshots/       # 快照存储
    ├── README.md            # 使用文档
    └── requirements.txt     # 依赖
```

## 安装和使用

### 快速安装

```bash
# 运行安装脚本
./install.sh
```

### 手动安装

#### 1. 安装追踪器

```bash
cd tracker
pip install -e .
cd ..
```

#### 2. 在项目中安装 hooks

```bash
# 在你的项目目录中
ai-tracker install

# 可选：指定服务器 URL
ai-tracker install --server http://localhost:8000
```

#### 3. 启动后端服务

```bash
cd server
python -m server
```

## 核心功能

### 追踪器 (tracker)

| 功能 | 说明 |
|------|------|
| 实时记录 | 自动记录 Claude Code 的 Write/Edit/MultiEdit 操作 |
| 智能分析 | 通过相似度匹配识别 AI 生成的代码行 |
| Git 集成 | pre-push hook 自动分析提交内容 |
| 报告生成 | 终端、JSON、Markdown 格式的报告 |

### 后端服务 (server)

| 功能 | 说明 |
|------|------|
| 操作记录 | 存储 Claude Code 的实时操作记录 |
| 提交分析 | 存储 pre-push 分析结果 |
| 统计报告 | 按项目、作者、日期生成统计报告 |
| 快照存储 | 保存文件快照用于后续分析 |

## API 接口

### 追踪器命令

```bash
# 安装 hooks
ai-tracker install

# 手动分析
ai-tracker analyze

# 查询报告
ai-tracker report --server http://localhost:8000
```

### 后端服务 API

- `POST /api/operation`: 保存操作记录
- `POST /api/analysis`: 保存分析结果
- `GET /api/operations`: 查询操作记录
- `GET /api/report`: 生成统计报告
- `GET /api/summary`: 获取汇总统计
- `GET /api/health`: 健康检查

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
