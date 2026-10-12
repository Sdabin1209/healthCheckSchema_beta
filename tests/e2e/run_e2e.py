#!/usr/bin/env python3
"""E2E trace checker for the 문진 컴포넌트 계약 (no component is executed).

A scenario file holds, per turn, the values that crossed every component
boundary (사용자 입력 → LoRA-A Input/Output → 정규화 → 상태 판정 → 저장 판단/DB →
Transition Plan → LoRA-B Input/Output → 사용자 응답).  This script checks:

  1. schema   every payload satisfies the JSON Schema of its contract
              (../../schemas/<Contract>.json)
  2. chain    a value handed from one component to the next is the same value
              (e.g. ParserOutput.items == AnswerNormalizerInput.items)
  3. store    the DB snapshots follow the Session Store write effects
              (db_after_store = apply(db_before, store_decisions);
               db_final = apply(db_before, store_decisions, Plan updates))
  4. expect   the declared assertions about codes (intent / status / action /
              flow / ...) hold in the trace

Use it on the shipped fixtures, or on traces captured from real components:

    python3 run_e2e.py                       # all scenarios/*.json
    python3 run_e2e.py scenarios/e2e_01_normal.json
    python3 run_e2e.py --trace my_run.json   # same format, e.g. a live capture

Exit code 0 = all checks passed.
Requires: pip install jsonschema
"""
import argparse
import copy
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

HERE = Path(__file__).resolve().parent
SCHEMAS = HERE.parent.parent / "schemas"


# --------------------------------------------------------------------------
# Session Store write effects (rules 9-2). Reference semantics, not production.
# --------------------------------------------------------------------------
def _key(slot):
    return json.dumps(slot, sort_keys=True, ensure_ascii=False)


def apply_store_decisions(records, decisions):
    recs = copy.deepcopy(records)
    idx = {_key(r["slot"]): r for r in recs}
    for dec in decisions:
        r = idx[_key(dec["slot"])]
        a = dec["action"]
        prev = r["current_value"]

        def push():
            if isinstance(prev, dict) and "answer" in prev:
                r["history"].append(prev["answer"])

        if a == "FIRST_WRITE":
            r["current_value"] = {"answer": dec["value"]}; r["risk_mark"] = dec["risk_mark"]
        elif a == "NEW_REVISION":
            push(); r["current_value"] = {"answer": dec["value"]}; r["risk_mark"] = dec["risk_mark"]
        elif a == "RECORD_UNKNOWN":
            push(); r["current_value"] = "UNKNOWN_RECORD"; r["risk_mark"] = None
        elif a == "RECORD_REFUSAL":
            push(); r["current_value"] = "REFUSAL_RECORD"; r["risk_mark"] = None
        elif a == "SET_PENDING":
            r["pending"] = {"pending_id": dec["pending_id"], "value": dec["value"], "risk_mark": dec["risk_mark"]}
        elif a == "ACCEPT_PENDING":
            push(); r["current_value"] = {"answer": r["pending"]["value"]}
            r["risk_mark"] = r["pending"]["risk_mark"]; r["pending"] = None
        elif a == "DROP_PENDING":
            r["pending"] = None
        elif a == "INVALIDATE":
            push(); r["current_value"] = "NONE"; r["risk_mark"] = None; r["pending"] = None
        else:
            raise ValueError(f"unknown store action {a}")
    return recs


def apply_progress_update(progress, upd):
    p = copy.deepcopy(progress)
    p["last_directive"] = copy.deepcopy(upd["last_directive"])
    p["open_requests"] = copy.deepcopy(upd["open_requests"])
    removed = set(upd["skipped_remove"])
    skipped = [s for s in p["skipped"] if s["question_id"] not in removed]  # remove first
    for add in upd["skipped_add"]:
        for s in skipped:
            if s["question_id"] == add["question_id"]:
                s["reason"] = add["reason"]; break
        else:
            skipped.append(copy.deepcopy(add))
    p["skipped"] = skipped
    drop = {_key(x) for x in upd["confirm_stopped_remove"]}
    cs = [c for c in p["confirm_stopped"] if _key(c) not in drop]
    for add in upd["confirm_stopped_add"]:
        if _key(add) not in {_key(x) for x in cs}:
            cs.append(copy.deepcopy(add))
    p["confirm_stopped"] = cs
    if upd["session_status"] is not None:
        p["session_status"] = upd["session_status"]
    p["pause_history"] = p["pause_history"] + copy.deepcopy(upd["pause_history_add"])
    return p


