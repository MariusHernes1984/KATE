"""
BOS Agent Evaluering – automatisert kjøring og scoring.

Kjører alle eval-spørsmål mot bertel-o-steen agenten i Azure AI Foundry,
scorer svar med LLM-as-judge, og genererer en rapport.

Bruk:
  python run_eval.py                        # Kjør alle 30 spørsmål
  python run_eval.py --ids 1 2 3            # Kjør kun spesifikke spørsmål
  python run_eval.py --kategori avtale_fakta # Kjør kun én kategori
  python run_eval.py --report-only          # Generer rapport fra siste kjøring
  python run_eval.py --no-judge             # Kjør uten LLM-scoring (kun svar + latency)
"""

import os
import json
import time
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient

load_dotenv(Path(__file__).parent.parent / "deploy" / ".env")

PROJECT_ENDPOINT = os.environ["PROJECT_ENDPOINT"]
AGENT_NAME = os.environ.get("EVAL_AGENT_NAME", "bertel-o-steen")
JUDGE_MODEL = os.environ.get("JUDGE_MODEL", "gpt-4.1")

EVAL_DIR = Path(__file__).parent
QUESTIONS_FILE = EVAL_DIR / "eval_questions.json"
RESULTS_DIR = EVAL_DIR / "resultater"


def load_questions(ids: list[int] | None = None, kategori: str | None = None) -> list[dict]:
    with open(QUESTIONS_FILE, encoding="utf-8") as f:
        questions = json.load(f)
    if ids:
        questions = [q for q in questions if q["id"] in ids]
    if kategori:
        questions = [q for q in questions if q["kategori"] == kategori]
    return questions


def run_agent_question(openai_client, question: str) -> dict:
    """Send spørsmål til versjonert agent via openai.responses.create()."""
    start = time.time()

    response = openai_client.responses.create(
        input=question,
        extra_body={
            "agent_reference": {
                "name": AGENT_NAME,
                "type": "agent_reference",
            }
        },
    )

    elapsed = time.time() - start

    # Hent svar og citations
    answer = response.output_text or ""
    citations = []
    for item in response.output:
        if item.type == "message":
            for block in item.content:
                if hasattr(block, "annotations") and block.annotations:
                    for ann in block.annotations:
                        if hasattr(ann, "url_citation"):
                            citations.append(ann.url_citation.url if hasattr(ann.url_citation, "url") else str(ann))
                        else:
                            citations.append(str(ann))

    return {
        "answer": answer,
        "status": "completed",
        "latency_s": round(elapsed, 2),
        "citations": citations,
        "response_id": response.id,
    }


