"""Render saved example results, from one run or several to compare, as a standalone HTML report."""

import argparse
import html
import json
import sys
from collections import Counter
from pathlib import Path
from string import Template

ASSETS = Path(__file__).with_name("report_assets")


def escape(value) -> str:
    return html.escape(str(value), quote=True)


def readable(value: str) -> str:
    return value.replace("_", " ").capitalize()


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
    failed = sum(row["status"] == "error" for row in rows)
    if failed:
        parts.append(f'<div class="muted">{escape(f"{failed} failed")}</div>')
    return "".join(parts)


def run_label(report: dict, index: int) -> str:
    try:
        metadata = report["server_models"]["data"][0]["metadata"]
    except (KeyError, IndexError, TypeError):
        return f"Run {index + 1}"
    return metadata.get("weights_file", "Von").removesuffix(".gguf")


def render_summary(runs: list[list[dict]]) -> str:
    groups = [group_rows(rows, "suite") for rows in runs]
    return "".join(
        f'<tbody data-suite="{escape(suite)}"><tr>'
        f'<th scope="row">{escape(readable(suite))}</th>'
        + "".join(f"<td>{summary_result(run[(suite,)])}</td>" for run in groups)
        + "</tr></tbody>"
        for (suite,) in groups[0]
    )


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
    if "elapsed_s" in row:
        parts.append(f'<p class="muted">Request time: {row["elapsed_s"]:.3f} seconds.</p>')
    parts.append(
        "<details><summary>Raw request and response</summary>"
        + code({"request": request, "response": row.get("response")})
        + "</details></details>"
    )
    return "".join(parts)


def render_answer(row: dict, label: str) -> str:
    parts = [f"<h4>{escape(label)}</h4>"]
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
        parts.append(badge("Failed", "warning"))
        parts.append(f"<p>{escape(row['error'])}</p>")
    parts.append(query_details(row))
    return '<section class="answer">' + "".join(parts) + "</section>"


def differs(row: dict) -> bool:
    return row["status"] == "ok" and any(
        outcome.get("correct") is False or outcome.get("absolute_error", 0) > 1e-9
        for outcome in row["outcomes"].values()
    )


def render_cases(labels: list[str], runs: list[list[dict]]) -> str:
    parts = []
    for rows in zip(*runs, strict=True):
        suite, case, source = rows[0]["suite"], rows[0]["case"], rows[0]["source"]
        different = any(differs(row) for row in rows)
        issue = any(row["status"] != "ok" for row in rows)
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
            '<div class="answers">'
            + "".join(render_answer(row, label) for row, label in zip(rows, labels, strict=True))
            + "</div></article>"
        )
    return "".join(parts)


def render_report(reports: list[dict]) -> str:
    for report in reports:
        if not isinstance(report, dict) or report.get("schema_version") != 2:
            raise ValueError("expected a schema-version-2 examples report")
        if not isinstance(report.get("cases"), list):
            raise ValueError("report cases must be a list")
    try:
        runs = [report["cases"] for report in reports]
        keys = [[(row["suite"], row["case"]) for row in rows] for rows in runs]
        if any(run_keys != keys[0] for run_keys in keys):
            raise ValueError("reports cover different cases")
        labels = [run_label(report, index) for index, report in enumerate(reports)]
        counts = Counter(row["status"] for rows in runs for row in rows)
        if counts.keys() - {"ok", "error"}:
            raise ValueError("unknown case status")
        suites = dict.fromkeys(row["suite"] for row in runs[0])
        return Template((ASSETS / "report.html").read_text(encoding="utf-8")).substitute(
            stylesheet=(ASSETS / "report.css").read_text(encoding="utf-8"),
            script=(ASSETS / "report.js").read_text(encoding="utf-8"),
            input_count=len(runs[0]),
            answered_count=counts["ok"],
            error_count=counts["error"],
            errors="".join(
                f'<p class="error-message">{escape(f"{label}: {error}")}</p>'
                for label, report in zip(labels, reports, strict=True)
                for error in report.get("errors", [])
            ),
            suite_options="".join(
                f'<option value="{escape(suite)}">{escape(readable(suite))}</option>'
                for suite in suites
            ),
            summary_header="".join(f"<th>{escape(label)}</th>" for label in labels),
            summary=render_summary(runs),
            cases=render_cases(labels, runs),
            run_metadata=code(
                [
                    {key: value for key, value in report.items() if key != "cases"}
                    for report in reports
                ]
            ),
        )
    except (KeyError, TypeError, AttributeError, IndexError) as exc:
        raise ValueError(f"malformed examples report: {exc}") from exc


def write_report(reports: list[dict], output: Path) -> None:
    document = render_report(reports)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(document, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reports", type=Path, nargs="+", help="Saved examples JSON, one per run")
    parser.add_argument("--output", type=Path, help="HTML destination (default: sibling .html)")
    args = parser.parse_args(argv)
    if len(args.reports) > 1 and not args.output:
        parser.error("--output is required when comparing several reports")
    output = args.output or args.reports[0].with_suffix(".html")
    try:
        if any(output.resolve() == report.resolve() for report in args.reports):
            raise ValueError("HTML output must differ from JSON input")
        write_report(
            [json.loads(report.read_text(encoding="utf-8")) for report in args.reports], output
        )
    except (ValueError, OSError) as exc:
        print(f"examples-report: {exc}", file=sys.stderr)
        return 1
    print(f"HTML report: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
