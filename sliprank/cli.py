"""Read a JSON case, evaluate it, and write the report files."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from sliprank.report import render_csv, render_report, render_summary, render_svg
from sliprank.schmid import SlipRankError, AnalysisResult, evaluate, requests_from_mapping
from sliprank.wizard import WizardError, build_document


def _read_document(path: Path) -> object:
    if not path.is_file():
        raise SlipRankError(f"找不到输入文件：{path}")
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise SlipRankError(f"输入不是合法 JSON：{exc.msg}（第 {exc.lineno} 行）。") from exc


def _write_outputs(results: list[AnalysisResult], out_dir: Path, input_name: str) -> str:
    report = render_report(results)
    out_dir.mkdir(parents=True, exist_ok=True)
    files = {
        "report.md": report,
        "systems.csv": render_csv(results),
        "summary.json": render_summary(results, input_name),
        "ranking.svg": render_svg(results),
    }
    for name, text in files.items():
        (out_dir / name).write_bytes(text.encode("utf-8"))
    saved = out_dir.resolve()
    return report + f"\n保存目录：{saved}\n" + "\n".join(f"已写 {name}" for name in files) + "\n"


def run_case(input_path: Path, out_dir: Path) -> str:
    document = _read_document(input_path)
    requests = requests_from_mapping(document)
    results = [evaluate(request) for request in requests]
    return _write_outputs(results, out_dir, input_path.name)


def _ask(prompt: str) -> str:
    print(prompt, flush=True)
    try:
        return input().strip()
    except EOFError as exc:
        raise SlipRankError("交互输入已结束，没有读到完整答案。") from exc


def run_interactive(out_dir: Path) -> str:
    """Ask one direction. CRSS stays in the JSON file; Enter here omits it."""
    print("SlipRank：一个取向，单轴拉伸或压缩。这里不填写 CRSS。", flush=True)
    structure = _ask("结构：hcp（α-Ti）或 bcc（β-Ti）")
    loading = _ask("加载：拉伸 或 压缩")
    direction = _ask("方向：HCP 例如 0001、2-1-10、[2-1-10]、10-11；BCC 例如 001")
    stress_text = _ask("施加应力 σ/MPa：直接回车则不计算 τ")
    crss_text = _ask("CRSS：直接回车跳过。不要在这里填一个数")
    if crss_text:
        raise SlipRankError(
            "这里不能填写 CRSS。分家族的数值请写进 JSON 的 crss_MPa；直接回车表示不提供 CRSS。"
        )
    stress = None
    if stress_text:
        try:
            stress = float(stress_text)
        except ValueError as exc:
            raise SlipRankError(f"施加应力必须是大于 0 的数，单位 MPa；实际得到 {stress_text!r}。") from exc
    document = build_document(
        structure=structure,
        loading=loading,
        direction=direction,
        stress_MPa=stress,
        label="user",
    )
    requests = requests_from_mapping(document)
    results = [evaluate(request) for request in requests]
    return _write_outputs(results, out_dir, "interactive")


def _utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors=stream.errors)


def main(argv: list[str] | None = None) -> int:
    _utf8_stdio()
    parser = argparse.ArgumentParser(
        prog="sliprank",
        description="Rank HCP or BCC slip and twin systems by uniaxial Schmid factor.",
    )
    parser.add_argument("input", nargs="?", help="JSON case. See examples/c_axis_tension.json.")
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Ask for one direction. Enter skips CRSS. JSON input remains the repeatable path.",
    )
    parser.add_argument("--out", required=True, help="Directory for report.md, systems.csv, summary.json, and ranking.svg.")
    args = parser.parse_args(argv)
    try:
        if args.interactive:
            text = run_interactive(Path(args.out))
        else:
            if not args.input:
                parser.error("需要 JSON 输入，或改用 --interactive。")
            text = run_case(Path(args.input), Path(args.out))
    except (SlipRankError, WizardError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(text, end="")
    return 0