def judge_answer(openai_client, question: dict, agent_answer: str) -> dict:
    """Bruk LLM-as-judge (chat completion) til å score svaret."""

    judge_prompt = f"""Du er en streng evaluator for en kundeagent hos Atea. Vurder agentens svar mot fasit.

SPØRSMÅL: {question["spørsmål"]}

FASIT: {question["fasit"]}

NØKKELORD SOM BØR FINNES I SVARET: {json.dumps(question["nøkkelord"], ensure_ascii=False)}

AGENTENS SVAR:
{agent_answer}

---

Evaluer og returner BARE et JSON-objekt (ingen annen tekst) med disse feltene:
{{
  "korrekthet": <0-10, hvor presis er informasjonen vs fasit>,
  "nøkkelord_treff": <antall nøkkelord fra listen som faktisk finnes i svaret>,
  "nøkkelord_totalt": {len(question["nøkkelord"])},
  "hallusinering": <0-10, 0=ingen hallusinering, 10=mye feil info>,
  "fullstendighet": <0-10, dekker svaret alle aspekter av fasiten>,
  "formatering": <0-10, er svaret velstrukturert og profesjonelt>,
  "begrunnelse": "<kort forklaring på norsk, maks 2 setninger>"
}}"""

    response = openai_client.chat.completions.create(
        model=JUDGE_MODEL,
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


def calculate_composite_score(scores: dict) -> float:
    """Beregn en samlet score (0-100) fra judge-scores."""
    if scores.get("korrekthet", -1) < 0:
        return 0.0

    hallusinering_inv = 10 - scores.get("hallusinering", 5)

    composite = (
        scores.get("korrekthet", 0) * 0.35
        + scores.get("fullstendighet", 0) * 0.25
        + hallusinering_inv * 0.25
        + scores.get("formatering", 0) * 0.15
    ) * 10

    return round(composite, 1)


def generate_report(results: list[dict], output_dir: Path) -> str:
    """Generer en tekstrapport fra eval-resultater."""
    timestamp = results[0].get("timestamp", "ukjent") if results else "ukjent"

    lines = []
    lines.append("=" * 70)
    lines.append(f"  BOS AGENT EVAL RAPPORT")
    lines.append(f"  Agent: {AGENT_NAME}")
    lines.append(f"  Tidspunkt: {timestamp}")
    lines.append(f"  Antall spørsmål: {len(results)}")
    lines.append("=" * 70)
    lines.append("")

    scores = [r["composite_score"] for r in results if r["composite_score"] > 0]
    latencies = [r["latency_s"] for r in results if r.get("status") == "completed"]
    failed = [r for r in results if r.get("status") != "completed"]

    lines.append("SAMMENDRAG")
    lines.append("-" * 40)
    if scores:
        lines.append(f"  Gjennomsnittlig score:  {sum(scores)/len(scores):.1f}/100")
        lines.append(f"  Median score:           {sorted(scores)[len(scores)//2]:.1f}/100")
        lines.append(f"  Laveste score:          {min(scores):.1f}/100")
        lines.append(f"  Høyeste score:          {max(scores):.1f}/100")
    if latencies:
        lines.append(f"  Gjennomsnittlig latency: {sum(latencies)/len(latencies):.1f}s")
        lines.append(f"  Maks latency:           {max(latencies):.1f}s")
    if failed:
        lines.append(f"  Feilede kjøringer:      {len(failed)}")
    lines.append("")

    kategorier = {}
    for r in results:
        kat = r["kategori"]
        if kat not in kategorier:
            kategorier[kat] = []
        kategorier[kat].append(r)

    lines.append("PER KATEGORI")
    lines.append("-" * 40)
    for kat, items in sorted(kategorier.items()):
        kat_scores = [i["composite_score"] for i in items if i["composite_score"] > 0]
        avg = sum(kat_scores) / len(kat_scores) if kat_scores else 0
        lines.append(f"  {kat:25s}  {avg:5.1f}/100  ({len(items)} spørsmål)")
    lines.append("")

    lines.append("DETALJER PER SPØRSMÅL")
    lines.append("-" * 70)
    for r in results:
        if r["composite_score"] >= 70:
            status_mark = "PASS"
        elif r["composite_score"] >= 40:
            status_mark = "WARN"
        else:
            status_mark = "FAIL"
        lines.append(f"\n  [{status_mark}] #{r['id']} [{r['kategori']}] Score: {r['composite_score']}/100 | Latency: {r['latency_s']}s")
        lines.append(f"  Q: {r['spørsmål'][:80]}{'...' if len(r['spørsmål']) > 80 else ''}")
        if r.get("judge_scores", {}).get("begrunnelse"):
            lines.append(f"  Judge: {r['judge_scores']['begrunnelse']}")
        if r.get("judge_scores", {}).get("nøkkelord_treff") is not None:
            treff = r["judge_scores"]["nøkkelord_treff"]
            totalt = r["judge_scores"].get("nøkkelord_totalt", "?")
            lines.append(f"  Nøkkelord: {treff}/{totalt}")

    lines.append("")
    lines.append("=" * 70)

    lines.append("\nANBEFALINGER")
    lines.append("-" * 40)

    low_scores = [r for r in results if 0 < r["composite_score"] < 60]
    if low_scores:
        lines.append("  Spørsmål med lav score (<60) som bør undersøkes:")
        for r in low_scores:
            lines.append(f"    - #{r['id']}: {r['spørsmål'][:60]}... ({r['composite_score']}/100)")
    else:
        lines.append("  Ingen spørsmål med kritisk lav score.")

    high_latency = [r for r in results if r["latency_s"] > 45]
    if high_latency:
        lines.append(f"\n  Spørsmål med høy latency (>45s): {len(high_latency)} stk")
        for r in high_latency:
            lines.append(f"    - #{r['id']}: {r['latency_s']}s")

    pass_count = len([r for r in results if r["composite_score"] >= 70])
    total = len(results)
    lines.append(f"\n  Bestått (>=70): {pass_count}/{total} ({pass_count/total*100:.0f}%)")

    report = "\n".join(lines)

    report_file = output_dir / "rapport.txt"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report)

    return report


