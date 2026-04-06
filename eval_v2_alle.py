"""
KATE V2 Evaluering – 15 nye spørsmål per agent (BOS, STAF, Komplett)
Kjører mot Azure AI Foundry med LLM-as-judge scoring.
"""

import json, time, sys, io, datetime, os
os.environ["PYTHONIOENCODING"] = "utf-8"

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

LOGFILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "eval_v2_log.txt")
_log = open(LOGFILE, "w", encoding="utf-8")

def log(msg=""):
    _log.write(msg + "\n")
    _log.flush()
    try:
        print(msg, flush=True)
    except Exception:
        pass

log("Connecting to Azure AI Foundry...")
client = AIProjectClient(
    credential=DefaultAzureCredential(),
    endpoint='https://kateecosystem-resource.cognitiveservices.azure.com/api/projects/kateecosystem',
)
oai = client.get_openai_client()
log("Client ready")

JUDGE_MODEL = "gpt-4.1"

AGENTS = [
    {
        "name": "bertel-o-steen",
        "label": "BOS",
        "questions_file": r"eval\eval_questions_BOS_v2.json",
    },
    {
        "name": "Statsforvalteren",
        "label": "STAF",
        "questions_file": r"eval\eval_questions_STAF_v2.json",
    },
    {
        "name": "komplett",
        "label": "Komplett",
        "questions_file": r"eval\eval_questions_Komplett_v2.json",
    },
]


def run_question(agent_name: str, question: str) -> dict:
    """Send spørsmål til agent via conversations + responses API."""
    start = time.time()
    try:
        conv = oai.conversations.create()
        oai.conversations.items.create(
            conversation_id=conv.id,
            items=[{"type": "message", "role": "user", "content": question}],
        )
        response = oai.responses.create(
            conversation=conv.id,
            extra_body={"agent_reference": {"name": agent_name, "type": "agent_reference"}},
            input="",
        )
        elapsed = time.time() - start

        answer = ""
        citations = []
        for out in response.output:
            if out.type == "message":
                for block in out.content:
                    if block.type == "output_text":
                        answer += block.text
                    if hasattr(block, "annotations") and block.annotations:
                        for ann in block.annotations:
                            citations.append(str(ann))

        return {"answer": answer, "status": "completed", "latency_s": round(elapsed, 2), "citations": citations}
    except Exception as e:
        elapsed = time.time() - start
        return {"answer": f"FEIL: {e}", "status": "failed", "latency_s": round(elapsed, 2), "citations": []}


def judge_answer(question: dict, agent_answer: str) -> dict:
    """Score svaret med LLM-as-judge."""
    keywords = question.get("nøkkelord", [])
    judge_prompt = f"""Du er en streng evaluator for en kundeagent hos Atea. Vurder agentens svar mot fasit.

SPØRSMÅL: {question["spørsmål"]}

FASIT: {question["fasit"]}

NØKKELORD SOM BØR FINNES I SVARET: {json.dumps(keywords, ensure_ascii=False)}

AGENTENS SVAR:
{agent_answer}

---

Evaluer og returner BARE et JSON-objekt (ingen annen tekst) med disse feltene:
{{
  "korrekthet": <0-10>,
  "nøkkelord_treff": <antall nøkkelord fra listen som faktisk finnes i svaret>,
  "nøkkelord_totalt": {len(keywords)},
  "hallusinering": <0-10, 0=ingen hallusinering, 10=mye feil info>,
  "fullstendighet": <0-10>,
  "formatering": <0-10>,
  "begrunnelse": "<kort forklaring på norsk, maks 2 setninger>"
}}"""

    try:
        response = oai.chat.completions.create(
            model=JUDGE_MODEL,
            messages=[{"role": "user", "content": judge_prompt}],
            temperature=0,
        )
        judge_text = response.choices[0].message.content
        start = judge_text.find("{")
        end = judge_text.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(judge_text[start:end])
    except Exception as e:
        return {"korrekthet": -1, "begrunnelse": f"Judge feil: {e}"}
    return {"korrekthet": -1, "begrunnelse": "Kunne ikke parse judge-output"}


def composite_score(scores: dict) -> float:
    if scores.get("korrekthet", -1) < 0:
        return 0.0
    hall_inv = 10 - scores.get("hallusinering", 5)
    return round((
        scores.get("korrekthet", 0) * 0.35
        + scores.get("fullstendighet", 0) * 0.25
        + hall_inv * 0.25
        + scores.get("formatering", 0) * 0.15
    ) * 10, 1)


def keyword_score(keywords: list, answer: str) -> float:
    """Beregn keyword-treff prosent."""
    if not keywords:
        return 0.0
    answer_lower = answer.lower()
    hits = sum(1 for kw in keywords if kw.lower() in answer_lower)
    return round(hits / len(keywords) * 100, 1)


