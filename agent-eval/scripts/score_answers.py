"""
KATE Agent Evaluation Scorer — Dual Scoring
Combines keyword-matching (fast, deterministic) with LLM-as-judge (semantic, comprehensive).

Usage:
    python score_answers.py <results_json> [--output <scored_json>] [--no-judge] [--sharepoint]

Examples:
    python score_answers.py eval_staf_resultater.json                    # Full dual scoring
    python score_answers.py eval_staf_resultater.json --no-judge         # Keyword only (fast)
    python score_answers.py eval_komplett_sp_resultater.json --sharepoint # Include SP indicators
"""

import json, re, sys, os, argparse, time
from pathlib import Path


# ---------------------------------------------------------------------------
# Method 1: Keyword-matching (hurtigsjekk)
# ---------------------------------------------------------------------------

def keyword_score(expected: str, actual: str) -> dict:
    """Score an answer by checking how many key facts from expected appear in actual.

    Splits expected answer on common delimiters to extract discrete facts.
    For each fact, checks if at least 50% of significant words (>3 chars) appear.
    Returns dict with score (0-100), facts found, and details.
    """
    key_facts = [t.strip() for t in re.split(r'[.,;()\n]', expected) if len(t.strip()) > 3]
    if not key_facts:
        return {"score": 100.0, "treff": 0, "totalt": 0, "detaljer": []}

    hits = 0
    details = []
    for fact in key_facts:
        words = [w for w in fact.split() if len(w) > 3 and not w.startswith('+')]
        if words:
            matches = sum(1 for w in words if w.lower() in actual.lower())
            matched = matches >= len(words) * 0.5
            if matched:
                hits += 1
            details.append({
                "fakta": fact,
                "ord_totalt": len(words),
                "ord_treff": matches,
                "bestatt": matched,
            })

    score = min(hits / max(len(key_facts), 1) * 100, 100)
    return {
        "score": round(score, 1),
        "treff": hits,
        "totalt": len(key_facts),
        "detaljer": details,
    }


# ---------------------------------------------------------------------------
# Method 2: LLM-as-Judge (hovedscore)
# ---------------------------------------------------------------------------

def get_judge_client():
    """Create Azure OpenAI client for LLM-as-judge scoring."""
    try:
        from azure.ai.projects import AIProjectClient
        from azure.identity import DefaultAzureCredential

        endpoint = os.environ.get(
            "PROJECT_ENDPOINT",
            "https://kateecosystem-resource.services.ai.azure.com/api/projects/kateecosystem"
        )
        project_client = AIProjectClient(
            endpoint=endpoint,
            credential=DefaultAzureCredential(),
        )
        return project_client.get_openai_client()
    except Exception as e:
        print(f"  ! Kunne ikke opprette judge-klient: {e}")
        return None


def judge_answer(openai_client, question: dict, agent_answer: str,
                 judge_model: str = "gpt-4.1") -> dict:
    """Use LLM-as-judge to score the answer semantically.

    Returns dict with korrekthet, hallusinering, fullstendighet, formatering,
    nokkelord_treff, nokkelord_totalt, and begrunnelse.
    """
    # Extract keywords from forventet if not provided
    nokkelord = question.get("nokkelord", [])
    if not nokkelord:
        # Auto-extract significant terms from expected answer
        words = re.findall(r'\b\w+\b', question["forventet"])
        nokkelord = [w for w in words if len(w) > 4 and not w.lower() in
                     {"dette", "disse", "eller", "andre", "under", "mellom", "etter", "fra"}]
        nokkelord = list(dict.fromkeys(nokkelord))[:10]  # Dedupe, max 10

    judge_prompt = f"""Du er en streng evaluator for en kundeagent hos Atea. Vurder agentens svar mot fasit.

SPØRSMÅL: {question["sporsmal"]}

FASIT: {question["forventet"]}

NØKKELORD SOM BØR FINNES I SVARET: {json.dumps(nokkelord, ensure_ascii=False)}

AGENTENS SVAR:
{agent_answer}

---

Evaluer og returner BARE et JSON-objekt (ingen annen tekst) med disse feltene:
{{
  "korrekthet": <0-10, hvor presis er informasjonen vs fasit>,
  "nokkelord_treff": <antall nøkkelord fra listen som faktisk finnes i svaret>,
  "nokkelord_totalt": {len(nokkelord)},
  "hallusinering": <0-10, 0=ingen hallusinering, 10=mye feil info>,
  "fullstendighet": <0-10, dekker svaret alle aspekter av fasiten>,
  "formatering": <0-10, er svaret velstrukturert og profesjonelt>,
  "begrunnelse": "<kort forklaring på norsk, maks 2 setninger>"
}}"""

    response = openai_client.chat.completions.create(
        model=judge_model,
        messages=[{"role": "user", "content": judge_prompt}],
        temperature=0,
    )

    judge_text = response.choices[0].message.content

    try:
        start = judge_text.find("{")
        end = judge_text.rfind("}") + 1
        if start >= 0 and end > start:
            scores = json.loads(judge_text[start:end])
        else:
            scores = {"korrekthet": -1, "begrunnelse": "Kunne ikke parse judge-output"}
    except json.JSONDecodeError:
        scores = {"korrekthet": -1, "begrunnelse": f"JSON parse feil: {judge_text[:200]}"}

    return scores