def apply_turn(store, decisions, planner_out):
    s = copy.deepcopy(store)
    s["answer_records"] = apply_store_decisions(store["answer_records"], decisions or [])
    s["progress_record"] = apply_progress_update(store["progress_record"], planner_out["progress_record_update"])
    s["planner_record"] = copy.deepcopy(planner_out["planner_record_update"])
    return s


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def get(trace, dotted):
    """trace is {stage: {contract, data}}; dotted = 'stage.path.to.field' ('' path = whole data)."""
    stage, _, path = dotted.partition(".")
    if stage not in trace:
        raise KeyError(stage)
    node = trace[stage]["data"]
    if path:
        for tok in path.split("."):
            node = node[int(tok)] if isinstance(node, list) else node[tok]
    return node


def subset(want, have):
    if isinstance(want, dict):
        return isinstance(have, dict) and all(k in have and subset(v, have[k]) for k, v in want.items())
    if isinstance(want, list):
        return isinstance(have, list) and len(want) == len(have) and all(subset(a, b) for a, b in zip(want, have))
    return want == have


def resolve(trace, path):
    """'stage.a.b[*].c' -> list of values."""
    stage, _, rest = path.partition(".")
    nodes = [trace[stage]["data"]]
    for tok in [t for t in rest.split(".") if t]:
        name, star = (tok[:-3], True) if tok.endswith("[*]") else (tok, False)
        nxt = []
        for n in nodes:
            v = n[name] if name else n
            nxt.extend(v if star else [v])
        nodes = nxt
    return nodes


# --------------------------------------------------------------------------
# checks
# --------------------------------------------------------------------------
# (from, to) pairs whose values must be identical when both stages exist.
CHAIN = [
    ("lora_a_output.items", "normalizer_input.items"),
    ("lora_a_output.items", "judge_input.items"),
    ("normalization_result.item_checks", "judge_input.item_checks"),
    ("normalization_result.missing_required_slots", "judge_input.missing_required_slots"),
    ("judge_output.judgments", "record_writer_input.judgments"),
    ("judge_output.judgments", "planner_input.judgments"),
    ("judge_output.invalidated_questions", "record_writer_input.invalidated_questions"),
    ("judge_output.utterance_judgment", "planner_input.utterance_judgment"),
    ("db_result.store_summary", "planner_input.store_summary"),
    ("orchestrator_output.turn_kind", "planner_input.turn_kind"),
    ("transition_plan.directive", "lora_b_input.directive"),
    ("transition_plan.staff_alert", "staff_console_input.staff_alert.staff_alert"),
    ("db_before.planner_record", "planner_input.planner_record"),
    ("db_before.progress_record.open_requests", "planner_input.open_requests"),
    ("db_before.progress_record.skipped", "planner_input.skipped"),
    ("db_before.progress_record.confirm_stopped", "planner_input.confirm_stopped"),
    ("db_before.progress_record.last_directive", "planner_input.last_directive"),
    ("db_before.progress_record.last_directive", "lora_a_input.last_directive"),
    ("db_before.progress_record.last_directive", "judge_input.last_directive"),
    ("question_bank", "planner_input.question_bank"),
    ("db_final.session_info", "dispatch_input.session_info"),
    ("db_final.answer_records", "dispatch_input.answer_records"),
    ("db_final.progress_record.skipped", "dispatch_input.skipped"),
    ("db_final.progress_record.confirm_stopped", "dispatch_input.confirm_stopped"),
    ("db_final.progress_record.session_status", "dispatch_input.session_status"),
    ("db_final.progress_record.pause_history", "dispatch_input.pause_history"),
    ("orchestrator_output.turn_failure_signal", "frontend_input.turn_failure_signal"),
    ("orchestrator_output.turn_failure_signal", "staff_console_input.turn_failure_signal"),
    ("orchestrator_output.intervention_result", "staff_console_input.intervention_result"),
]


def check_schema(trace, validators, problems):
    for stage, entry in trace.items():
        c = entry["contract"]
        if c not in validators:
            problems.append(f"[schema] {stage}: unknown contract {c}")
            continue
        for err in validators[c].iter_errors(entry["data"]):
            loc = "/".join(str(p) for p in err.absolute_path)
            problems.append(f"[schema] {stage} ({c}) /{loc}: {err.message[:160]}")


