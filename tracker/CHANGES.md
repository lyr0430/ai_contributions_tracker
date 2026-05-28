# AI Tracker 更新日志

## 2026-05-27 - 问题修复版本

### 已修复的问题

#### 1. 路径硬编码问题 (CRITICAL)
**位置**: `server/db.py`
- **问题**: 硬编码了 `/Users/zhenqi/demo/ai-contributions` 路径
- **修复**: 改为使用 `Path.cwd() / ".ai-contributions"` 相对路径
- **影响**: 现在可以在任何机器上运行，无需修改代码

#### 2. 快照路径不一致问题
**位置**: `event_store.py`
- **问题**: events.jsonl 中的 snapshot_path 指向错误的路径
- **修复**: 确保所有快照都保存到 `.ai-contributions/snapshots/` 目录
- **影响**: 快照文件现在可以正确找到

#### 3. Git Hook 安装问题 (Windows)
**位置**: `installer.py`
- **问题**: Windows 版本的 hook 脚本缺少 `--project` 参数
- **修复**: 添加 `project_name` 参数到 Windows hook 脚本
- **影响**: Windows 用户现在可以正确记录项目名称

#### 4. 错误处理不完善
**位置**: `hook_handler.py`
- **问题**: 使用过于宽泛的 `except:` 捕获所有异常
- **修复**: 改为捕获具体的异常类型并记录错误信息
- **影响**: 错误信息更清晰，便于调试

#### 5. to_dict() 方法问题
**位置**: `models.py`
- **问题**: `to_dict()` 方法返回的字典键是整数而非字符串
- **修复**: 在 `to_dict()` 中将行号键转换为字符串
- **影响**: JSON 序列化更一致

### 新增功能

#### 1. 测试套件
- 添加了 41 个单元测试
- 覆盖模型、配置、事件存储、相似度计算等模块
- 测试覆盖率: 43% (核心模块 81-99%)

#### 2. 文档
- 添加了 `ai_tracker/README.md` 使用文档
- 添加了 `ai-contributions-server/README.md` 后端文档
- 添加了 `requirements.txt` 依赖文件

### 文件变更

#### ai_tracker/
- `models.py`: 修复 `to_dict()` 方法
- `event_store.py`: 修复快照路径逻辑
- `installer.py`: 修复 Windows hook 脚本
- `hook_handler.py`: 改进错误处理
- `tests/`: 新增测试目录和测试文件
- `README.md`: 新增使用文档
- `CHANGES.md`: 新增更新日志

#### ai-contributions-server/
- `server/db.py`: 修复路径硬编码问题
- `README.md`: 新增使用文档
- `requirements.txt`: 新增依赖文件

### 测试结果

```
41 passed in 0.26s

Name                        Stmts   Miss  Cover
---------------------------------------------------------
__init__.py                     1      0   100%
config.py                      28      0   100%
event_store.py                 70     13    81%
models.py                      94      1    99%
similarity.py                  85     19    78%
tests/__init__.py               0      0   100%
tests/conftest.py               4      0   100%
tests/test_config.py           56      0   100%
tests/test_event_store.py      98      0   100%
tests/test_models.py           81      0   100%
tests/test_similarity.py       49      0   100%
---------------------------------------------------------
TOTAL                        1253    720    43%
```

### 下一步计划

1. 提高测试覆盖率到 80% 以上
2. 添加集成测试
3. 优化性能（事件分片存储）
4. 添加更多文档示例
