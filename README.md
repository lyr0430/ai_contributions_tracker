# AI Code Contributions

AI 代码贡献追踪系统 — 自动统计项目中 AI 与人工的代码贡献比例。

## 快速安装

```bash
# 1. 下载安装脚本
curl -sL https://raw.githubusercontent.com/lyr0430/ai_contributions_tracker/main/install.sh -o /tmp/install-ai-tracker.sh

# 2. 在你的项目目录下执行
cd your-project
bash /tmp/install-ai-tracker.sh
```

安装完成后，**不需要任何配置**，以下行为会自动触发：

| 场景 | 行为 |
|------|------|
| Claude Code 写代码 | 自动记录 AI 写了哪些行 |
| `git push` | 自动分析并上报到服务器 |

## 工作原理

```
Claude Code 写代码
  → PostToolUse hook 记录 AI 事件到 .ai-contributions/events.jsonl

git push
  → pre-push hook 运行分析
  → 对比 git diff + AI 事件，逐行归因
  → 上报到后端服务器（含作者、项目、行数、字符数）
```

### 归因逻辑

每行代码会被归入以下类别：

| 类别 | 说明 |
|------|------|
| **纯 AI** | AI 生成且未被修改（相似度 > 95%） |
| **AI 修改** | AI 生成后被人工微调（相似度 > 60%） |
| **混合** | AI 与人工共同贡献（相似度 > 30%） |
| **人工** | 完全由人工编写 |

如果文件中超过 50% 的行是 AI 生成的，剩余未匹配的行会用更宽松的阈值重新判定，避免人工小修改导致误判。

### 统计维度

- **行数**：纯AI行 / AI修改行 / 混合行 / 人工行
- **字符数**：每个类别的字符总数
- **AI 原始生成量**：AI 一共写了多少（含后续被修改的），不关心最终状态
- **AI 净贡献率**：最终 push 中可归因于 AI 的比例

## 后端服务

### 启动

```bash
cd server
pip install -r requirements.txt
python -m server
```

服务默认监听 `http://localhost:8000`，数据存储在 `server/data/contributions.db`。

### 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `DATABASE_URL` | 数据库连接地址 | SQLite (server/data/) |
| `AI_TRACKER_SERVER` | 服务端地址（覆盖 .env） | http://localhost:8000 |

### API 接口

```bash
# 健康检查
curl http://localhost:8000/api/health

# 查询统计汇总
curl "http://localhost:8000/api/summary"

# 按作者统计
curl "http://localhost:8000/api/report?group_by=author"

# 按项目统计
curl "http://localhost:8000/api/report?project_name=xxx&group_by=commit"

# 按文件统计
curl "http://localhost:8000/api/report?group_by=file"

# 筛选某人的记录
curl "http://localhost:8000/api/summary?author_name=张三"

# 按日期筛选
curl "http://localhost:8000/api/summary?from_date=2026-01-01&to_date=2026-05-31"
```

## 更新

重新执行安装命令即可更新本地的 tracker 代码：

```bash
curl -sL https://raw.githubusercontent.com/lyr0430/ai_contributions_tracker/main/install.sh -o /tmp/install-ai-tracker.sh
cd your-project
bash /tmp/install-ai-tracker.sh
```

## 项目结构

```
ai-code-contributions/
├── install.sh              # 一键安装脚本
├── tracker/                # AI 代码追踪器
│   ├── ai_tracker/         # 核心模块
│   │   ├── analyzer.py     # 分析引擎（归因逻辑）
│   │   ├── similarity.py   # 相似度计算
│   │   ├── hook_handler.py # Claude Code hook 处理
│   │   ├── installer.py    # 安装器（写入 hooks）
│   │   ├── reporter.py     # 报告生成
│   │   ├── models.py       # 数据模型
│   │   ├── config.py       # 配置（.env 读取）
│   │   └── event_store.py  # 事件存储
│   ├── .env                # 配置文件（服务器地址）
│   └── setup.py
│
└── server/                 # 后端服务（FastAPI）
    ├── server/
    │   ├── api.py          # API 接口
    │   ├── db.py           # 数据库操作
    │   └── models.py       # 数据模型
    ├── data/               # SQLite 数据库（gitignore）
    └── requirements.txt
```

## 许可证

MIT License
