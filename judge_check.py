"""
AgentSRS — Judge Spot-Check Sampler
=====================================
Stratified sample of judge decisions from pure_102.json.
You read each case and enter your own verdict (Y/N).
Your agreement rate vs the judge is tallied at the end.

Run from the project root:
    .conda\python.exe judge_check.py
"""

import json, pathlib, random, zipfile, sys, textwrap

RESULTS_FILE = pathlib.Path("backend/experiments/results/pure_102.json")
ZIP_PATH     = pathlib.Path("backend/data/ReGen.zip")
SAMPLE_MATCH    = 6
SAMPLE_NO_MATCH = 6
RANDOM_SEED     = 42

if hasattr(sys.stdout, "reconfigure"):
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass

results = json.loads(RESULTS_FILE.read_text(encoding="utf-8"))

with zipfile.ZipFile(ZIP_PATH) as z:
    raw_data = json.loads(z.read("data/re_data.json").decode("utf-8"))

source_lookup = {}
for doc_id, doc in raw_data.items():
    for spec in doc["specifications"]:
        source_lookup[(doc_id, spec["function_name"])] = {
            "description":    spec["function_description"],
            "specifications": spec["function_specifications"],
            "label":          spec["label"],
        }

rng = random.Random(RANDOM_SEED)

def stratified_pick(pool, n):
    by_level = {}
    for r in pool:
        by_level.setdefault(r["sample_level"], []).append(r)
    picked = []
    levels = sorted(by_level.keys())
    iters = {lv: iter(rng.sample(items, len(items))) for lv, items in by_level.items()}
    while len(picked) < n:
        for lv in levels:
            if len(picked) >= n: break
            try: picked.append(next(iters[lv]))
            except StopIteration: pass
    return picked

matched_cases  = [r for r in results if r.get("multi_agent_matched")]
no_match_cases = [r for r in results if r.get("multi_agent_pred") and not r.get("multi_agent_matched")]

sample = stratified_pick(matched_cases, SAMPLE_MATCH) + stratified_pick(no_match_cases, SAMPLE_NO_MATCH)
rng.shuffle(sample)

SEP  = "-" * 72
DSEP = "=" * 72

def wrap(text, indent=4):
    return textwrap.fill(text or "(none)", width=72,
                         initial_indent=" "*indent, subsequent_indent=" "*indent)

def print_case(i, total, r):
    src = source_lookup.get((r["doc_id"], r["function_name"]), {})
    level_label = {1:"L1 Easy", 2:"L2 Medium", 3:"L3 Hard"}.get(r["sample_level"], "?")
    print()
    print(DSEP)
    print(f"  Case {i}/{total}  |  {level_label}  |  gap_type: {r['gap_type']}  |  topic: {r['topic']}")
    print(DSEP)
    print("\n  DESCRIPTION (informal source text):")
    print(wrap(src.get("description", "(not found)")))
    print("\n  SPECIFICATION (formal requirements as given to the model):")
    for j, s in enumerate(src.get("specifications", []), 1):
        print(wrap(f"{j}. {s}", indent=4))
    print(f"\n  GROUND TRUTH -- what was actually removed:")
    print(f"      Short label : {r['absence']}")
    print(f"      Full label  : {src.get('label', r.get('absence','?'))}")
    print(f"\n  MODEL PREDICTED this was missing:")
    print(wrap(r.get("multi_agent_issue") or "(model said nothing / pred=False)"))
    verdict_str = "YES MATCH" if r.get("multi_agent_matched") else "NO MATCH"
    print(f"\n  JUDGE VERDICT : {verdict_str}  (confidence: {r.get('multi_agent_judge_conf','?')})")
    print(f"  Judge reason  :")
    print(wrap(r.get("multi_agent_judge_reason", "(none)")))
    print()

print()
print(DSEP)
print("  AgentSRS -- LLM-as-Judge Spot Check")
print(f"  {len(sample)} cases ({SAMPLE_MATCH} judge-match + {SAMPLE_NO_MATCH} judge-reject), stratified by level")
print("  Read description, spec, ground truth, prediction.")
print("  Form YOUR OWN opinion BEFORE looking at the judge verdict.")
print("  Y = you agree with the judge  |  N = you disagree  |  S = skip")
print(DSEP)
input("  Press Enter to begin...")

agreements = []
judgements = []
skipped = 0

for i, r in enumerate(sample, 1):
    print_case(i, len(sample), r)
    while True:
        ans = input(f"  Agree with judge? (Y/N/S): ").strip().upper()
        if ans in ("Y", "N", "S"): break
        print("  Please enter Y, N, or S.")
    if ans == "S":
        skipped += 1
        print("  Skipped.")
        continue
    agreed = (ans == "Y")
    agreements.append(agreed)
    judgements.append({
        "case_id":       r["id"],
        "level":         r["sample_level"],
        "gap_type":      r["gap_type"],
        "judge_verdict": "MATCH" if r.get("multi_agent_matched") else "NO MATCH",
        "your_verdict":  "AGREE" if agreed else "DISAGREE",
        "judge_conf":    r.get("multi_agent_judge_conf"),
    })
    print(f"  Logged: {'agree' if agreed else 'DISAGREE <-- note this'}")

print()
print(DSEP)
print("  RESULTS")
print(DSEP)
reviewed = len(agreements)
if reviewed == 0:
    print("  No cases reviewed.")
else:
    n_agree    = sum(agreements)
    n_disagree = reviewed - n_agree
    rate       = n_agree / reviewed
    print(f"  Reviewed : {reviewed}  (skipped: {skipped})")
    print(f"  Agreed   : {n_agree}/{reviewed} ({rate:.0%})")
    print(f"  Disagreed: {n_disagree}/{reviewed}")
    print()
    disagree_match   = [j for j in judgements if j["your_verdict"]=="DISAGREE" and j["judge_verdict"]=="MATCH"]
    disagree_nomatch = [j for j in judgements if j["your_verdict"]=="DISAGREE" and j["judge_verdict"]=="NO MATCH"]
    if disagree_match:
        print(f"  WARNING: {len(disagree_match)} case(s) where judge said MATCH but you disagreed (too lenient?):")
        for j in disagree_match:
            print(f"    {j['case_id']}  L{j['level']} {j['gap_type']}  conf={j['judge_conf']}")
    if disagree_nomatch:
        print(f"  WARNING: {len(disagree_nomatch)} case(s) where judge said NO MATCH but you disagreed (too strict?):")
        for j in disagree_nomatch:
            print(f"    {j['case_id']}  L{j['level']} {j['gap_type']}  conf={j['judge_conf']}")
    print()
    if rate >= 0.85:
        print("  ASSESSMENT: >=85% agreement -- judge appears reliable.")
        print("  Report with spot-check disclosure in Threats to Validity.")
    elif rate >= 0.70:
        print("  ASSESSMENT: 70-84% -- borderline. Disclose uncertainty.")
    else:
        print("  ASSESSMENT: <70% -- judge is unreliable. Revisit prompt or drop PURE claim.")
    print()
    print("  Suggested paper wording:")
    print(f'  "A manual spot-check of {reviewed} stratified judge decisions ({SAMPLE_MATCH} matched,')
    print(f'  {SAMPLE_NO_MATCH} rejected) found {rate:.0%} human agreement with the LLM-as-judge')
    print(f'  ({n_disagree} disagreement(s)). This is a small-sample check, not a full')
    print(f'  inter-annotator study; see Threats to Validity."')
print()
print(DSEP)