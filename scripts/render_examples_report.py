"""Render saved example results as a small, standalone HTML report."""

import argparse
import html
import json
import sys
from collections import Counter
from pathlib import Path
from string import Template

ASSETS = Path(__file__).with_name("report_assets")
QUERY_NAMES = {
    "baseline": "Original query",
    "prepared": "Reworded query",
    "direct": "Original text",
    "translated": "English translation",
    "glossary": "Glossary lookup",
}
CASE_USES = {
    "development": "Tuning query wording",
    "evaluation": "Checking query results",
    "legacy": "Checking query results (older materials cases)",
}


def escape(value) -> str:
    return html.escape(str(value), quote=True)


def readable(value: str) -> str:
    return value.replace("_", " ").capitalize()


def query_name(value: str) -> str:
    return QUERY_NAMES.get(value, readable(value))


def display(value) -> str:
    if type(value) is bool:
        return "Yes" if value else "No"
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def code(value) -> str:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2)
    return f"<pre>{escape(text)}</pre>"


def badge(text: str, kind: str = "neutral") -> str:
    return f'<span class="badge {kind}">{escape(text)}</span>'


def group_rows(rows: list[dict], *keys: str) -> dict:
    groups = {}
    for row in rows:
        groups.setdefault(tuple(row[key] for key in keys), []).append(row)
    return groups


def summary_result(rows: list[dict]) -> str:
    questions = {}
    for row in rows:
        if row["status"] == "ok":
            for name, outcome in row["outcomes"].items():
                questions.setdefault(name, []).append(outcome)
    parts = []
    for name, outcomes in questions.items():
        if outcomes[0]["type"] == "score":
            error = sum(outcome["absolute_error"] for outcome in outcomes) / len(outcomes)
            result = f"Average distance from expected: {error:.3f} (lower is better)"
        else:
            correct = sum(outcome["correct"] for outcome in outcomes)
            result = f"{correct}/{len(outcomes)} correct"
        label = f"{readable(name)}: " if len(questions) > 1 else ""
        parts.append(f"<div>{escape(label + result)}</div>")
    if not parts:
        parts.append("No answers")
    counts = Counter(row["status"] for row in rows)
    missing = []
    if counts["skipped"]:
        missing.append(f"{counts['skipped']} skipped")
    if counts["error"]:
        missing.append(f"{counts['error']} failed")
    if missing:
        parts.append(f'<div class="muted">{escape(" · ".join(missing))}</div>')
    return "".join(parts)


def render_summary(rows: list[dict]) -> str:
    parts = []
    for (suite,), suite_rows in group_rows(rows, "suite").items():
        variants = group_rows(suite_rows, "variant")
        parts.append(f'<tbody data-suite="{escape(suite)}">')
        for index, ((variant,), selected) in enumerate(variants.items()):
            heading = (
                f'<th scope="rowgroup" rowspan="{len(variants)}">{escape(readable(suite))}</th>'
                if index == 0
                else ""
            )
            parts.append(
                f"<tr>{heading}<td>{escape(query_name(variant))}</td>"
                f"<td>{summary_result(selected)}</td></tr>"
            )
        parts.append("</tbody>")
    return "".join(parts)


def query_details(row: dict) -> str:
    parts = ["<details><summary>Query details</summary>"]
    request = row.get("request")
    if request:
        parts.append("<h5>Text sent to the model</h5>" + code(request["state"]))
        for name, question in request["questions"].items():
            parts.append(
                f"<h5>{escape(readable(name))}</h5><p>{escape(question['instructions'])}</p>"
            )
            criteria = question.get("criteria")
            if criteria:
                entries = criteria.items() if isinstance(criteria, dict) else enumerate(criteria)
                parts.append("<dl class=criteria>")
                for label, description in entries:
                    parts.append(f"<dt>{escape(label)}</dt><dd>{escape(description)}</dd>")
                parts.append("</dl>")
            if row["status"] == "ok":
                answer = row["response"]["answers"][name]
                values = (
                    {"Yes": answer["noul"], "No": 1 - answer["noul"]}
                    if answer["type"] == "noul"
                    else answer["probabilities"]
                )
                parts.append("<h5>Answer probabilities</h5>")
                for label, probability in values.items():
                    parts.append(
                        f'<div class="probability"><span>{escape(label)}</span>'
                        f'<meter min="0" max="1" value="{escape(probability)}" '
                        f'aria-label="{escape(label)} probability">{probability:.1%}</meter>'
                        f"<span>{probability:.1%}</span></div>"
                    )
    purpose = CASE_USES.get(row["split"], row["split"])
    parts.append(
        f'<p class="muted">Case purpose: {escape(purpose)}. '
        f"Language: {escape(row['language'])}.</p>"
    )
    if "elapsed_s" in row:
        parts.append(f'<p class="muted">Request time: {row["elapsed_s"]:.3f} seconds.</p>')
    parts.append(
        "<details><summary>Raw request and response</summary>"
        + code({"request": request, "response": row.get("response")})
        + "</details></details>"
    )
    return "".join(parts)


