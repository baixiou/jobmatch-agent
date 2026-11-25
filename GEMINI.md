# JobMatch Agent 项目指南

## 项目定位
- 简历核心项目：**JobMatch Agent（AI 岗位匹配与简历优化助手）**，用于路线 A（AI 应用 / Agent 寒假实习，6 周冲刺）。
- 技术主线：`Structured Output + 技能归一 + RAG 经历检索 + Agent 工具调用 + Eval 评测 + FastAPI/前端 Demo`。

## 本地运行环境
- Python 虚拟环境：`.\.venv\Scripts\python.exe`（已安装 `openai`、`python-dotenv`、`pydantic`、`httpx2`）。
- 模型接口：DeepSeek（OpenAI 兼容 SDK），密钥配置在根目录 `.env`（绝不提交到 Git）。
- **网络坑提醒**：DeepSeek 为国内直连接口，客户端默认设置 `httpx2.Client(trust_env=False)` 忽略系统代理，避免代理引发 `SSL: UNEXPECTED_EOF_WHILE_READING`。

## 当前进度
- **Day 1（已完成）**：`src/parse_jd.py` 跑通单份 JD 的 JSON Mode + Pydantic 校验。
- **Day 2（进行中/已完成）**：`data/jd_01_*.txt` ~ `jd_05_*.txt` 收集了 5 份来自 Boss 直聘的真实 AI 实习 JD；`src/batch_analyze.py` 实现并发批量解析与技能高频榜报告；Git 仓库初始化。
- **下一步（Day 3）**：录入个人简历/项目经历库，开始搭建「简历 × JD 匹配度打分 + 缺口分析 + 针对性改写建议」。
