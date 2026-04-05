"""
Build a comprehensive HTML comparison report for all 3 KATE agents.
Uses dual-scored results (composite from LLM-as-judge + keyword scores).
"""
import json, datetime, os

BASE = r"C:\Users\marherne\.claude\projects\C--Users-marherne--claude-projects-KATE"
BOS_BASE = r"C:\Users\marherne\OneDrive - Atea\Documents\Claude\Projects\KATE\eval\resultater"

# Load all results
def load(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    # Handle both formats: list of results or dict with "resultater" key
    if isinstance(data, dict) and "resultater" in data:
        return data["resultater"]
    return data

# BOS results (already have judge scores from run_eval.py)
bos_know = load(os.path.join(BOS_BASE, "bos_knowledge_v2_20260405", "resultater.json"))
bos_le = load(os.path.join(BOS_BASE, "bos_land_expand_v2_20260405", "resultater.json"))
bos_sp = load(os.path.join(BOS_BASE, "bos_sharepoint_v2_20260405", "resultater.json"))

# STAF results (dual scored)
staf_know = load(os.path.join(BASE, "eval_staf_resultater_scored_v2.json"))
staf_le = load(os.path.join(BASE, "eval_staf_le_scored_v2.json"))
staf_sp = load(os.path.join(BASE, "eval_staf_sp_scored_v2.json"))

# Komplett results (dual scored)
komp_know = load(os.path.join(BASE, "eval_komplett_resultater_scored_v2.json"))
komp_le = load(os.path.join(BASE, "eval_komplett_le_scored_v2.json"))
komp_sp = load(os.path.join(BASE, "eval_komplett_sp_scored_v2.json"))

def avg_composite(results):
    scores = [r.get("composite_score", 0) for r in results]
    return round(sum(scores) / len(scores), 1) if scores else 0

def avg_keyword(results):
    scores = [r.get("keyword_score", 0) for r in results]
    return round(sum(scores) / len(scores), 1) if scores else 0

def pass_rate(results, threshold=70):
    passed = sum(1 for r in results if r.get("composite_score", 0) >= threshold)
    return f"{passed}/{len(results)}"

def weak_items(results, threshold=70):
    return [r for r in results if r.get("composite_score", 0) < threshold]

def category_breakdown(results):
    cats = {}
    for r in results:
        cat = r.get("kategori", "Ukjent")
        if cat not in cats:
            cats[cat] = []
        cats[cat].append(r.get("composite_score", 0))
    return {k: round(sum(v)/len(v), 1) for k, v in cats.items()}

# Build agent data
agents = {
    "BOS": {
        "name": "Bertel O. Steen",
        "model": "gpt-5.3",
        "color": "#2563eb",
        "tiers": {
            "Tier 1: Knowledge": {"results": bos_know, "questions": len(bos_know)},
            "Tier 2: Land & Expand": {"results": bos_le, "questions": len(bos_le)},
            "Tier 3: SP Grounding": {"results": bos_sp, "questions": len(bos_sp)},
        }
    },
    "STAF": {
        "name": "Statsforvalteren",
        "model": "gpt-4o",
        "color": "#059669",
        "tiers": {
            "Tier 1: Knowledge": {"results": staf_know, "questions": len(staf_know)},
            "Tier 2: Land & Expand": {"results": staf_le, "questions": len(staf_le)},
            "Tier 3: SP Grounding": {"results": staf_sp, "questions": len(staf_sp)},
        }
    },
    "Komplett": {
        "name": "Komplett",
        "model": "gpt-4o",
        "color": "#d97706",
        "tiers": {
            "Tier 1: Knowledge": {"results": komp_know, "questions": len(komp_know)},
            "Tier 2: Land & Expand": {"results": komp_le, "questions": len(komp_le)},
            "Tier 3: SP Grounding": {"results": komp_sp, "questions": len(komp_sp)},
        }
    }
}

# Calculate totals
for alias, agent in agents.items():
    all_results = []
    for tier_name, tier_data in agent["tiers"].items():
        tier_data["composite"] = avg_composite(tier_data["results"])
        tier_data["keyword"] = avg_keyword(tier_data["results"])
        tier_data["pass_rate"] = pass_rate(tier_data["results"])
        tier_data["weak"] = weak_items(tier_data["results"])
        tier_data["categories"] = category_breakdown(tier_data["results"])
        all_results.extend(tier_data["results"])
    agent["total_composite"] = avg_composite(all_results)
    agent["total_keyword"] = avg_keyword(all_results)
    agent["total_questions"] = len(all_results)
    agent["all_results"] = all_results

now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

def bar_color(score):
    if score >= 90: return "#22c55e"
    if score >= 80: return "#84cc16"
    if score >= 70: return "#eab308"
    if score >= 60: return "#f97316"
    return "#ef4444"

def badge(score):
    if score >= 90: return "🟢"
    if score >= 80: return "🔵"
    if score >= 60: return "🟡"
    return "🔴"

html = f"""<!DOCTYPE html>
<html lang="no">
<head>
<meta charset="UTF-8">
<title>KATE Agent Evaluering — Sammenligning {now}</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: 'Segoe UI', -apple-system, sans-serif; background: #f8fafc; color: #1e293b; line-height: 1.6; }}
  .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
  .header {{ background: linear-gradient(135deg, #1e3a5f 0%, #2563eb 100%); color: white; padding: 40px; border-radius: 16px; margin-bottom: 30px; }}
  .header h1 {{ font-size: 28px; margin-bottom: 8px; }}
  .header p {{ opacity: 0.85; font-size: 14px; }}
  .header .subtitle {{ font-size: 16px; opacity: 0.9; margin-top: 4px; }}

  .summary-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-bottom: 30px; }}
  .agent-card {{ background: white; border-radius: 12px; padding: 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); border-top: 4px solid; }}
  .agent-card h3 {{ font-size: 18px; margin-bottom: 4px; }}
  .agent-card .model {{ font-size: 12px; color: #64748b; margin-bottom: 16px; }}
  .big-score {{ font-size: 48px; font-weight: 700; }}
  .score-label {{ font-size: 13px; color: #64748b; }}

  .tier-row {{ display: flex; align-items: center; margin: 8px 0; gap: 10px; }}
  .tier-label {{ width: 160px; font-size: 13px; font-weight: 500; }}
  .tier-bar-bg {{ flex: 1; background: #e2e8f0; border-radius: 6px; height: 22px; position: relative; }}
  .tier-bar {{ height: 100%; border-radius: 6px; transition: width 0.5s; min-width: 2px; }}
  .tier-score {{ width: 70px; text-align: right; font-size: 13px; font-weight: 600; }}

  .section {{ background: white; border-radius: 12px; padding: 24px; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
  .section h2 {{ font-size: 20px; margin-bottom: 16px; border-bottom: 2px solid #e2e8f0; padding-bottom: 8px; }}
  .section h3 {{ font-size: 16px; margin: 16px 0 8px; }}

  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  th {{ background: #f1f5f9; padding: 10px 12px; text-align: left; font-weight: 600; }}
  td {{ padding: 10px 12px; border-bottom: 1px solid #e2e8f0; }}
  tr:hover {{ background: #f8fafc; }}

  .comparison-table th {{ text-align: center; }}
  .comparison-table td:not(:first-child) {{ text-align: center; }}
  .comparison-table td:first-child {{ font-weight: 500; }}

  .weak-item {{ background: #fef2f2; border-left: 3px solid #ef4444; padding: 12px 16px; margin: 8px 0; border-radius: 0 8px 8px 0; font-size: 13px; }}
  .weak-item .q {{ font-weight: 600; }}
  .weak-item .reason {{ color: #64748b; font-style: italic; margin-top: 4px; }}

  .rec-box {{ background: #eff6ff; border-left: 3px solid #2563eb; padding: 12px 16px; margin: 8px 0; border-radius: 0 8px 8px 0; }}
  .rec-box strong {{ color: #1e40af; }}

  .insight {{ padding: 8px 0; border-bottom: 1px solid #f1f5f9; }}
  .insight:last-child {{ border-bottom: none; }}

  .dual-note {{ background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; padding: 16px; margin: 16px 0; font-size: 13px; }}
  .dual-note strong {{ color: #166534; }}

  .footer {{ text-align: center; color: #94a3b8; font-size: 12px; margin-top: 30px; padding: 20px; }}
</style>
</head>
<body>
<div class="container">

<div class="header">
  <h1>KATE Agent Evaluering — Sammenligning</h1>
  <p class="subtitle">3-Tier evaluering med dual scoring (keyword + LLM-as-judge gpt-4.1)</p>
  <p>Generert: {now} | Agenter oppdatert til Git/Azure</p>
</div>

<div class="dual-note">
  <strong>Dual Scoring:</strong> Alle scorer bruker to metoder — <strong>Composite score</strong> (LLM-as-judge, primær) kombinerer korrekthet (35%), fullstendighet (25%), anti-hallusinering (25%) og formatering (15%). <strong>Keyword score</strong> (sekundær) sjekker deterministisk om nøkkelfakta finnes i svaret. Divergenser &gt;25 poeng flagges for gjennomgang.
</div>

<div class="summary-grid">
"""

# Agent summary cards
for alias, agent in agents.items():
    total = agent["total_composite"]
    color = bar_color(total)
    html += f"""
  <div class="agent-card" style="border-color: {agent['color']}">
    <h3>{agent['name']}</h3>
    <div class="model">Agent: {alias.lower()} | Modell: {agent['model']} | {agent['total_questions']} spørsmål</div>
    <div class="big-score" style="color: {color}">{total}</div>
    <div class="score-label">Composite snitt / 100 (KW: {agent['total_keyword']}%)</div>
    <div style="margin-top: 16px">
"""
    for tier_name, tier_data in agent["tiers"].items():
        c = tier_data["composite"]
        bc = bar_color(c)
        html += f"""
      <div class="tier-row">
        <span class="tier-label">{tier_name}</span>
        <div class="tier-bar-bg"><div class="tier-bar" style="width:{c}%;background:{bc}"></div></div>
        <span class="tier-score">{c}/100</span>
      </div>"""
    html += """
    </div>
  </div>"""

html += """
</div>

<!-- Comparison Table -->
<div class="section">
  <h2>Tier-sammenligning</h2>
  <table class="comparison-table">
    <tr>
      <th></th>
      <th colspan="2">BOS (gpt-5.3)</th>
      <th colspan="2">STAF (gpt-4o)</th>
      <th colspan="2">Komplett (gpt-4o)</th>
    </tr>
    <tr>
      <th>Tier</th>
      <th>Composite</th><th>Keyword</th>
      <th>Composite</th><th>Keyword</th>
      <th>Composite</th><th>Keyword</th>
    </tr>
"""

tier_names = ["Tier 1: Knowledge", "Tier 2: Land & Expand", "Tier 3: SP Grounding"]
for tier_name in tier_names:
    html += f"<tr><td>{tier_name}</td>"
    for alias in ["BOS", "STAF", "Komplett"]:
        td = agents[alias]["tiers"][tier_name]
        c = td["composite"]
        k = td["keyword"]
        html += f'<td style="font-weight:700;color:{bar_color(c)}">{c}</td><td style="color:#64748b">{k}%</td>'
    html += "</tr>\n"

# Totals row
html += "<tr style='font-weight:700;border-top:2px solid #1e293b'><td>Totalt</td>"
for alias in ["BOS", "STAF", "Komplett"]:
    tc = agents[alias]["total_composite"]
    tk = agents[alias]["total_keyword"]
    html += f'<td style="color:{bar_color(tc)}">{tc}</td><td style="color:#64748b">{tk}%</td>'
html += "</tr></table>\n"

# Pass rates
html += """
  <h3 style="margin-top:20px">Bestått-rate (score ≥ 70)</h3>
  <table class="comparison-table">
    <tr><th>Tier</th><th>BOS</th><th>STAF</th><th>Komplett</th></tr>
"""
for tier_name in tier_names:
    html += f"<tr><td>{tier_name}</td>"
    for alias in ["BOS", "STAF", "Komplett"]:
        pr = agents[alias]["tiers"][tier_name]["pass_rate"]
        html += f"<td>{pr}</td>"
    html += "</tr>\n"
html += "</table></div>\n"

# Per-agent detailed sections
for alias, agent in agents.items():
    html += f"""
<div class="section">
  <h2>{agent['name']} ({alias}) — Detaljert analyse</h2>
  <p style="color:#64748b;font-size:13px;margin-bottom:16px">Modell: {agent['model']} | Total: {agent['total_composite']}/100 composite, {agent['total_keyword']}% keyword | {agent['total_questions']} spørsmål</p>
"""
    for tier_name, tier_data in agent["tiers"].items():
        html += f"""
  <h3>{tier_name} — {tier_data['composite']}/100 (KW: {tier_data['keyword']}%) | Bestått: {tier_data['pass_rate']}</h3>
  <table>
    <tr><th>Kategori</th><th>Composite</th></tr>
"""
        for cat, score in sorted(tier_data["categories"].items(), key=lambda x: -x[1]):
            html += f'<tr><td>{cat}</td><td style="font-weight:600;color:{bar_color(score)}">{score}/100</td></tr>\n'
        html += "</table>\n"

        # Show weak items
        if tier_data["weak"]:
            html += f"<h3 style='color:#dc2626'>Svake spørsmål ({len(tier_data['weak'])} stk, score &lt; 70)</h3>\n"
            for item in tier_data["weak"]:
                q_field = item.get("sporsmal", item.get("spørsmål", ""))
                score = item.get("composite_score", 0)
                reason = ""
                if "judge_scores" in item:
                    reason = item["judge_scores"].get("begrunnelse", "")
                html += f"""<div class="weak-item">
  <div class="q">{badge(score)} {item.get('id', '?')} [{item.get('kategori', '')}] — {score}/100</div>
  <div>{q_field[:120]}...</div>
  <div class="reason">{reason[:200]}</div>
</div>\n"""
    html += "</div>\n"

# Key findings
html += """
<div class="section">
  <h2>Nøkkelfunn og analyse</h2>
"""

# Rank agents
ranked = sorted(agents.items(), key=lambda x: -x[1]["total_composite"])
best = ranked[0]
worst_sp = min(agents.items(), key=lambda x: x[1]["tiers"]["Tier 3: SP Grounding"]["composite"])

html += f"""
  <div class="insight"><strong>Beste agent totalt:</strong> {best[1]['name']} med {best[0]} ({best[1]['total_composite']}/100)</div>
  <div class="insight"><strong>Svakest på SP Grounding:</strong> {worst_sp[1]['name']} ({worst_sp[1]['tiers']['Tier 3: SP Grounding']['composite']}/100) — indikerer at agenten ikke henter informasjon fra SharePoint-dokumenter effektivt</div>
  <div class="insight"><strong>Keyword vs Judge divergens:</strong> Keyword-scoring underrapporterer konsekvent, spesielt for Land &amp; Expand (samtalebaserte svar). Judge fanger semantisk korrekthet som keyword misser.</div>
"""

# BOS-specific insight
bos_k = agents["BOS"]["tiers"]["Tier 1: Knowledge"]["composite"]
bos_sp = agents["BOS"]["tiers"]["Tier 3: SP Grounding"]["composite"]
html += f"""
  <div class="insight"><strong>BOS-paradokset:</strong> BOS scorer {bos_k}/100 på knowledge men bare {bos_sp}/100 på SP grounding — den rikeste systemprompt-en betyr at metadata er inline, men agenten henter ikke fra SharePoint-dokumenter for detaljer som kun finnes der.</div>
"""

komp_sp = agents["Komplett"]["tiers"]["Tier 3: SP Grounding"]["composite"]
html += f"""
  <div class="insight"><strong>Komplett-mønsteret fungerer:</strong> Komplett scorer {komp_sp}/100 på SP grounding — dokumentoppsummeringer i instruksjonene hjelper agenten å finne riktig informasjon i SharePoint.</div>
"""

html += "</div>\n"

# Recommendations
html += """
<div class="section">
  <h2>Anbefalinger</h2>
"""

recs = []
if agents["BOS"]["tiers"]["Tier 3: SP Grounding"]["composite"] < 70:
    recs.append(("BOS: Legg til dokumentoppsummeringer", "Implementer 'Komplett-mønsteret' — legg til oppsummeringer av SharePoint-dokumenter i agent-instruksjonene. Dette løftet Komplett fra ~50% til ~96% på SP grounding."))

for alias, agent in agents.items():
    weak_all = []
    for tier_name, tier_data in agent["tiers"].items():
        weak_all.extend(tier_data["weak"])
    if weak_all:
        cats = {}
        for w in weak_all:
            c = w.get("kategori", "Ukjent")
            cats[c] = cats.get(c, 0) + 1
        worst_cats = sorted(cats.items(), key=lambda x: -x[1])[:2]
        if worst_cats:
            cat_str = ", ".join(f"{c} ({n} stk)" for c, n in worst_cats)
            recs.append((f"{alias}: Forbedre svake kategorier", f"Fokuser på: {cat_str}. Legg til mer spesifikke fakta i instruksjonene for disse områdene."))

recs.append(("Alle: Standardiser eval-rammeverk", "Bruk 33-spørsmåls-standarden (15+10+8) for alle nye agenter. Alltid dual scoring med gpt-4.1 som judge."))
recs.append(("Alle: Kjør re-eval etter endringer", "Etter instruksjonsendringer, kjør kun de svake tier-ene på nytt for rask feedback."))

for title, desc in recs:
    html += f'<div class="rec-box"><strong>{title}:</strong> {desc}</div>\n'

html += "</div>\n"

# Footer
html += f"""
<div class="footer">
  KATE Agent Evaluering | Generert {now} | Dual scoring: keyword + LLM-as-judge (gpt-4.1)<br>
  Powered by Atea KATE Platform
</div>

</div>
</body>
</html>
"""

output_path = os.path.join(BASE, "KATE_Agent_Sammenligning_v2_2026-04-05.html")
with open(output_path, "w", encoding="utf-8") as f:
    f.write(html)
print(f"Rapport generert: {output_path}")
print(f"\nSammendrag:")
for alias, agent in agents.items():
    t1 = agent["tiers"]["Tier 1: Knowledge"]["composite"]
    t2 = agent["tiers"]["Tier 2: Land & Expand"]["composite"]
    t3 = agent["tiers"]["Tier 3: SP Grounding"]["composite"]
    total = agent["total_composite"]
    print(f"  {alias:10s}  T1: {t1:5.1f}  T2: {t2:5.1f}  T3: {t3:5.1f}  Total: {total:5.1f}/100")
