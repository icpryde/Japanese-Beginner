#!/usr/bin/env python3
"""
gen_answer_pages.py — rebuild the three quiz "Answers" lesson pages from
content/quizzes/*.json as clean, styled answer keys (the imported originals
were unformatted dumps). Run before build_site.py.
"""
import json, re
from pathlib import Path
from html import escape

import build_site as bs

REPO = Path(__file__).parent
LESSONS = REPO / "content" / "lessons"

PAGES = [
    {"key": "week_03", "lesson_id": "Week 3 - Review quiz Answers",
     "heading": "Week 3 Test — Answer Key", "test_href": "../weeks/week3-test.html"},
    {"key": "week_08", "lesson_id": "Week 8 Review Quiz Answers",
     "heading": "Week 8 Test — Answer Key", "test_href": "../weeks/week8-test.html"},
    {"key": "week_09-12", "lesson_id": "Week 9-12 Quiz Review Answers",
     "heading": "Week 9–12 Test — Answer Key", "test_href": "../weeks/week9-12-test.html"},
]

CSS = """
<style>
.akey-item{background:var(--card-bg,rgba(128,128,128,.06));border:1px solid var(--border,rgba(128,128,128,.18));
  border-radius:10px;padding:14px 16px;margin:12px 0;}
.akey-head{display:flex;align-items:center;gap:10px;margin-bottom:8px;}
.akey-num{font-weight:700;color:var(--accent,#e63946);}
.akey-prompt{margin:6px 0 10px;}
.akey-prompt audio{display:block;margin:8px 0;max-width:420px;height:36px;}
.akey-prompt img{max-width:100%;height:auto;border-radius:8px;display:block;margin:8px 0;}
.akey-prompt ruby rt{font-size:.55em;}
.akey-answer{border-left:3px solid #2f9e63;background:rgba(47,158,99,.10);
  border-radius:0 8px 8px 0;padding:8px 12px;}
.akey-answer .akey-label{font-size:.72rem;font-weight:700;letter-spacing:.5px;color:#2f9e63;
  text-transform:uppercase;display:block;margin-bottom:4px;}
.akey-answer audio{display:block;margin:6px 0;max-width:380px;height:34px;}
.akey-answer .akey-choice{margin:2px 0;font-weight:600;}
</style>
"""


def answer_block(choice_html_localized, idx):
    soup = bs.BeautifulSoup(choice_html_localized, "html.parser")
    audio = soup.find("audio")
    text = " ".join(soup.get_text(" ", strip=True).split())
    if audio is not None:
        looks_file = bool(re.search(r"\.(wav|mp3|m4a)", text, re.I))
        label = text if (text and not looks_file and len(text) < 80) else f"Clip {idx}"
        return f'<div class="akey-choice">{escape(label)}</div>{str(audio)}'
    return f'<div class="akey-choice">{escape(text)}</div>'


def build_page(spec):
    data = json.loads((REPO / "content" / "quizzes" / f"{spec['key']}.json").read_text(encoding="utf-8"))
    questions = sorted(data.get("questions", []), key=lambda q: q.get("position", 0))
    by_q = {}
    for c in data.get("choices", []):
        by_q.setdefault(c["question_id"], []).append(c)

    parts = ['<div class="fr-view">', CSS, f"<h3>{escape(spec['heading'])}</h3>",
             "<p>Every question with its correct answer. Listening clips are playable inline.</p>"]
    if spec["test_href"]:
        parts.append(
            f'<a href="{spec["test_href"]}" class="test-link-card">'
            '<span class="test-link-icon">📝</span><div class="test-link-info">'
            '<h3>Take this test interactively</h3><p>Scored, one question at a time, with instant feedback</p>'
            '</div><span class="test-link-arrow">→</span></a>')

    for i, q in enumerate(questions, 1):
        prompt = bs._localize_quiz_fragment(q.get("prompt") or "", spec["key"])
        chs = sorted(by_q.get(q["id"], []), key=lambda c: c.get("position", 0))
        correct = []
        for j, c in enumerate(chs, 1):
            if bs._decode_quiz_credited(c.get("credited")):
                correct.append(answer_block(
                    bs._localize_quiz_fragment(c.get("text") or "", spec["key"]), j))
        parts.append(
            f'<div class="akey-item"><div class="akey-head"><span class="akey-num">Q{i}</span></div>'
            f'<div class="akey-prompt">{prompt}</div>'
            f'<div class="akey-answer"><span class="akey-label">Correct answer{"s" if len(correct) > 1 else ""}</span>'
            f'{"".join(correct)}</div></div>')
    parts.append("</div>")
    return "".join(parts)


def main():
    for spec in PAGES:
        p = LESSONS / f"{spec['lesson_id']}.json"
        if not p.exists():
            print(f"skip {spec['lesson_id']}: lesson JSON not found")
            continue
        lesson = json.loads(p.read_text(encoding="utf-8"))
        lesson["html"] = build_page(spec)
        p.write_text(json.dumps(lesson, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"rebuilt: {spec['lesson_id']}")


if __name__ == "__main__":
    main()
