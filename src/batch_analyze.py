import json
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

from parse_jd import JobRequirement, create_client, parse_jd

# 常见同义写法兜底归一，降低跨 JD 统计的碎片化
SKILL_ALIAS_MAP = {
    "python": "Python",
    "typescript": "TypeScript",
    "javascript": "JavaScript",
    "js": "JavaScript",
    "ts": "TypeScript",
    "go": "Go",
    "golang": "Go",
    "c++": "C++",
    "java": "Java",
    "ai agent": "AI Agent",
    "agent": "AI Agent",
    "智能体": "AI Agent",
    "rag": "RAG",
    "rag知识库": "RAG",
    "知识库": "RAG",
    "prompt": "Prompt Engineering",
    "prompt engineering": "Prompt Engineering",
    "pe工程": "Prompt Engineering",
    "llm api": "LLM API",
    "openai api": "LLM API",
    "api调用": "LLM API",
    "function calling": "Function Calling",
    "langchain": "LangChain",
    "fastapi": "FastAPI",
    "git": "Git/开源项目",
    "github": "Git/开源项目",
    "开源项目": "Git/开源项目",
    "git/开源项目": "Git/开源项目",
    "向量数据库": "向量数据库",
    "工作流编排": "工作流编排",
    "工作流": "工作流编排",
    "自动化脚本": "自动化脚本",
}


def canonicalize_skill(skill: str) -> str:
    cleaned = skill.strip()
    if not cleaned:
        return ""
    return SKILL_ALIAS_MAP.get(cleaned.lower(), cleaned)


def analyze_single_file(jd_path: Path) -> Tuple[str, JobRequirement, float]:
    client, model = create_client()
    t0 = time.perf_counter()
    jd_text = jd_path.read_text(encoding="utf-8")
    req = parse_jd(jd_text, client=client, model=model)
    elapsed = round(time.perf_counter() - t0, 2)
    return jd_path.name, req, elapsed


def build_markdown_report(
    records: List[Dict],
    skill_counter: Counter,
    total_elapsed: float,
) -> str:
    n = len(records)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    lines = [
        "# JobMatch Agent · 真实岗位高频技能分析报告",
        "",
        f"> 生成时间：{now_str} ｜ 样本量：**{n} 份真实 JD** ｜ 并发解析总耗时：**{total_elapsed:.2f}s**",
        "",
        "## 1. 岗位样本总览",
        "",
        "| 文件 | 公司 | 岗位 | 地点 | 薪资 | 学历/届次 | 耗时 |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :-: |",
    ]

    for rec in records:
        d = rec["parsed"]
        lines.append(
            f"| `{rec['file']}` | {d.get('company') or '-'} | {d.get('job_title') or '-'} | "
            f"{d.get('location') or '-'} | {d.get('salary') or '-'} | "
            f"{d.get('education') or '-'} | {rec['elapsed_s']}s |"
        )

    lines.extend([
        "",
        "## 2. 高频核心技能 Top 榜",
        "",
        "| 排名 | 技能标签 | 出现岗位数 | 覆盖率 | 热度条 |",
        "| :-: | :--- | :-: | :-: | :--- |",
    ])

    for rank, (skill, count) in enumerate(skill_counter.most_common(20), start=1):
        ratio = count / n if n else 0
        bar = "█" * int(round(ratio * 10)) + "░" * (10 - int(round(ratio * 10)))
        lines.append(f"| {rank} | **{skill}** | {count}/{n} | {ratio * 100:.0f}% | `{bar}` |")

    lines.extend(["", "## 3. 各岗位核心要求与加分项摘录", ""])
    for rec in records:
        d = rec["parsed"]
        lines.append(f"### {d.get('company') or '未知公司'} — {d.get('job_title')}")
        lines.append(f"- **标准技能标签**：{', '.join(rec['canonical_skills']) or '无'}")
        if d.get("must_have_skills"):
            lines.append("- **核心要求**：" + "；".join(d["must_have_skills"][:5]))
        if d.get("nice_to_have"):
            lines.append("- **加分项**：" + "；".join(d["nice_to_have"][:5]))
        lines.append("")

    return "\n".join(lines)


def main() -> None:
    project_root = Path(__file__).resolve().parent.parent
    data_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else project_root / "data"
    output_dir = project_root / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    jd_files = sorted(data_dir.glob("jd_*.txt"))
    if not jd_files:
        jd_files = sorted(data_dir.glob("*.txt"))

    if not jd_files:
        print(f"目录 {data_dir} 下没有找到任何 .txt JD 文件。")
        sys.exit(1)

    print(f"发现 {len(jd_files)} 份 JD，开始并发解析（max_workers=3）...\n")
    t_start = time.perf_counter()

    results_by_name: Dict[str, Tuple[JobRequirement, float]] = {}
    errors: List[Tuple[str, str]] = []

    with ThreadPoolExecutor(max_workers=3) as pool:
        future_map = {pool.submit(analyze_single_file, p): p.name for p in jd_files}
        for future in as_completed(future_map):
            fname = future_map[future]
            try:
                name, req, elapsed = future.result()
                results_by_name[name] = (req, elapsed)
                print(f"  [OK] {name} -> {req.company or '未知'} / {req.job_title} ({elapsed}s)")
            except Exception as exc:
                errors.append((fname, str(exc)))
                print(f"  [ERR] {fname}: {exc}")

    total_elapsed = round(time.perf_counter() - t_start, 2)

    records: List[Dict] = []
    skill_counter: Counter = Counter()

    for p in jd_files:
        if p.name not in results_by_name:
            continue
        req, elapsed = results_by_name[p.name]
        # 单份 JD 内去重，统计的是“有多少个岗位要求这项技能”
        canonical_skills = list(
            dict.fromkeys(
                s for s in (canonicalize_skill(x) for x in req.normalized_skills) if s
            )
        )
        skill_counter.update(canonical_skills)
        records.append(
            {
                "file": p.name,
                "elapsed_s": elapsed,
                "canonical_skills": canonical_skills,
                "parsed": req.model_dump(),
            }
        )

    json_path = output_dir / "parsed_jds.json"
    report_path = output_dir / "skill_report.md"

    json_path.write_text(
        json.dumps(
            {
                "generated_at": datetime.now().isoformat(timespec="seconds"),
                "total_files": len(jd_files),
                "success_count": len(records),
                "error_count": len(errors),
                "total_elapsed_s": total_elapsed,
                "skill_ranking": [
                    {"skill": s, "job_count": c, "coverage": round(c / len(records), 3)}
                    for s, c in skill_counter.most_common()
                ]
                if records
                else [],
                "records": records,
                "errors": errors,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    report_md = build_markdown_report(records, skill_counter, total_elapsed)
    report_path.write_text(report_md, encoding="utf-8")

    print(f"\n=== 批量解析完成（成功 {len(records)}/{len(jd_files)}，总耗时 {total_elapsed}s）===")
    print("\nTop 10 高频技能榜：")
    for rank, (skill, cnt) in enumerate(skill_counter.most_common(10), start=1):
        pct = cnt / len(records) * 100 if records else 0
        print(f"  {rank:2d}. {skill:<26s} {cnt}/{len(records)} ({pct:.0f}%)")

    print(f"\n已保存 JSON：{json_path}")
    print(f"已保存报告：{report_path}")


if __name__ == "__main__":
    main()