def render_answer(row: dict) -> str:
    parts = [f"<h4>{escape(query_name(row['variant']))}</h4>"]
    if row.get("unsupported_language_input"):
        parts.append(badge("Non-English input: model supports English only", "warning"))
    if row["status"] == "ok":
        for name, outcome in row["outcomes"].items():
            parts.append(f'<div class="outcome"><h5>{escape(readable(name))}</h5>')
            parts.append(f'<p class="prediction">{escape(display(outcome["actual"]))}</p>')
            if outcome["type"] == "score":
                parts.append(badge(f"Distance from expected: {outcome['absolute_error']:.3f}"))
            else:
                parts.append(
                    badge(
                        "Correct" if outcome["correct"] else "Incorrect",
                        "good" if outcome["correct"] else "bad",
                    )
                )
                if outcome["type"] == "noul":
                    probability = row["response"]["answers"][name]["noul"]
                    parts.append(
                        f'<p class="muted">{probability:.1%} probability of yes. '
                        "Yes at 50% or above.</p>"
                    )
            parts.append("</div>")
    else:
        skipped = row["status"] == "skipped"
        parts.append(badge("Skipped" if skipped else "Failed", "warning"))
        parts.append(f"<p>{escape(row['reason' if skipped else 'error'])}</p>")
    if row["preparation"] == "translation":
        parts.append('<p class="muted">Uses a fixed English translation.</p>')
    parts.append(query_details(row))
    return '<section class="variant">' + "".join(parts) + "</section>"


def render_cases(rows: list[dict]) -> str:
    parts = []
    for (suite, case), selected in group_rows(rows, "suite", "case").items():
        source = selected[0]["source"]
        different = any(
            outcome.get("correct") is False or outcome.get("absolute_error", 0) > 1e-9
            for row in selected
            if row["status"] == "ok"
            for outcome in row["outcomes"].values()
        )
        issue = any(row["status"] != "ok" for row in selected)
        expected = "".join(
            f"<div>{escape(readable(name))}: <strong>{escape(display(value))}</strong></div>"
            for name, value in source["expected"].items()
        )
        state = source["state"]
        search = json.dumps(state, ensure_ascii=False) if isinstance(state, dict) else state
        parts.append(
            f'<article class="case" data-suite="{escape(suite)}" '
            f'data-different="{int(different)}" data-issue="{int(issue)}" '
            f'data-search="{escape(case + " " + search)}">'
            f"<header><h3>{escape(readable(suite))} "
            f'<span class="muted">/ {escape(case)}</span></h3></header>'
            f'<div class="input"><h4>Input</h4>{code(state)}'
            f"<h4>Expected answer</h4>{expected}</div>"
            f'<div class="variants">{"".join(render_answer(row) for row in selected)}</div>'
            "</article>"
        )
    return "".join(parts)


def render_report(report: dict) -> str:
    if not isinstance(report, dict) or report.get("schema_version") != 1:
        raise ValueError("expected a schema-version-1 examples report")
    if not isinstance(report.get("cases"), list):
        raise ValueError("report cases must be a list")
    try:
        rows = report["cases"]
        counts = Counter(row["status"] for row in rows)
        if counts.keys() - {"ok", "skipped", "error"}:
            raise ValueError("unknown case status")
        suites = dict.fromkeys(row["suite"] for row in rows)
        return Template((ASSETS / "report.html").read_text(encoding="utf-8")).substitute(
            stylesheet=(ASSETS / "report.css").read_text(encoding="utf-8"),
            script=(ASSETS / "report.js").read_text(encoding="utf-8"),
            input_count=len(group_rows(rows, "suite", "case")),
            answered_count=counts["ok"],
            skipped_count=counts["skipped"],
            error_count=counts["error"],
            errors="".join(
                f'<p class="error-message">{escape(error)}</p>'
                for error in report.get("errors", [])
            ),
            suite_options="".join(
                f'<option value="{escape(suite)}">{escape(readable(suite))}</option>'
                for suite in suites
            ),
            summary=render_summary(rows),
            cases=render_cases(rows),
            run_metadata=code({key: value for key, value in report.items() if key != "cases"}),
        )
    except (KeyError, TypeError, AttributeError, IndexError) as exc:
        raise ValueError(f"malformed examples report: {exc}") from exc


def write_report(report: dict, output: Path) -> None:
    document = render_report(report)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(document, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path, help="Saved examples JSON")
    parser.add_argument("--output", type=Path, help="HTML destination (default: sibling .html)")
    args = parser.parse_args(argv)
    output = args.output or args.report.with_suffix(".html")
    try:
        if output.resolve() == args.report.resolve():
            raise ValueError("HTML output must differ from JSON input")
        write_report(json.loads(args.report.read_text(encoding="utf-8")), output)
    except (ValueError, OSError) as exc:
        print(f"examples-report: {exc}", file=sys.stderr)
        return 1
    print(f"HTML report: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