def check_chain(trace, problems):
    for a, b in CHAIN:
        sa, sb = a.split(".")[0], b.split(".")[0]
        if sa not in trace or sb not in trace:
            continue
        try:
            va, vb = get(trace, a), get(trace, b)
        except (KeyError, IndexError, TypeError):
            continue
        if va != vb:
            problems.append(f"[chain] {a} != {b}")
    # utterance text travels as a plain string
    if "input_message" in trace and trace["input_message"]["contract"] == "FrontendMessage":
        msg = trace["input_message"]["data"]
        if "orchestrator_input" in trace and trace["orchestrator_input"]["data"]["frontend_input"] != msg:
            problems.append("[chain] input_message != orchestrator_input.frontend_input")
        for st in ("lora_a_input", "judge_input", "lora_b_input"):
            if st in trace:
                d = trace[st]["data"]
                if d.get("utterance") != msg.get("utterance"):
                    problems.append(f"[chain] input_message.utterance != {st}.utterance")
    # response text goes to the frontend unchanged unless the turn failed
    if "lora_b_output" in trace and "frontend_input" in trace:
        fi = trace["frontend_input"]["data"]
        if fi["turn_failure_signal"] is None and fi["response_text"] != trace["lora_b_output"]["data"]["response_text"]:
            problems.append("[chain] lora_b_output.response_text != frontend_input.response_text")


def check_store(trace, problems):
    if "db_before" not in trace:
        return
    before = trace["db_before"]["data"]
    decisions = trace["db_result"]["data"]["store_decisions"] if "db_result" in trace else []
    if "db_after_store" in trace:
        want = apply_store_decisions(before["answer_records"], decisions)
        if want != trace["db_after_store"]["data"]["answer_records"]:
            problems.append("[store] db_after_store.answer_records != apply(db_before, store_decisions)")
    if "planner_input" in trace and "db_after_store" in trace:
        if trace["planner_input"]["data"]["answer_records"] != trace["db_after_store"]["data"]["answer_records"]:
            problems.append("[store] planner_input.answer_records != db_after_store.answer_records")
    if "transition_plan" in trace and "db_final" in trace:
        want = apply_turn(before, decisions, trace["transition_plan"]["data"])
        got = trace["db_final"]["data"]
        for part in ("answer_records", "progress_record", "planner_record", "session_info"):
            if part == "session_info":
                continue
            if want[part] != got[part]:
                problems.append(f"[store] db_final.{part} != apply(db_before, decisions, Plan updates)")


def check_expect(trace, assertions, problems):
    for a in assertions:
        try:
            vals = resolve(trace, a["path"])
        except (KeyError, IndexError, TypeError):
            problems.append(f"[expect] {a['id']}: path not found {a['path']}")
            continue
        op, want = a["op"], a["value"]
        if op == "contains_subset":  # path may end at an array: look inside it
            vals = [x for v in vals for x in (v if isinstance(v, list) else [v])]
        if op == "equals":
            ok = len(vals) == 1 and vals[0] == want
        elif op == "set_equals":
            ok = set(map(json.dumps, vals)) == set(map(json.dumps, want))
        elif op == "contains_subset":
            ok = all(any(subset(w, v) for v in vals) for w in want)
        elif op == "is_null":
            ok = all(v is None for v in vals) == bool(want)
        else:
            problems.append(f"[expect] {a['id']}: unknown op {op}")
            continue
        if not ok:
            problems.append(f"[expect] {a['id']} ({a['desc']}): {a['path']} -> {vals!r}, wanted {op} {want!r}")


def load_validators():
    out = {}
    for p in SCHEMAS.glob("*.json"):
        schema = json.loads(p.read_text(encoding="utf-8"))
        out[p.stem] = Draft202012Validator(schema)
    return out


def run_scenario(path, validators):
    sc = json.loads(Path(path).read_text(encoding="utf-8"))
    qb_path = (Path(path).parent / sc.get("question_bank_ref", "")).resolve() if sc.get("question_bank_ref") else None
    qb = json.loads(qb_path.read_text(encoding="utf-8")) if qb_path and qb_path.exists() else None
    results = []
    for turn in sc["turns"]:
        trace = turn["trace"]
        if qb is not None and "question_bank" not in trace:
            trace = {**trace, "question_bank": {"contract": "QuestionBank", "data": qb}}
        problems = []
        check_schema(trace, validators, problems)
        check_chain(trace, problems)
        check_store(trace, problems)
        check_expect(trace, turn.get("assertions", []), problems)
        results.append((turn["turn"], turn.get("source_case"), len(trace), len(turn.get("assertions", [])), problems))
    return sc, results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="*")
    ap.add_argument("--trace", help="a captured trace file in scenario format")
    args = ap.parse_args()
    files = args.files or ([args.trace] if args.trace else sorted(str(p) for p in (HERE / "scenarios").glob("e2e_*.json")))
    validators = load_validators()
    bad = 0
    for f in files:
        sc, results = run_scenario(f, validators)
        print(f"{sc['scenario_id']}  {sc['title']}")
        for turn, case, n, na, problems in results:
            status = "PASS" if not problems else "FAIL"
            print(f"  turn {turn} [{case}] stages={n} assertions={na}  {status}")
            for p in problems:
                print("     -", p)
            bad += bool(problems)
    print("\nALL PASSED" if not bad else f"\n{bad} turn(s) with problems")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
