# AI Contributions Server

AI 代码贡献追踪系统的后端服务器，用于存储和分析 AI 代码贡献数据。

## 功能特性

- **操作记录**: 存储 Claude Code 的实时操作记录
- **提交分析**: 存储 pre-push 分析结果
- **统计报告**: 按项目、作者、日期生成统计报告
- **快照存储**: 保存文件快照用于后续分析

## 安装

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置数据库

默认使用 SQLite 数据库，存储在 `.ai-contributions/contributions.db`。

如需使用 MySQL，设置环境变量：

```bash
export DATABASE_URL="mysql+pymysql://user:pass@host:port/dbname"
```

## 启动服务器

```bash
python -m server
```

服务器默认运行在 `http://localhost:8000`。

## API 接口

### 保存操作记录

```bash
curl -X POST http://localhost:8000/api/operation \
  -H "Content-Type: application/json" \
  -d '{
    "project_name": "myproject",
    "project_path": "/path/to/project",
    "session_id": "session-123",
    "operation_id": "op-456",
    "timestamp": "2026-01-01T00:00:00",
    "operation": "write",
    "file_path": "src/main.py",
    "diff_added": ["print(\"hello\")"],
    "diff_removed": [],
    "snapshot_content": "print(\"hello\")\n",
    "file_hash": "abc123..."
  }'
```

### 保存分析结果

```bash
curl -X POST http://localhost:8000/api/analysis \
  -H "Content-Type: application/json" \
  -d '{
    "project_name": "myproject",
    "project_path": "/path/to/project",
    "commit_hash": "abc123...",
    "branch_name": "main",
    "author_name": "John Doe",
    "author_email": "john@example.com",
    "commit_time": "2026-01-01T00:00:00",
    "total_push_lines": 100,
    "ai_events_count": 10,
    "generation_rate": 0.8,
    "retention_rate": 0.9,
    "net_contribution": 0.75,
    "ai_pure_lines": 50,
    "ai_modified_lines": 20,
    "mixed_lines": 10,
    "human_lines": 20,
    "deleted_ai_lines": 5,
    "files": [
      {
        "path": "src/main.py",
        "source": "ai",
        "ai_pure_lines": 30,
        "ai_modified_lines": 10,
        "mixed_lines": 5,
        "human_lines": 5
      }
    ]
  }'
```

### 查询操作记录

```bash
# 查询所有记录
curl http://localhost:8000/api/operations

# 按项目过滤
curl "http://localhost:8000/api/operations?project_name=myproject"

# 按作者过滤
curl "http://localhost:8000/api/operations?author_name=John%20Doe"

# 按日期过滤
curl "http://localhost:8000/api/operations?from_date=2026-01-01&to_date=2026-01-31"
```

### 生成统计报告

```bash
# 按提交分组
curl "http://localhost:8000/api/report?group_by=commit"

# 按文件分组
curl "http://localhost:8000/api/report?group_by=file"

# 按作者分组
curl "http://localhost:8000/api/report?group_by=author"

# 按项目过滤
curl "http://localhost:8000/api/report?project_name=myproject&group_by=commit"
```

### 获取汇总统计

```bash
curl http://localhost:8000/api/summary

# 按项目过滤
curl "http://localhost:8000/api/summary?project_name=myproject"
```

### 健康检查

```bash
curl http://localhost:8000/api/health
```

## 数据库模型

### OperationRecord

存储操作记录和分析结果：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | int | 主键 |
| project_name | str | 项目名称 |
| project_path | str | 项目路径 |
| commit_hash | str | 提交哈希 |
| branch_name | str | 分支名称 |
| author_name | str | 作者姓名 |
| author_email | str | 作者邮箱 |
| commit_time | datetime | 提交时间 |
| file_path | str | 文件路径 |
| source | str | 来源 (ai/human) |
| ai_pure_lines | int | 纯 AI 行数 |
| ai_modified_lines | int | AI 修改行数 |
| mixed_lines | int | 混合贡献行数 |
| human_lines | int | 人工编写行数 |
| total_lines | int | 总行数 |
| created_at | datetime | 创建时间 |

### CommitSummary

提交汇总（用于快速查询）：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | int | 主键 |
| project_name | str | 项目名称 |
| project_path | str | 项目路径 |
| commit_hash | str | 提交哈希（唯一） |
| branch_name | str | 分支名称 |
| author_name | str | 作者姓名 |
| author_email | str | 作者邮箱 |
| commit_time | datetime | 提交时间 |
| total_operations | int | 总操作数 |
| total_files_changed | int | 变更文件数 |
| total_lines_added | int | 新增行数 |
| total_lines_removed | int | 删除行数 |
| ai_pure_lines | int | 纯 AI 行数 |
| ai_modified_lines | int | AI 修改行数 |
| mixed_lines | int | 混合贡献行数 |
| human_lines | int | 人工编写行数 |
| created_at | datetime | 创建时间 |

## 文件结构

```
server/
├── __init__.py
├── __main__.py           # 启动脚本
├── api.py                # FastAPI 接口
├── db.py                 # 数据库操作
├── models.py             # 数据模型
└── snapshots/            # 快照存储目录
```

## 开发

### 运行开发服务器

```bash
uvicorn server.api:app --reload --host 0.0.0.0 --port 8000
```

### 测试

```bash
# 运行测试（需要安装 pytest）
pytest
```

## 部署

### 使用 Docker

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY server/ ./server/
EXPOSE 8000

CMD ["python", "-m", "server"]
```

### 使用 systemd

创建 `/etc/systemd/system/ai-contributions.service`：

```ini
[Unit]
Description=AI Contributions Server
After=network.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/path/to/ai-contributions-server
ExecStart=/usr/bin/python -m server
Restart=always

[Install]
WantedBy=multi-user.target
```

## 许可证

MIT License