def calculate_composite(judge_scores: dict) -> float:
    """Calculate composite score (0-100) from judge scores.

    Weights: 35% correctness, 25% completeness, 25% anti-hallucination, 15% formatting.
    """
    if judge_scores.get("korrekthet", -1) < 0:
        return 0.0

    hallusinering_inv = 10 - judge_scores.get("hallusinering", 5)

    composite = (
        judge_scores.get("korrekthet", 0) * 0.35
        + judge_scores.get("fullstendighet", 0) * 0.25
        + hallusinering_inv * 0.25
        + judge_scores.get("formatering", 0) * 0.15
    ) * 10

    return round(composite, 1)


# ---------------------------------------------------------------------------
# SharePoint Grounding Indicators
# ---------------------------------------------------------------------------

def check_sharepoint_indicators(answer: str) -> list[str]:
    """Check if the answer shows evidence of SharePoint document retrieval."""
    indicators = []
    lower = answer.lower()

    checks = [
        (["ifølge", "i følge", "ifolge", "i dokumentet", "i rapporten", "basert på", "basert pa", "fra sharepoint"],
         "Refererer til dokument/kilde"),
        (["discovery", "mapping", "purview", "sensitivity label"],
         "Copilot Discovery-terminologi"),
        (["sprint", "scrum", "artikkel 20", "artikkel 23"],
         "NIS2 prosjektplan-detaljer"),
        (["klientdagen", "sikkerhetsdagen", "community"],
         "Møtereferat-detaljer"),
        (["pilotprogram", "pilot"],
         "Copilot pilot-detaljer"),
        (["dlp", "mrm", "compliance manager"],
         "Purview/DLP-funn"),
    ]

    for terms, label in checks:
        if any(term in lower for term in terms):
            indicators.append(label)

    return indicators


# ---------------------------------------------------------------------------
# Dual scoring orchestration
# ---------------------------------------------------------------------------

def score_results(results: list[dict], use_judge: bool = True,
                  include_sp: bool = False, judge_model: str = "gpt-4.1") -> list[dict]:
    """Score all results with keyword-matching and optionally LLM-as-judge."""
    openai_client = None
    if use_judge:
        openai_client = get_judge_client()
        if not openai_client:
            print("  ! Faller tilbake til kun keyword-scoring")
            use_judge = False

    scored = []
    for i, r in enumerate(results, 1):
        print(f"  [{i}/{len(results)}] {r['id']} ({r['kategori']})...", end=" ")

        # Method 1: Keyword
        kw = keyword_score(r["forventet"], r["svar"])

        entry = {
            **r,
            "keyword_score": kw["score"],
            "keyword_detaljer": {
                "treff": kw["treff"],
                "totalt": kw["totalt"],
            },
        }

        # Method 2: LLM-as-judge
        if use_judge:
            try:
                judge_scores = judge_answer(openai_client, r, r["svar"], judge_model)
                composite = calculate_composite(judge_scores)
                entry["judge_scores"] = judge_scores
                entry["composite_score"] = composite
                begrunnelse = judge_scores.get("begrunnelse", "")[:60]
                print(f"KW: {kw['score']}% | Judge: {composite}/100 — {begrunnelse}")
            except Exception as e:
                print(f"Judge feil: {e}")
                entry["judge_scores"] = {"korrekthet": -1, "begrunnelse": str(e)}
                entry["composite_score"] = 0.0
        else:
            entry["composite_score"] = kw["score"]
            print(f"KW: {kw['score']}%")

        # SharePoint indicators
        if include_sp:
            entry["sharepoint_indikatorer"] = check_sharepoint_indicators(r["svar"])

        scored.append(entry)

    return scored