# ===== MAIN =====
timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
log(f"KATE V2 Evaluering - {timestamp}")
log(f"Judge: {JUDGE_MODEL}")
log("=" * 110)

all_results = {}

for agent in AGENTS:
    agent_name = agent["name"]
    label = agent["label"]

    with open(agent["questions_file"], "r", encoding="utf-8") as f:
        questions = json.load(f)

    log(f"\n{'=' * 110}")
    log(f"  {label} ({agent_name}) - {len(questions)} sporsmal")
    log(f"{'=' * 110}")

    results = []
    for i, q in enumerate(questions, 1):
        qid = q["id"]
        log(f"\n  [{i}/{len(questions)}] {qid} | {q['kategori']}")
        log(f"  Q: {q['spørsmål'][:90]}")

        # 1. Kjor agent
        agent_result = run_question(agent_name, q["spørsmål"])
        status = agent_result["status"]
        latency = agent_result["latency_s"]
        answer = agent_result["answer"]
        log(f"  -> {status} ({latency}s, {len(answer)} tegn)")

        # 2. Keyword score
        kw_score = keyword_score(q.get("nøkkelord", []), answer)

        # 3. Judge score
        judge_scores = {}
        comp = 0.0
        if status == "completed":
            judge_scores = judge_answer(q, answer)
            comp = composite_score(judge_scores)
            begrunnelse = judge_scores.get("begrunnelse", "")[:80]
            kw_treff = judge_scores.get("nøkkelord_treff", "?")
            kw_tot = judge_scores.get("nøkkelord_totalt", "?")
            log(f"  -> Score: {comp}/100 | Nokkelord: {kw_treff}/{kw_tot} ({kw_score}%) | {begrunnelse}")
        else:
            log(f"  -> FEILET")

        results.append({
            "id": qid,
            "kategori": q["kategori"],
            "spørsmål": q["spørsmål"],
            "fasit": q["fasit"],
            "nøkkelord": q.get("nøkkelord", []),
            "agent_svar": answer,
            "status": status,
            "latency_s": latency,
            "citations": agent_result["citations"],
            "keyword_score_pct": kw_score,
            "judge_scores": judge_scores,
            "composite_score": comp,
        })

    # Sammendrag per agent
    scores = [r["composite_score"] for r in results if r["composite_score"] > 0]
    kw_scores = [r["keyword_score_pct"] for r in results if r["status"] == "completed"]
    latencies = [r["latency_s"] for r in results if r["status"] == "completed"]
    failed = [r for r in results if r["status"] != "completed"]

    log(f"\n  {'─' * 60}")
    log(f"  {label} SAMMENDRAG:")
    if scores:
        avg = sum(scores) / len(scores)
        log(f"    Gjennomsnitt composite:  {avg:.1f}/100")
        log(f"    Min/Max:                 {min(scores):.1f} / {max(scores):.1f}")
    if kw_scores:
        kw_avg = sum(kw_scores) / len(kw_scores)
        log(f"    Gjennomsnitt nokkelord:  {kw_avg:.1f}%")
    if latencies:
        log(f"    Gjennomsnitt latency:    {sum(latencies)/len(latencies):.1f}s")
    if failed:
        log(f"    Feilede:                 {len(failed)}")
    pass_count = len([r for r in results if r["composite_score"] >= 70])
    log(f"    Bestatt (>=70):          {pass_count}/{len(results)}")

    all_results[label] = results

    # Lagre per-agent resultater
    outfile = f"eval_v2_{label.lower()}_resultater.json"
    with open(outfile, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    log(f"    Lagret: {outfile}")


# ===== TOTAL OVERSIKT =====
log(f"\n{'=' * 110}")
log(f"  TOTAL OVERSIKT - KATE V2 EVALUERING")
log(f"{'=' * 110}")

for label, results in all_results.items():
    scores = [r["composite_score"] for r in results if r["composite_score"] > 0]
    kw_scores = [r["keyword_score_pct"] for r in results if r["status"] == "completed"]
    pass_count = len([r for r in results if r["composite_score"] >= 70])
    avg = sum(scores) / len(scores) if scores else 0
    kw_avg = sum(kw_scores) / len(kw_scores) if kw_scores else 0

    grade = "A" if avg >= 90 else "A-" if avg >= 85 else "B+" if avg >= 80 else "B" if avg >= 70 else "C+" if avg >= 60 else "C" if avg >= 50 else "D"
    log(f"  {label:12s}  Composite: {avg:5.1f}/100  Nokkelord: {kw_avg:5.1f}%  Bestatt: {pass_count}/{len(results)}  Karakter: {grade}")

log(f"\n  Tidspunkt: {timestamp}")
log(f"  Judge: {JUDGE_MODEL}")
log(f"{'=' * 110}")
_log.close()
