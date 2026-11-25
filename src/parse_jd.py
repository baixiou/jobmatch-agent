import json
import os
import sys
import time
from pathlib import Path
from typing import List, Optional, Tuple

from dotenv import load_dotenv
import httpx2
from openai import OpenAI
from pydantic import BaseModel, Field


class JobRequirement(BaseModel):
    """结构化的招聘岗位描述（JD）数据模型"""

    job_title: str = Field(description="岗位名称")
    company: Optional[str] = Field(default=None, description="公司名称，未提及则填 null")
    salary: Optional[str] = Field(default=None, description="薪资范围，未提及则填 null")
    location: Optional[str] = Field(default=None, description="工作地点，未提及则填 null")
    attendance: Optional[str] = Field(default=None, description="每周出勤与实习时长要求")
    education: Optional[str] = Field(default=None, description="学历与届别要求")
    responsibilities: List[str] = Field(default_factory=list, description="核心岗位职责列表")
    must_have_skills: List[str] = Field(default_factory=list, description="必须掌握的硬技能或要求")
    nice_to_have: List[str] = Field(default_factory=list, description="加分项列表")
    normalized_skills: List[str] = Field(
        default_factory=list,
        description="归一化后的标准技术/工具技能标签（如 Python、AI Agent、RAG、Prompt Engineering、FastAPI、Git、向量数据库、TypeScript 等），用于跨岗位统计",
    )
    keywords: List[str] = Field(default_factory=list, description="3~8 个核心技术/业务关键词")


SYSTEM_PROMPT = """你是一位资深的互联网技术招聘分析助手。
请阅读用户提供的岗位描述（JD），严格提取关键信息，并以标准 JSON 对象输出。

JSON 字段必须严格遵循以下结构（不要遗漏字段，也不要输出多余解释）：
{
  "job_title": "字符串",
  "company": "字符串或 null",
  "salary": "字符串或 null",
  "location": "字符串或 null",
  "attendance": "字符串或 null",
  "education": "字符串或 null",
  "responsibilities": ["字符串"],
  "must_have_skills": ["字符串"],
  "nice_to_have": ["字符串"],
  "normalized_skills": ["标准技能名"],
  "keywords": ["字符串"]
}

关于 normalized_skills（技能归一化规则，非常重要）：
- 只提取具体的技术栈、框架、工具或工程能力，去重并统一命名风格，便于多份 JD 横向统计。
- 常用标准写法示例：Python、TypeScript、JavaScript、Go、C++、Java、AI Agent、RAG、Prompt Engineering、LLM API、Function Calling、工作流编排、FastAPI、React/Vue、向量数据库、SQL/数据库、Linux/Docker、Git/开源项目、AI编程工具（Cursor/Claude Code/Codex）、模型评测（Eval）、自动化脚本。
"""


def create_client() -> Tuple[OpenAI, str]:
    """加载环境变量并返回配置好的 OpenAI 兼容客户端与模型名。"""
    load_dotenv()

    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "未检测到 DEEPSEEK_API_KEY。请先打开项目根目录的 .env 文件，填入你的 DeepSeek API Key。"
        )

    base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").strip()
    model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat").strip()
    use_proxy = os.getenv("USE_SYSTEM_PROXY", "false").strip().lower() == "true"

    # DeepSeek 为国内直连接口，默认忽略系统代理，避免代理导致的 SSL EOF 握手中断
    http_client = httpx2.Client(trust_env=use_proxy, timeout=60.0)
    client = OpenAI(api_key=api_key, base_url=base_url, http_client=http_client)
    return client, model


def parse_jd(
    jd_text: str,
    client: Optional[OpenAI] = None,
    model: Optional[str] = None,
    max_retries: int = 2,
) -> JobRequirement:
    """调用大模型解析单份 JD 文本，并经 Pydantic 校验后返回结构化对象。"""
    if client is None or model is None:
        client, model = create_client()

    last_error: Optional[Exception] = None
    for attempt in range(max_retries + 1):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"请解析以下招聘 JD：\n\n{jd_text}"},
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
            )
            raw_content = response.choices[0].message.content or "{}"
            data = json.loads(raw_content)
            return JobRequirement.model_validate(data)
        except Exception as exc:
            last_error = exc
            if attempt < max_retries:
                time.sleep(1.5 * (attempt + 1))

    raise RuntimeError(f"JD 解析失败（已重试 {max_retries} 次）：{last_error}") from last_error


def main() -> None:
    project_root = Path(__file__).resolve().parent.parent
    jd_path = Path(sys.argv[1]) if len(sys.argv) > 1 else project_root / "data" / "sample_jd.txt"

    if not jd_path.exists():
        print(f"找不到 JD 文件：{jd_path}")
        sys.exit(1)

    jd_text = jd_path.read_text(encoding="utf-8")
    print(f"正在解析：{jd_path.name} ...\n")

    result = parse_jd(jd_text)
    print(json.dumps(result.model_dump(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