def category_averages(scored: list[dict], score_field: str = "composite_score") -> dict[str, float]:
    """Calculate average scores per category."""
    categories = {}
    for s in scored:
        cat = s["kategori"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(s.get(score_field, 0))
    return {k: round(sum(v) / len(v), 1) for k, v in categories.items()}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Score KATE agent evaluation results (dual scoring)")
    parser.add_argument("results_json", help="Path to results JSON file")
    parser.add_argument("--output", "-o", help="Output path for scored JSON")
    parser.add_argument("--no-judge", action="store_true", help="Skip LLM-as-judge, keyword only")
    parser.add_argument("--sharepoint", "-sp", action="store_true", help="Include SharePoint grounding indicators")
    parser.add_argument("--judge-model", default="gpt-4.1", help="Model for LLM-as-judge (default: gpt-4.1)")
    args = parser.parse_args()

    with open(args.results_json, "r", encoding="utf-8") as f:
        results = json.load(f)

    print(f"Scorer {len(results)} sporsmal...")
    print(f"  Keyword-matching: JA")
    print(f"  LLM-as-judge: {'NEI (--no-judge)' if args.no_judge else f'JA ({args.judge_model})'}")
    print(f"  SharePoint-indikatorer: {'JA' if args.sharepoint else 'NEI'}")
    print()

    scored = score_results(
        results,
        use_judge=not args.no_judge,
        include_sp=args.sharepoint,
        judge_model=args.judge_model,
    )

    # Aggregates
    kw_avg = sum(s["keyword_score"] for s in scored) / len(scored)
    composite_avg = sum(s["composite_score"] for s in scored) / len(scored)
    cat_avgs_composite = category_averages(scored, "composite_score")
    cat_avgs_kw = category_averages(scored, "keyword_score")

    # Output
    output_path = args.output or args.results_json.replace(".json", "_scored.json")
    output_data = {
        "scoring_metode": "dual" if not args.no_judge else "keyword_only",
        "judge_model": args.judge_model if not args.no_judge else None,
        "keyword_gjennomsnitt": round(kw_avg, 1),
        "composite_gjennomsnitt": round(composite_avg, 1),
        "kategori_gjennomsnitt_composite": cat_avgs_composite,
        "kategori_gjennomsnitt_keyword": cat_avgs_kw,
        "antall_sporsmal": len(scored),
        "resultater": scored,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    # Print summary
    print(f"\n{'='*60}")
    print(f"SAMMENDRAG")
    print(f"{'='*60}")
    print(f"  Keyword-snitt:   {kw_avg:.1f}%")
    if not args.no_judge:
        print(f"  Composite-snitt: {composite_avg:.1f}/100")
    print(f"\nKategorier (composite / keyword):")
    for cat in sorted(cat_avgs_composite.keys(), key=lambda c: -cat_avgs_composite[c]):
        comp = cat_avgs_composite[cat]
        kw = cat_avgs_kw[cat]
        badge = "OK" if comp >= 80 else "DELVIS" if comp >= 60 else "SVAK"
        print(f"  {cat:30s}  {comp:5.1f} / {kw:5.1f}%  ({badge})")

    # Flag divergences
    divergences = []
    for s in scored:
        diff = abs(s["composite_score"] - s["keyword_score"])
        if diff > 25:
            divergences.append(s)

    if divergences:
        print(f"\nDIVERGENSER (>25 poeng mellom keyword og judge):")
        for s in divergences:
            print(f"  {s['id']:12s} KW: {s['keyword_score']:5.1f}% vs Judge: {s['composite_score']:5.1f}/100")
            if s.get("judge_scores", {}).get("begrunnelse"):
                print(f"             {s['judge_scores']['begrunnelse'][:80]}")

    print(f"\nResultater lagret i: {output_path}")


if __name__ == "__main__":
    main()
