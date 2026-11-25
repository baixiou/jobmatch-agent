# JobMatch Agent · 智能岗位匹配与简历优化助手

一个面向真实求职场景的 AI 应用工程项目，完整覆盖：**结构化输出（Structured Output）→ 批量解析与技能归一 → RAG 经历检索 → Agent 工具调用 → 评测对比（Eval）→ Web Demo 部署**。

## 项目结构

```text
jobmatch-agent/
├── data/                   # 真实招聘 JD 样本（jd_*.txt）与测试样例
├── src/
│   ├── parse_jd.py         # 单份 JD 结构化解析（DeepSeek + JSON Mode + Pydantic 校验）
│   └── batch_analyze.py    # 多份 JD 并发批量解析 + 技能归一化 + 高频技能榜报告生成
├── output/                 # 运行产物（parsed_jds.json / skill_report.md，已忽略）
├── .env.example            # 环境变量模板
├── requirements.txt        # Python 依赖
└── README.md
```

## 快速开始

1. 复制 `.env.example` 为 `.env`，填入你的 `DEEPSEEK_API_KEY`（`.env` 已加入 `.gitignore`，不会被提交到 Git）。
2. 创建虚拟环境并安装依赖：
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\pip install -r requirements.txt
   ```
3. **单份 JD 结构化解析（Day 1）**：
   ```powershell
   .\.venv\Scripts\python src\parse_jd.py data\jd_01_wanshi_ai.txt
   ```
4. **多份真实 JD 批量解析 & 高频技能榜（Day 2）**：
   ```powershell
   .\.venv\Scripts\python src\batch_analyze.py
   ```
   运行后会在 `output/` 目录生成：
   - `output/parsed_jds.json`：全部岗位的结构化 JSON 与技能覆盖率数据
   - `output/skill_report.md`：可读性良好的岗位对比与高频技能 Top 榜报告

## 开发路线图

- [x] **Day 1**：项目骨架 + DeepSeek API 接入 + JD 结构化解析（JSON Mode + Pydantic 校验 + 国内直连代理兼容）
- [x] **Day 2**：采集 5 份真实 AI 实习 JD + 并发批量解析 + 技能归一化与高频技能榜 + Git 首次提交
- [ ] **Week 2~3**：接入个人经历 RAG 检索 + 匹配度打分与简历改写 Agent + FastAPI/前端界面
- [ ] **Week 4**：构建 20~30 条评测集（Eval），记录优化前后准确率与耗时对比
