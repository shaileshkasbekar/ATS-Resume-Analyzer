"""
Measures the Job Match engine against the hand-labelled cases.

Run:  venv\\Scripts\\python.exe -m evaluation.evaluate

Rule-based only (no AI), so the numbers are repeatable. Reports:

- requirement extraction: precision / recall of mandatory and preferred
- matching: how often matched / missing is decided correctly
- evidence: how often the evidence level (experience / project / listed) is right
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evaluation.cases import CASES                                    # noqa: E402
from resume_parser.jd_analyzer import analyze_job_match               # noqa: E402


def _key(any_of):

    return "|".join(sorted(s.lower() for s in any_of))


def _label_key(label):

    return "|".join(sorted(label.split("|")))


def _prf(found, expected):

    found, expected = set(found), set(expected)

    true_positive = len(found & expected)

    precision = true_positive / len(found) if found else 1.0
    recall = true_positive / len(expected) if expected else 1.0

    return true_positive, precision, recall


def evaluate(cases=CASES):

    totals = {"req_found": 0, "req_expected": 0, "req_tp": 0,
              "match_total": 0, "match_correct": 0,
              "evidence_total": 0, "evidence_correct": 0}

    rows = []
    mistakes = []

    for case in cases:

        result = analyze_job_match(case["resume"], case["job"], use_ai=False)

        mandatory = [_key(m["any_of"]) for m in result["mandatory"]]
        preferred = [_key(m["any_of"]) for m in result["preferred"]]

        expected_mandatory = [_label_key(x) for x in case["mandatory"]]
        expected_preferred = [_label_key(x) for x in case["preferred"]]

        found = [("M", k) for k in mandatory] + [("P", k) for k in preferred]
        expected = [("M", k) for k in expected_mandatory] + [("P", k) for k in expected_preferred]

        tp, precision, recall = _prf(found, expected)

        totals["req_found"] += len(set(found))
        totals["req_expected"] += len(set(expected))
        totals["req_tp"] += tp

        for kind, key in set(expected) - set(found):
            mistakes.append(f"[{case['name']}] requirement not extracted as {'mandatory' if kind == 'M' else 'preferred'}: {key}")

        for kind, key in set(found) - set(expected):
            mistakes.append(f"[{case['name']}] extra / wrongly classified requirement ({'mandatory' if kind == 'M' else 'preferred'}): {key}")

        # Matching and evidence, for requirements that were extracted

        by_key = {_key(m["any_of"]): m for m in result["mandatory"] + result["preferred"]}

        labels = {_label_key(k): ("matched", v) for k, v in case["matched"].items()}
        labels.update({_label_key(k): ("missing", None) for k in case["missing"]})

        case_correct = 0

        for key, (status, evidence) in labels.items():

            match = by_key.get(key)

            if not match:
                continue

            totals["match_total"] += 1

            if match["status"] == status:
                totals["match_correct"] += 1
                case_correct += 1
            else:
                mistakes.append(f"[{case['name']}] {key}: expected {status}, got {match['status']}")

            if status == "matched" and match["status"] == "matched":

                totals["evidence_total"] += 1

                if match["evidence"] == evidence:
                    totals["evidence_correct"] += 1
                else:
                    mistakes.append(f"[{case['name']}] {key}: evidence expected {evidence}, got {match['evidence']}")

        rows.append((case["name"], precision, recall, case_correct, len(labels)))

    metrics = {
        "requirement_precision": totals["req_tp"] / totals["req_found"] if totals["req_found"] else 1.0,
        "requirement_recall": totals["req_tp"] / totals["req_expected"] if totals["req_expected"] else 1.0,
        "match_accuracy": totals["match_correct"] / totals["match_total"] if totals["match_total"] else 1.0,
        "evidence_accuracy": totals["evidence_correct"] / totals["evidence_total"] if totals["evidence_total"] else 1.0,
        "cases": len(cases),
        "requirements_checked": totals["match_total"],
    }

    return metrics, rows, mistakes


def main():

    metrics, rows, mistakes = evaluate()

    print(f"\nJob Match engine evaluation ({metrics['cases']} hand-labelled cases, rule-based, no AI)\n")
    print(f"{'Case':48} {'Req P':>6} {'Req R':>6} {'Match':>8}")

    for name, precision, recall, correct, total in rows:
        print(f"{name[:48]:48} {precision:6.0%} {recall:6.0%} {correct:>4}/{total:<3}")

    print()
    print(f"Requirement extraction  precision {metrics['requirement_precision']:.0%}   recall {metrics['requirement_recall']:.0%}")
    print(f"Matched / missing       accuracy  {metrics['match_accuracy']:.0%}  ({metrics['requirements_checked']} requirements)")
    print(f"Evidence level          accuracy  {metrics['evidence_accuracy']:.0%}")

    if mistakes:
        print("\nMistakes:")
        for m in mistakes:
            print(" -", m)
    else:
        print("\nNo mistakes on this dataset.")


if __name__ == "__main__":
    main()