def main():
    import argparse

    parser = argparse.ArgumentParser(description="BOS Agent Evaluering")
    parser.add_argument("--ids", nargs="+", type=int, help="Kjør kun spesifikke spørsmål-IDer")
    parser.add_argument("--kategori", type=str, help="Kjør kun én kategori")
    parser.add_argument("--report-only", action="store_true", help="Generer rapport fra siste kjøring")
    parser.add_argument("--no-judge", action="store_true", help="Hopp over LLM-as-judge scoring")
    parser.add_argument("--output", type=str, help="Mappenavn for resultater (default: timestamp)")
    args = parser.parse_args()

    run_name = args.output or datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = RESULTS_DIR / run_name
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.report_only:
        latest = sorted(RESULTS_DIR.iterdir())[-1] if RESULTS_DIR.exists() else None
        if latest and (latest / "resultater.json").exists():
            with open(latest / "resultater.json", encoding="utf-8") as f:
                results = json.load(f)
            report = generate_report(results, latest)
            print(report)
        else:
            print("Ingen tidligere resultater funnet.")
        return

    questions = load_questions(ids=args.ids, kategori=args.kategori)

    print(f"Kobler til Azure AI Foundry: {PROJECT_ENDPOINT}")
    print(f"Agent: {AGENT_NAME} (via responses API)")
    print(f"Judge: {JUDGE_MODEL} (chat completion)")
    print(f"Antall spørsmål: {len(questions)}")
    print(f"Resultater: {output_dir}\n")

    project_client = AIProjectClient(
        endpoint=PROJECT_ENDPOINT,
        credential=DefaultAzureCredential(),
    )
    openai_client = project_client.get_openai_client()

    results = []
    timestamp = datetime.now().isoformat()

    for i, q in enumerate(questions, 1):
        print(f"[{i}/{len(questions)}] #{q['id']} ({q['kategori']}): {q['spørsmål'][:50]}...")

        # 1. Kjør agenten
        try:
            agent_result = run_agent_question(openai_client, q["spørsmål"])
            print(f"  + completed ({agent_result['latency_s']}s, {len(agent_result['answer'])} chars)")
        except Exception as e:
            print(f"  x Feil: {e}")
            agent_result = {
                "answer": f"FEIL: {e}",
                "status": "failed",
                "latency_s": 0,
                "citations": [],
                "response_id": "",
            }

        # 2. Score med judge
        judge_scores = {}
        composite = 0.0
        if not args.no_judge and agent_result["status"] == "completed":
            try:
                judge_scores = judge_answer(openai_client, q, agent_result["answer"])
                composite = calculate_composite_score(judge_scores)
                begrunnelse = judge_scores.get("begrunnelse", "")[:60]
                print(f"  -> Score: {composite}/100 – {begrunnelse}")
            except Exception as e:
                print(f"  x Judge feil: {e}")
                judge_scores = {"korrekthet": -1, "begrunnelse": f"Judge feil: {e}"}

        result = {
            "id": q["id"],
            "kategori": q["kategori"],
            "spørsmål": q["spørsmål"],
            "fasit": q["fasit"],
            "formål": q.get("formål", ""),
            "agent_svar": agent_result["answer"],
            "status": agent_result["status"],
            "latency_s": agent_result["latency_s"],
            "citations": agent_result["citations"],
            "judge_scores": judge_scores,
            "composite_score": composite,
            "timestamp": timestamp,
        }
        results.append(result)

        # Lagre fortløpende (crash-safe)
        with open(output_dir / "resultater.json", "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

    # Generer rapport
    print("\n" + "=" * 50)
    report = generate_report(results, output_dir)
    print(report)

    print(f"\nResultater lagret til: {output_dir}")
    print(f"  resultater.json  – full data (svar, scores, latency)")
    print(f"  rapport.txt      – lesbar rapport")


if __name__ == "__main__":
    main()
