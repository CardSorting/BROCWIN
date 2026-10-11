"""Produce static poster-session artifacts from retained evidence only.

This is a presentation exporter. It never imports runtime modules, launches a
game, runs a compatibility test, prepares a manifest, or starts native services.
Remote requests are blocked during local document rendering.
"""
from pathlib import Path
import base64
import csv
from datetime import datetime, timezone
import hashlib
import html
import json
import math
import re
import shutil
import sys
import textwrap

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PAPER = ROOT / "theseus/publications/2026-10-11-v1.0.1"
DATA = json.loads((HERE / "session.json").read_text(encoding="utf-8"))
SCENES = DATA["scenes"]
INK = "#122c38"
TEAL = "#087f80"
AMBER = "#a55313"
CREAM = "#f5f3ed"
MUTED = "#50636b"


def write(name, value):
    dest = HERE / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(value if isinstance(value, str) else json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def esc(value):
    return html.escape(str(value), quote=True)


def uri(path):
    suffix = path.suffix.lower()
    mime = {".svg": "image/svg+xml", ".png": "image/png", ".jpg": "image/jpeg"}[suffix]
    return "data:" + mime + ";base64," + base64.b64encode(path.read_bytes()).decode()


def provenance():
    asset_sources = {
        "architecture.svg": PAPER / "figures/architecture.svg",
        "cold-login.png": ROOT / "theseus/reports/performance/heap-control-20261011/run-01/first-visible-scene.png",
        "warm-login.png": ROOT / "theseus/reports/performance/heap-control-20261011/run-02/final-canvas.png",
    }
    paths = list(asset_sources.values()) + [
        PAPER / "03-technical-white-paper.md", PAPER / "03-technical-white-paper.pdf",
        PAPER / "evidence-index.md", PAPER / "evidence-ledger.json",
        PAPER / "publication-facts.json", PAPER / "01-environment-as-executable-artifact.md",
        ROOT / "theseus/wiki/closeout.md", ROOT / "theseus/browser/dependencies.json",
        ROOT / "theseus/browser/provenance.json", ROOT / "theseus/provenance.json",
        ROOT / "theseus/reports/performance/heap-control-20261011/run-01/result.json",
        ROOT / "theseus/reports/performance/heap-control-20261011/run-02/result.json",
        ROOT / "theseus/reports/performance/heap-control-20261011/source-audit-review.json",
        ROOT / "theseus/reports/performance/heap-free-20261011/microbenchmark-summary.json",
        ROOT / "theseus/reports/performance/heap-candidate-20261011/run-01/result.json",
        ROOT / "theseus/reports/performance/heap-candidate-20261011/run-02/result.json",
        ROOT / "theseus/reports/frozen-closeout-20261011/independent-review.json",
    ]
    (HERE / "assets").mkdir(exist_ok=True)
    for name, src in asset_sources.items():
        shutil.copyfile(src, HERE / "assets" / name)
    records = [{"path": p.relative_to(ROOT).as_posix(), "sha256": sha(p), "bytes": p.stat().st_size} for p in paths]
    write("source-ledger.json", {"schema": "heav3ns.brocwin.poster-sources/v1", "primaryVersion": "1.0.1", "knowledgeBaseline": "1.4.1", "records": records, "assets": [{"copy": "assets/" + k, "source": v.relative_to(ROOT).as_posix(), "sha256": sha(v), "unchangedCopy": True} for k, v in asset_sources.items()]})
    facts = json.loads((PAPER / "publication-facts.json").read_text(encoding="utf-8"))
    assert [x["firstVisibleLoginSeconds"] for x in facts["control"]] == [440.703, 438.797]
    assert [x["progress"]["frameAdvances"] for x in facts["control"]] == [1073, 1080]
    assert facts["inputEntries"] == 321 and facts["servedObserverIdentities"] == 211
    assert all(not x["reportedErrors"] for x in facts["control"])
    write("evidence-summary.json", facts)
    micro = json.loads((ROOT / "theseus/reports/performance/heap-free-20261011/microbenchmark-summary.json").read_text(encoding="utf-8"))
    write("allocator-data.json", {"source": "E04 microbenchmark-summary.json", "method": micro["method"], "environment": micro["environment"], "workload": micro["workload"], "rows": micro["rows"], "scope": micro["scope"]})
    return facts, micro


class SVG:
    """Vector poster and plots; use installed font metrics to wrap text."""
    def __init__(self, width, height, background="white"):
        from PIL import ImageFont
        self.font_module = ImageFont
        self.width, self.height = width, height
        self.bits = [f'<rect width="{width}" height="{height}" fill="{background}"/>']
        self.fonts = {}

    def font(self, size, bold=False):
        key = (size, bold)
        if key not in self.fonts:
            self.fonts[key] = self.font_module.truetype("C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf", size)
        return self.fonts[key]

    def rect(self, x, y, w, h, fill, radius=0, stroke=None):
        self.bits.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}"' + (f' stroke="{stroke}" stroke-width="2"' if stroke else "") + "/>" )

    def line(self, x1, y1, x2, y2, color, width=2, dash=None):
        self.bits.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{width}"' + (f' stroke-dasharray="{dash}"' if dash else "") + "/>" )

    def text(self, x, y, content, size=28, color=INK, bold=False, width=None, leading=1.3, anchor="start"):
        lines = []
        for paragraph in str(content).split("\n"):
            if not width:
                lines.append(paragraph)
                continue
            words = paragraph.split()
            current = ""
            for word in words:
                trial = current + (" " if current else "") + word
                if current and self.font(size, bold).getlength(trial) > width:
                    lines.append(current)
                    current = word
                else:
                    current = trial
            lines.append(current)
        for ordinal, line in enumerate(lines):
            self.bits.append(f'<text x="{x}" y="{y + ordinal * size * leading}" font-family="Arial,sans-serif" font-size="{size}" fill="{color}" font-weight="{700 if bold else 400}" text-anchor="{anchor}">{esc(line)}</text>')
        return y + len(lines) * size * leading

    def image(self, x, y, w, h, path):
        self.bits.append(f'<image x="{x}" y="{y}" width="{w}" height="{h}" preserveAspectRatio="xMidYMid meet" href="{uri(path)}"/>')

    def output(self, physical=False):
        dimensions = 'width="48in" height="36in"' if physical else f'width="{self.width}" height="{self.height}"'
        return f'<svg xmlns="http://www.w3.org/2000/svg" {dimensions} viewBox="0 0 {self.width} {self.height}" role="img"><title>BROCWIN research poster</title><desc>Ontology, inherited architecture, retained login controls, allocator results, evidence limits, and independent continuation.</desc>' + "".join(self.bits) + "</svg>"


def panel(svg, x, y, w, h, number, title):
    svg.rect(x, y, w, h, "white", 12)
    svg.text(x + 25, y + 48, number, 24, TEAL, True)
    svg.text(x + 78, y + 49, title, 31, INK, True, width=w - 100)
    svg.line(x + 25, y + 69, x + w - 25, y + 69, "#dce6e5")


def poster(facts, micro):
    p = SVG(2880, 2160, CREAM)
    p.rect(0, 0, 2880, 290, INK)
    p.text(80, 64, "HEAV3NS  /  RESEARCH POSTER SESSION", 29, "#88ded7", True)
    p.text(80, 205, "BROCWIN", 125, "white", True)
    p.text(1070, 108, "Browser-hosted execution of an inherited Windows MMO client", 43, "white", True, width=1680, leading=1.23)
    p.text(1070, 222, "Commissioned by MAJO, Executive Chair  ·  Presented by Dr. GPT", 29, "#c4d7dc")
    p.text(80, 357, "What does it mean for a Windows application to exist outside Windows?", 43, INK, True)
    p.text(80, 400, "Reconstruct sufficient conditions. Retain original compiled logic. Report a bounded result.", 28, MUTED)
    lx, lw, mx, mw, rx, rw = 80, 760, 880, 1120, 2040, 760

    panel(p, lx, 445, lw, 440, "01", "What exists in this experiment")
    y = 554
    for label, detail in [
        ("Application", "Inherited executable, libraries and content."),
        ("BROCWIN", "Selected reconstructed execution conditions."),
        ("Browser", "Host for the interpreter and adapters."),
        ("Native services", "Existing servers and SQL outside the browser."),
        ("Research artifact", "Sources, observations, identities and limits.")]:
        p.text(lx + 28, y, label, 28, TEAL, True)
        p.text(lx + 28, y + 33, detail, 26, INK, width=lw - 55)
        y += 68

    panel(p, lx, 910, lw, 375, "02", "Inheritance and intervention")
    y = p.text(lx + 28, 1018, "HEAV3NS-COMBO integrates inherited client resources, Wine-Assembly and existing native services. The institution did not author the original game.", 28, width=lw - 56)
    y = p.text(lx + 28, y + 20, "Audited disk files were retained. A guarded send wrapper was installed in mapped code padding under the original socket lock.", 28, width=lw - 56)
    p.text(lx + 28, 1255, "White paper §5 · E16–E17", 21, MUTED)

    panel(p, lx, 1310, lw, 340, "03", "Strategy and evolution")
    y = p.text(lx + 28, 1418, "Interpret x86 in Wasm; reconstruct Windows contracts; adapt graphics, input and audio; mount resources; retain native services.", 26, width=lw - 56)
    p.text(lx + 28, y + 12, "Contract repair → cache studies → allocator study. Overall speedup and full acceptance remain unproven.", 26, width=lw - 56)
    p.text(lx + 28, 1622, "White paper §§4, 7–10", 21, MUTED)

    panel(p, lx, 1675, lw, 350, "04", "Questions beyond this client")
    p.text(lx + 28, 1780, "Can reconstructed conditions extend software's life? Can operating-system interfaces become research objects? What else must archives preserve for independent examination?", 28, width=lw - 56)
    p.text(lx + 28, 1940, "These are research opportunities, not universal capabilities demonstrated by this trial.", 26, AMBER, width=lw - 56)

    panel(p, mx, 445, mw, 685, "05", "Architecture and native boundary")
    p.image(mx + 28, 529, mw - 56, 545, HERE / "assets/architecture.svg")
    p.text(mx + 28, 1110, "Figure 1 from paper 1.0.1, unchanged; relationships are not measured costs. E10–E15.", 21, MUTED)

    panel(p, mx, 1155, mw, 400, "06", "Final retained control pair")
    p.text(mx + 28, 1272, "COLD PROFILE", 28, TEAL, True)
    p.text(mx + 585, 1272, "WARM PROFILE", 28, TEAL, True)
    p.text(mx + 28, 1358, "440.703 s", 76, INK, True)
    p.text(mx + 585, 1358, "438.797 s", 76, INK, True)
    p.text(mx + 28, 1404, "1,073 advances / 31.094 s", 29)
    p.text(mx + 585, 1404, "1,080 advances / 31.109 s", 29)
    p.text(mx + 28, 1460, "321 matching input entries · 211 served/observer checks", 30, TEAL, True)
    p.text(mx + 28, 1504, "No reported errors in these observations. One sample per condition.", 25, MUTED)
    p.text(mx + 28, 1534, "Profiles, not whole-machine boots. Timing starts before browser launch. E01–E03, E19.", 21, MUTED)

    panel(p, mx, 1580, mw, 445, "07", "Allocator microbenchmark")
    chart = allocator_plot(micro, width=1058, height=245)
    plot_file = HERE / "assets/allocator-poster.svg"
    plot_file.write_text(chart, encoding="utf-8")
    p.image(mx + 30, 1666, mw - 60, 245, plot_file)
    p.text(mx + 28, 1938, "Deep lists: 5.1–5.5× faster. Empty list: 13.9% slower.", 28, TEAL, True)
    p.text(mx + 28, 1975, "Local workload benefit; no equivalent application acceleration established.", 26, AMBER)
    p.text(mx + 28, 2006, "512-byte pairs · ABBA processes · mean of process medians · White paper §9 / E04", 21, MUTED)

    panel(p, rx, 445, rw, 645, "08", "Archived login evidence")
    p.image(rx + 28, 538, rw - 56, 500, HERE / "assets/cold-login.png")
    p.text(rx + 28, 1071, "Cold first-visible canvas, 1280 × 960; original game imagery. E03.", 21, MUTED)

    panel(p, rx, 1115, rw, 425, "09", "Evidence limits")
    p.text(rx + 28, 1220, "Frame counts are not verified refreshes or complete gameplay. About 31 seconds cannot establish sustained stability.", 28, width=rw - 56)
    p.text(rx + 28, 1342, "Candidate cold observation failed in the screenshot helper; later warm priming was unmatched. Final observer validation is incomplete.", 28, width=rw - 56)
    p.text(rx + 28, 1508, "No full port, 3× gain or long-duration acceptance. §§7.2, 10.", 22, AMBER, True)

    panel(p, rx, 1565, rw, 460, "10", "Independent continuation")
    p.text(rx + 28, 1673, "Restore matching artifacts and observer. Recover original/platform inputs, native services, private configuration and suitable SQL state with lawful access and permissions.", 28, width=rw - 56)
    p.text(rx + 28, 1840, "Then validate the observer, repeat startup studies, test longer durations and broaden the application corpus. Independent restoration remains outstanding.", 27, width=rw - 56)
    p.text(rx + 28, 2003, "Cycle closed. HEAV3NS makes no completion promise. §§8, 11.", 22, TEAL, True)

    p.text(80, 2078, "Source: BROCWIN Technical White Paper 1.0.1 · 11 October 2026 · Knowledge closeout 1.4.1 · Research report; no external peer review claimed.", 24, MUTED)
    p.text(80, 2116, "Credit: original developers · CardSorting/JoySwordOnline · Wine-Assembly contributors · Microsoft · websockets · recorded Codex contributors. Full slate accompanies this poster.", 22, MUTED)
    p.text(80, 2150, "THE WORK NO LONGER DEMANDS AN AUTHOR.", 27, TEAL, True)
    output = p.output(physical=True)
    write("research-poster.svg", output)
    write("research-poster.html", '<!doctype html><html lang="en"><meta charset="utf-8"><title>BROCWIN conference poster</title><style>html,body{margin:0;padding:0;background:#f5f3ed}svg{display:block;width:2880px;height:2160px}@page{size:48in 36in;margin:0}@media print{html,body{width:48in;height:36in}svg{width:48in;height:36in}}</style>' + output + '</html>')
    return output


def allocator_plot(micro, width=1030, height=490):
    p = SVG(width, height)
    left, top, bottom, right = 90, 42, height - 55, width - 35
    plot_h = bottom - top
    max_ratio = 6
    for tick in range(0, 7):
        y = bottom - tick / max_ratio * plot_h
        p.line(left, y, right, y, "#d4dfdf", 1, "6 5" if tick == 1 else None)
        p.text(left - 13, y + 6, f"{tick}×", 21 if height > 300 else 17, MUTED, anchor="end")
    rows = micro["rows"]
    spacing = (right - left) / len(rows)
    for i, row in enumerate(rows):
        ratio = row["controlOverCandidateSpeedRatio"]
        bar_width = spacing * .46
        x = left + spacing * (i + .5) - bar_width / 2
        y = bottom - ratio / max_ratio * plot_h
        p.rect(x, y, bar_width, bottom - y, TEAL if ratio >= 1 else AMBER, 3)
        p.text(x + bar_width / 2, y - 12, f"{ratio:.3f}×", 22 if height > 300 else 18, INK, True, anchor="middle")
        p.text(x + bar_width / 2, bottom + 30, str(row["retainedFreeListDepth"]), 22 if height > 300 else 18, MUTED, anchor="middle")
    p.text(left, height - 5, "Retained free-list depth   |   ratio = control time / candidate time", 20 if height > 300 else 17, MUTED)
    return p.output()


CSS = """
*{box-sizing:border-box}html,body{margin:0;padding:0;width:1920px;height:1080px;overflow:hidden}
body{background:#f5f3ed;color:#122c38;font-family:Arial,sans-serif}
.mast{position:absolute;top:0;left:0;width:1920px;height:90px;background:#122c38;color:#93ded8;padding:29px 70px;font-size:25px;letter-spacing:3px;font-weight:700}
.num{float:right;color:#d0e4e8;letter-spacing:0}h1{position:absolute;margin:0;top:138px;left:70px;width:1770px;font-size:65px;line-height:1.12;font-weight:700;letter-spacing:-1.2px}
.body{position:absolute;top:325px;left:70px;width:1770px;height:490px;display:flex;gap:48px}
.list{flex:1;margin:0;padding:0;list-style:none;min-width:0}.list li{font-size:39px;line-height:1.26;padding:0 0 25px 32px;border-left:6px solid #087f80;margin:0 0 13px 0}.list li:last-child{margin-bottom:0}
.small li{font-size:31px;padding-bottom:19px;line-height:1.25}.source{position:absolute;left:70px;top:873px;width:1770px;color:#50636b;font-size:23px;border-top:2px solid #cad8d7;padding-top:16px}
.safe{position:absolute;left:0;top:950px;width:1920px;height:130px;background:#122c38}.pill{font-size:26px;display:inline-block;color:#087f80;background:#e1efec;padding:14px 18px;border-radius:4px;font-weight:700;margin-bottom:16px}
.figure{width:1060px;flex:none;display:flex;align-items:center;justify-content:center;background:white;padding:15px;border-radius:8px}.figure img{max-width:100%;max-height:100%;object-fit:contain}.note{font-size:29px;line-height:1.32;color:#50636b}.card{background:white;padding:32px;border-radius:8px;flex:1}
.card .label{font-size:30px;color:#087f80;font-weight:700}.metric{font-size:97px;font-weight:700;margin:37px 0 20px;letter-spacing:-2px}.card p{font-size:32px;line-height:1.35;margin:16px 0}.foot{font-size:26px!important;color:#50636b}
.objects{display:flex;gap:20px;width:100%;align-items:stretch}.object{width:20%;background:white;padding:28px 22px;border-top:7px solid #087f80}.object .index{color:#087f80;font-size:27px;margin-bottom:23px}.object h2{font-size:35px;line-height:1.18;margin:0 0 28px}.object p{font-size:28px;line-height:1.3}
.qa .body{top:360px}.qa .list li{font-size:37px}.qa .q{font-size:24px;color:#a55313}.closing .body{gap:45px;top:330px}.closing .list li{font-size:32px}.closing .final{font-size:46px;font-weight:700;color:#087f80;line-height:1.12}
.credits .body{top:295px;height:565px}.creditcol{width:50%;background:white;padding:24px}.creditcol p{margin:0 0 23px;font-size:25px;line-height:1.23}.creditcol strong{color:#087f80}.credits h1{font-size:57px}
.opening h1{font-size:60px;width:1660px}.opening .figure{width:920px}.opening .list li{font-size:38px}.architecture h1,.boundary h1{font-size:55px}.architecture .body,.boundary .body{top:245px;height:590px}.architecture .figure,.boundary .figure{width:1090px}.architecture .list li,.boundary .list li{font-size:32px}
.screenshot .body{top:248px;height:590px}.screenshot .figure{width:920px;background:#000;padding:0}.screenshot .list li{font-size:33px}
.candidate .body{top:306px}.candidate .list li{font-size:33px}.candidate .card p{font-size:30px}.candidate .metric{font-size:51px;letter-spacing:-1px;margin:25px 0;color:#a55313}.candidate .card{padding:27px}
.progress .list li{font-size:39px;padding-bottom:16px}.future .list li,.reproduction .list li{font-size:34px;padding-bottom:18px}
"""


def slide_html(scene, micro):
    k = scene["kind"]
    points = '<ul class="list ' + ('small' if k in ['microbenchmark'] else '') + '">' + ''.join('<li>' + esc(x) + '</li>' for x in scene["points"]) + '</ul>'
    image = None
    if k in ['architecture', 'boundary']:
        image = 'architecture.svg'
    elif k == 'screenshot':
        image = 'cold-login.png'
    elif k == 'microbenchmark':
        image = 'allocator-chart.svg'
    if image:
        content = '<div class="figure"><img alt="' + esc(scene["visual"]) + '" src="../assets/' + image + '"></div>' + points
    elif k in ['opening', 'closing']:
        content = points + '<div class="figure"><img alt="Complete BROCWIN research poster" src="../research-poster.svg"></div>'
    elif k == 'objects':
        details = [x.split(': ', 1) for x in scene['points']]
        content = '<div class="objects">' + ''.join(f'<div class="object"><div class="index">0{i + 1}</div><h2>{esc(a)}</h2><p>{esc(b)}</p></div>' for i, (a, b) in enumerate(details)) + '</div>'
    elif k == 'control':
        content = '<div class="card"><div class="label">COLD · FRESH BROWSER PROFILE</div><div class="metric">440.703 s</div><p>Visible original login</p><p class="foot">One retained sample</p></div><div class="card"><div class="label">WARM · REUSED BROWSER PROFILE</div><div class="metric">438.797 s</div><p>Visible original login</p><p class="foot">Timing begins before browser launch.<br>OS caches were not flushed.</p></div>'
    elif k == 'candidate':
        content = '<div class="card"><div class="label">CANDIDATE COLD</div><div class="metric">297.484 s</div><p>Screenshot-helper stability timeout</p><p>No retained login timestamp</p><p class="foot">Observer failure does not establish an allocator failure.</p></div><div class="card"><div class="label">LATER WARM PROFILE</div><div class="metric">457.859 s</div><p>Login after interrupted priming</p><p class="foot">Not matched to the fully primed control warm run.</p><p class="foot">Final observer revision incompletely validated.</p></div>'
    elif k == 'credits':
        content = '''<div class="creditcol"><p><strong>Primary source</strong><br>BROCWIN Technical White Paper 1.0.1<br>11 October 2026 · Knowledge closeout 1.4.1</p><p><strong>Institution and presentation</strong><br>HEAV3NS · Commission: MAJO, Executive Chair<br>Publication and presenter: Dr. GPT, AI researcher</p><p><strong>Inherited software and resources</strong><br>Original Elsword / fork developers; CardSorting/JoySwordOnline and prior local contributors<br>Original Lua, D3DX and FMOD guest paths</p><p><strong>Recorded production</strong><br>Local Microsoft David and Zira synthesized voices<br>Simulated Q&A · Archival stills · FFmpeg</p></div><div class="creditcol"><p><strong>Wine-Assembly</strong><br>Human and agent contributors, including upstream credit to Claude Code and Codex · MIT dependency<br>Pin d7854bc6…2ce0686 in full source slate</p><p><strong>Platform and transport</strong><br>Microsoft Windows / Direct3D contributors<br>Aymeric Augustin and websockets contributors</p><p><strong>Recorded Codex research roles</strong><br>/root: integration and closeout coordination<br>/root/kernel_audit: reservation implementation<br>/root/evidence_audit: independent review</p><p><strong>Attribution limits</strong><br>No exclusive authorship or endorsement implied.<br>Game/platform rights remain separate.<br>No external peer review claimed.</p></div>'''
    else:
        content = points
    if k == 'closing':
        content = content.replace('<li>THE WORK NO LONGER DEMANDS AN AUTHOR.</li>', '<li class="final">THE WORK NO LONGER<br>DEMANDS AN AUTHOR.</li>')
    title = scene.get('question', scene['title']) if k == 'qa' else scene['title']
    footer = ' · '.join(scene['sources']) + (' · SIMULATED AUDIENCE Q&A' if k == 'qa' else '')
    return f'<!doctype html><html lang="en"><head><meta charset="utf-8"><title>{esc(title)}</title><style>{CSS}</style></head><body class="{k}"><div class="mast">HEAV3NS / BROCWIN <span class="num">{scene["id"]} / 28</span></div><h1>{esc(title)}</h1><div class="body">{content}</div><div class="source">{esc(footer)}</div><div class="safe"></div></body></html>'


def utterances():
    items = []
    number = 0
    for scene in SCENES:
        for speaker in scene['speech']:
            protected = speaker['text'].replace('Dr.', 'Dr¦')
            sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', protected)
            sentences = [x.replace('Dr¦', 'Dr.') for x in sentences]
            for sentence in sentences:
                number += 1
                spoken = sentence
                for before, after in [
                    ('HEAV3NS-COMBO', 'Heavens Combo'), ('HEAV3NS', 'Heavens'), ('BROCWIN', 'Brock win'),
                    ('Dr. GPT', 'Doctor G P T'), ('Wine-Assembly', 'Wine Assembly'), ('CardSorting', 'Card Sorting'),
                    ('JoySwordOnline', 'Joy Sword Online'), ('x86', 'x eighty-six'), ('PE ', 'P E '),
                    ('API', 'A P I'), ('FMOD', 'F mod'), ('WebAudio', 'Web Audio'), ('WebSocket', 'Web Socket'),
                    ('SQL', 'S Q L'), ('MMO', 'M M O')]:
                    spoken = spoken.replace(before, after)
                items.append({'id': f'{number:03d}', 'scene': scene['id'], 'role': speaker['role'], 'captionText': sentence, 'spokenText': spoken, 'wav': f'audio/utterance-{number:03d}.wav'})
    write('utterances.json', items)
    return items


def source_slate():
    write('source-and-attribution-slate.md', '''# BROCWIN Sources and Research Attribution

The presentation reports a completed, bounded experimental cycle. It is based on the repository-grounded technical report below; no external peer review, journal acceptance, endorsement, complete port or new experiment is claimed.

## Primary source and institution

BROCWIN: Browser-Hosted Execution of a Legacy Windows MMO Client Through a Synthetic Compatibility Runtime. Publication III, version 1.0.1, 11 October 2026. Commissioned by MAJO, Executive Chair, HEAV3NS; prepared by Dr. GPT, the commissioned AI researcher. “Dr. GPT” is the commission's AI presenter designation. The engineering baseline is corrected knowledge closeout 1.4.1.

The exact white paper, shared index and fact ledger are copied into [sources](sources). Their source hashes and paths are in [source-ledger.json](source-ledger.json). The original figure and two screenshots are unchanged copies in [assets](assets); presentation layout and plots are newly typeset from retained data.

## Inherited software and dependencies

| Contributor or object | Documented role and attribution limit |
| --- | --- |
| Original Elsword / fork developers | Compiled client/server implementation and original game content. Individual authorship cannot be established from supplied binaries. Original game artwork, interface and logos remain credited to their original developers and respective rights holders. |
| CardSorting/JoySwordOnline and prior local contributors | Inherited installation, scripts, archive recovery and native checkpoint. Source identity: `4c39249b939d79c229e1fd4f63dfd462a90f9060`. Attribution follows the retained provenance; it is not a new upstream audit. |
| Wine-Assembly human and agent contributors | Existing x86/Wasm interpreter and compatibility foundation. MIT dependency pin: `d7854bc6c6bd0319ca33b5f31a465602e2ce0686`. Upstream attribution includes human contributors, Claude Code and Codex. Local patches and generated artifacts require separate custody. Wine-Assembly is not asserted to be the Wine project. |
| Original Lua, D3DX and FMOD paths | Original guest libraries/code remain part of the documented execution path. No institution authorship or independent component conformance is asserted. |
| Microsoft Windows / Direct3D contributors | Platform interfaces and the locally derived compiled shader-validator algorithm executed as guest x86. The installed DLL and derived component are separate protected inputs, not institution-authored code. |
| Aymeric Augustin and websockets contributors | Local WebSocket protocol implementation, recorded version 17.1, BSD-3-Clause dependency. |

## Experimentation and review

Codex /root is credited in retained provenance for local inspection, browser integration, manifests, resource serving, compatibility corrections, captures, validation and documentation. The corrected closeout separately records Codex /root/kernel_audit as reservation-correction implementer, /root/evidence_audit as independent reviewer, and /root as closeout coordinator. An independent review within this agent workflow is not external peer review or independent institutional replication.

MAJO supplies commissioning and institutional framing. Dr. GPT prepares and presents the publications. These labels make no exclusive engineering-authorship claim and do not identify every historical contributor or image reviewer. Attribution survives transfer of custody.

## Visual and audio provenance

- Architecture: Figure 1, white paper 1.0.1, unchanged vector; a repository-derived architectural account, not an execution trace.
- Cold login image: `theseus/reports/performance/heap-control-20261011/run-01/first-visible-scene.png`.
- Warm login image: `theseus/reports/performance/heap-control-20261011/run-02/final-canvas.png`.
- The images are archival stills. No game footage, avatar, live demonstration, new outcome or conference recording is fabricated.
- Graph: derived from retained `microbenchmark-summary.json`; ratios are control elapsed time divided by candidate elapsed time. The graph begins at zero and includes the 1× baseline and the empty-list cost.
- Presenter narration: local Microsoft David Desktop synthesized voice. Simulated audience: local Microsoft Zira Desktop synthesized voice. This does not imply Microsoft or any contributor endorses the research.
- Production: locally installed Python, Pillow font metrics, Playwright/Edge static document rendering, Windows SAPI, and FFmpeg. No game runtime, backend service or compatibility experiment is started.

## Scope and access

The copy of the technical report retains its bibliography as originally published; external literature provides context, not BROCWIN results. The presentation adds no unseen citation or priority claim. The commissioned downstream framing is interpretive and identified as such in the claim matrix.

This local production package is not a public release or a license grant. A group planning external distribution must establish rights for original game imagery and other protected material. No credentials, private SQL state, game/platform binaries or full executable restoration bundle are included. The project and dependency links below identify provenance; the referenced contents were not newly re-audited for this recording.

- [CardSorting/JoySwordOnline](https://github.com/CardSorting/JoySwordOnline/tree/4c39249b939d79c229e1fd4f63dfd462a90f9060)
- [Pinned Wine-Assembly dependency](https://github.com/vgrichina/wine-assembly/tree/d7854bc6c6bd0319ca33b5f31a465602e2ce0686)

The originating institution completed its cycle. Another group may continue with suitable access, permissions, matching artifacts and a separately authorized experiment. HEAV3NS makes no promise to complete future studies.
''')


def documents():
    timing = json.loads((HERE / 'timeline.json').read_text(encoding='utf-8')) if (HERE / 'timeline.json').exists() else None
    timings = {x['scene']: x for x in timing['scenes']} if timing else {}
    script = ['# BROCWIN Presenter Script', '', 'Dr. GPT presents a completed research cycle beside the conference poster. The formal presentation is followed by a simulated audience Q&A, source slate and closing statement. Spoken text is reproduced in the transcript; direction and citations here are production annotations.', '', 'Delivery: calm, explanatory and candid. Read technical terms at conversational pace. Point to poster panels and identify archived evidence as still images. The narration starts with the commissioned ontological question.', '']
    transcript = ['# BROCWIN Recorded Transcript', '', 'Presenter: Dr. GPT. Audience questions are simulated. Voices are synthesized locally. Primary source: BROCWIN Technical White Paper 1.0.1, 11 October 2026. Technical baseline: corrected closeout 1.4.1.', '']
    qa = ['# BROCWIN Audience Q&A', '', 'This simulated sequence follows the formal presentation. Questions use an audience voice; answers use Dr. GPT’s presenter voice. Answers retain the white paper’s evidence limits.', '']
    storyboard = ['# BROCWIN Timed Storyboard', '', 'Target range: 12–15 minutes, interpreting the commission’s “1215 minutes” as a missing range separator. The rendered edition targets 14:45, including Q&A and attribution. Timecodes below follow the synthesized narration waveform; the sequence contains archival stills and static explanatory visuals, with no new runtime footage.', '', '| Segment | Timecode | Visual and action | Spoken segment | Source |', '| --- | --- | --- | --- | --- |']
    csv_rows = []
    plain_transcript = []
    for s in SCENES:
        t = timings.get(s['id'])
        span = timecode(t['start']) + '–' + timecode(t['end']) if t else 'Timing pending audio synthesis'
        title = s.get('question', s['title']) if s['kind'] == 'qa' else s['title']
        script += ['## ' + s['id'] + ' ' + s['title'], '', '**Time:** ' + span + '  ', '**Visual:** ' + s['visual'] + '  ', '**Source:** ' + '; '.join(s['sources']), '']
        transcript += ['## ' + span + ' ' + s['title'], '']
        for speech in s['speech']:
            script += ['**' + speech['role'] + ':** ' + speech['text'], '']
            transcript += ['**' + speech['role'] + ':** ' + speech['text'], '']
            plain_transcript += [speech['role'] + ': ' + speech['text'], '']
        if s['kind'] == 'qa':
            qa += ['## ' + title, '', '**Time:** ' + span, '']
            for speech in s['speech']:
                qa += ['**' + speech['role'] + ':** ' + speech['text'], '']
            qa += ['Source: ' + '; '.join(s['sources']) + '.', '']
        summary = s['speech'][0]['text'].split('. ')[0]
        storyboard.append('| ' + s['id'] + ' ' + s['title'] + ' | ' + span + ' | ' + s['visual'] + ' | ' + summary + '… Full exact narration in presenter script. | ' + '; '.join(s['sources']) + ' |')
        csv_rows.append([s['id'], t['start'] if t else '', t['end'] if t else '', s['title'], 'slides/scene-' + s['id'] + '.png', s['visual'], '\n'.join(x['role'] + ': ' + x['text'] for x in s['speech']), '; '.join(s['sources'])])
    storyboard += ['', 'Captions use the actual utterance audio boundaries, divided into short readable groups within each utterance. Internal cue boundaries are proportional estimates by character count; utterance boundaries and scene timecodes are measured from the synthesized WAV files. The rendered video burns the captions into the lower safe area.', '', 'At opening and closing, hold the full poster before the next cut. At evidence slides, preserve the original image aspect ratio and exact recorded units. At the Q&A, change only the voice and question card; do not imply a live audience was recorded.', '']
    write('presenter-script.md', '\n'.join(script))
    write('transcript.md', '\n'.join(transcript))
    write('transcript.txt', '\n'.join(plain_transcript))
    write('audience-qa.md', '\n'.join(qa))
    write('storyboard.md', '\n'.join(storyboard))
    with (HERE / 'storyboard.csv').open('w', encoding='utf-8-sig', newline='') as out:
        writer = csv.writer(out)
        writer.writerow(['segment', 'start_seconds', 'end_seconds', 'title', 'visual_file', 'visual_direction', 'exact_spoken_text', 'sources'])
        writer.writerows(csv_rows)
    glossary = ['# BROCWIN Technical Glossary', '', 'Plain-language definitions for the poster session. These explain the documented architecture; they do not expand its compatibility claims.', '', '| Term | Meaning |', '| --- | --- |']
    glossary += ['| ' + x + ' | ' + y + ' |' for x, y in DATA['glossary']]
    write('glossary.md', '\n'.join(glossary) + '\n')
    matrix = ['# BROCWIN Claim and Source Matrix', '', 'Each presentation segment is grounded in the technical white paper or explicitly identified institutional interpretation. E-identifiers resolve through the supplied original evidence index.', '', '| Segment | Claim class | Evidence and qualification |', '| --- | --- | --- |']
    for s in SCENES:
        cls = 'Interpretive / proposed research' if s['kind'] in ['implications', 'future', 'closing'] else 'Synthesized explanation of retained evidence'
        if s['kind'] in ['control', 'progress', 'screenshot']:
            cls = 'Observed, within retained condition'
        if s['kind'] in ['allocator', 'microbenchmark']:
            cls = 'Contract / microbenchmark tested; no application speedup'
        matrix.append('| ' + s['id'] + ' ' + s['title'] + ' | ' + cls + ' | ' + '; '.join(s['sources']) + ' |')
    matrix += ['', 'The commission’s malformed “5.15.5” is resolved from white paper §9 as **5.1–5.5×**, not 5.15.5 or 5.15×. Cold/warm are browser-profile conditions. Reported-error absence belongs only to the retained observer channels. The closing custodianship thesis is institutional framing and does not remove contributor credit or establish legal rights.', '']
    write('claim-source-matrix.md', '\n'.join(matrix))


def timecode(seconds):
    value = int(round(seconds))
    return f'{value // 60:02d}:{value % 60:02d}'


def reading_html():
    sys.path.insert(0, str(ROOT / 'theseus/tools/python'))
    import markdown
    pieces = []
    for name in ['presenter-script', 'storyboard', 'glossary', 'audience-qa', 'transcript', 'source-and-attribution-slate', 'claim-source-matrix']:
        body = markdown.markdown((HERE / (name + '.md')).read_text(encoding='utf-8'), extensions=['tables'])
        pieces.append('<section class="doc" id="' + name + '">' + body + '</section>')
    css = '''body{font:17px/1.55 Arial,sans-serif;color:#122c38;background:#f5f3ed;margin:0}header{background:#122c38;color:white;padding:35px max(30px,calc((100vw - 1100px)/2));}main{max-width:1100px;margin:auto;padding:25px}nav a{display:inline-block;color:#93ded8;margin:0 22px 12px 0}a{color:#087f80}video{width:100%;background:#122c38}.poster{width:100%;background:white}.doc{background:white;padding:38px;margin:35px 0;overflow-wrap:anywhere}h1{font-size:30px}h2{font-size:22px;border-top:1px solid #dde5e4;padding-top:22px}table{border-collapse:collapse;width:100%;font-size:14px}td,th{border:1px solid #d2dddc;text-align:left;vertical-align:top;padding:9px}th{background:#e1efec}@page{size:A4;margin:17mm}@media print{body{background:white;font-size:11px;line-height:1.4}header,.watch{display:none}main{padding:0;max-width:none}.doc{padding:0;margin:0;page-break-before:always}h1{font-size:20px}h2{font-size:15px}table{font-size:9px}.poster{display:none}}'''
    write('production-book.html', '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>BROCWIN production book</title><style>' + css + '</style></head><body><header><h1>BROCWIN Poster Session Production Book</h1><p>Completed experimental cycle · White paper 1.0.1 · Presented by Dr. GPT</p><nav>' + ''.join('<a href="#' + n + '">' + label + '</a>' for n, label in [('presenter-script', 'Script'), ('storyboard', 'Storyboard'), ('glossary', 'Glossary'), ('audience-qa', 'Q&A'), ('transcript', 'Transcript'), ('source-and-attribution-slate', 'Sources')]) + '</nav></header><main><div class="watch"><video controls preload="metadata" aria-label="BROCWIN narrated poster session"><source src="brocwin-poster-session.mp4" type="video/mp4"></video><p>The video has open captions. <a href="captions.srt">SRT captions</a> · <a href="captions.vtt">WebVTT captions</a> · <a href="research-poster.pdf">48 × 36 inch poster PDF</a></p></div><img class="poster" src="research-poster.svg" alt="BROCWIN research poster including architecture, login controls and evidence limits">' + ''.join(pieces) + '</main></body></html>')


def render_static():
    sys.path.insert(0, str(ROOT / 'theseus/tools/python'))
    from playwright.sync_api import sync_playwright
    render_log = []
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='msedge', headless=True)
        try:
            context = browser.new_context(viewport={'width': 1920, 'height': 1080}, device_scale_factor=1)
            context.route('**/*', lambda route: route.continue_() if route.request.url.startswith(('file:', 'data:', 'about:')) else route.abort())
            page = context.new_page()
            for s in SCENES:
                page.goto((HERE / 'slides' / ('scene-' + s['id'] + '.html')).as_uri(), wait_until='load')
                page.evaluate('document.fonts.ready')
                errors = page.evaluate('''() => {
                    const issues=[];
                    for(const el of document.querySelectorAll('h1,.body,.list,.card,.object,.creditcol,.source')){
                        const b=el.getBoundingClientRect();
                        if(b.right>1921||b.bottom>951||el.scrollHeight>el.clientHeight+3) issues.push({tag:el.className||el.tagName,bottom:b.bottom,scrollHeight:el.scrollHeight,clientHeight:el.clientHeight});
                    }
                    if(!Array.from(document.images).every(i=>i.complete&&i.naturalWidth>0))issues.push({images:'incomplete'});
                    return issues;
                }''')
                page.screenshot(path=str(HERE / 'slides' / ('scene-' + s['id'] + '.png')))
                render_log.append({'scene': s['id'], 'layoutIssues': errors})
                print('Rendered static presentation scene ' + s['id'], flush=True)
            context.close()
            pc = browser.new_context(viewport={'width': 2880, 'height': 2160}, device_scale_factor=2)
            pc.route('**/*', lambda route: route.continue_() if route.request.url.startswith(('file:', 'data:', 'about:')) else route.abort())
            pp = pc.new_page()
            pp.goto((HERE / 'research-poster.html').as_uri(), wait_until='load')
            pp.evaluate('document.fonts.ready')
            pp.screenshot(path=str(HERE / 'research-poster.png'))
            pp.pdf(path=str(HERE / 'research-poster.pdf'), width='48in', height='36in', print_background=True, prefer_css_page_size=True)
            pc.close()
            book = browser.new_page()
            book.route('**/*', lambda route: route.continue_() if route.request.url.startswith(('file:', 'data:', 'about:')) else route.abort())
            book.goto((HERE / 'production-book.html').as_uri(), wait_until='load')
            book.evaluate('document.fonts.ready')
            book.pdf(path=str(HERE / 'production-book.pdf'), format='A4', print_background=True, prefer_css_page_size=True)
            book.close()
            write('static-render-record.json', {'browser': browser.version, 'method': 'Static local documents only; network requests blocked.', 'runtimeOrServiceLaunch': False, 'newRuntimeCapture': False, 'scenes': render_log})
        finally:
            browser.close()
    issues = [(x['scene'], x['layoutIssues']) for x in render_log if x['layoutIssues']]
    if issues:
        print('Layout issues require review: ' + json.dumps(issues), flush=True)


def copy_sources():
    dest = HERE / 'sources'
    dest.mkdir(exist_ok=True)
    for name in ['03-technical-white-paper.md', '03-technical-white-paper.pdf', 'evidence-index.md', 'evidence-ledger.json', 'publication-facts.json']:
        shutil.copyfile(PAPER / name, dest / name)
    for name, original in [('closeout-1.4.1.md', ROOT / 'theseus/wiki/closeout.md')]:
        shutil.copyfile(original, dest / name)


def readme():
    write('README.md', '''# BROCWIN Research Poster Session

This package presents the completed BROCWIN experimental cycle for an audience encountering the project for the first time. The main result is original-client execution to login under retained browser-hosted conditions, with short frame progression and scoped input identity. It does not establish a complete port, whole-application acceleration or sustained reliability.

Commission: MAJO, Executive Chair, HEAV3NS. Presenter: Dr. GPT. Primary source: BROCWIN Technical White Paper 1.0.1, 11 October 2026. Technical baseline: corrected closeout 1.4.1.

## Deliverables

| Artifact | Use |
| --- | --- |
| [Finished narrated video](brocwin-poster-session.mp4) | 1920 × 1080 poster walkthrough with local synthesized voices, simulated Q&A, 28 chapter markers and burned captions. |
| [Complete delivery ZIP](brocwin-poster-session-package-1.0.0.zip) · [Checksum receipt](archive-record.json) | Video, mixed narration master, editable sources, poster, documents, captions, evidence and hash inventory. |
| [Production book](production-book.html) · [PDF](production-book.pdf) | Local player and complete script, storyboard, glossary, Q&A, transcript, attribution and source mapping. |
| [Conference poster PDF](research-poster.pdf) · [SVG](research-poster.svg) · [PNG](research-poster.png) | 48 × 36 inch landscape poster; vector PDF/SVG and 5760 × 4320 raster copy. |
| [Presenter script](presenter-script.md) | Exact spoken text and production direction in Dr. GPT's commissioned role. |
| [Timed storyboard](storyboard.md) · [CSV](storyboard.csv) · [Timeline](timeline.json) | Every visual and spoken segment, with waveform-derived scene timecodes. |
| [Glossary](glossary.md) · [Audience Q&A](audience-qa.md) | Plain-language terms and eight evidence-bounded answers. |
| [Captions SRT](captions.srt) · [WebVTT](captions.vtt) | Reusable caption files matching the rendered narration. |
| [Transcript](transcript.md) · [Text](transcript.txt) | Complete spoken presentation including simulated questions and credits. |
| [Source and attribution slate](source-and-attribution-slate.md) | Institution, original software, dependencies, documented research roles, and production attribution. |
| [Claim matrix](claim-source-matrix.md) · [Source hashes](source-ledger.json) | Traceability and explicit observed/interpretive boundaries. |
| [Verification record](verification-record.json) | Container, duration, captions, assets and frozen/publication integrity results. |

The commission's “1215 minutes” is interpreted as **12–15 minutes**. This edition targets **14:45**. Its “5.15.5” allocator range is resolved from the paper as **5.1–5.5×**. These interpretations are recorded rather than silently changing the measured claims.

The video is a narrated poster session, not footage of a physical conference or an avatar performance. The first spoken line is the commissioned ontological question. Original stills retain their aspect ratios and are labeled archival evidence. No experiment is reopened, no game is launched, and no native service is changed.

## Reproduction of the presentation

Run from the repository root using the installed Python environment with Pillow and the repository's existing local Markdown and Playwright packages. Static rendering uses the installed Edge channel. The speech script uses installed Microsoft David and Zira Desktop voices. FFmpeg and FFprobe must be available on PATH.

```powershell
python theseus/presentations/2026-10-11-poster-session-v1.0.0/build_package.py
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ./theseus/presentations/2026-10-11-poster-session-v1.0.0/synthesize.ps1
python theseus/presentations/2026-10-11-poster-session-v1.0.0/render_video.py
python theseus/presentations/2026-10-11-poster-session-v1.0.0/build_package.py --finalize
python theseus/presentations/2026-10-11-poster-session-v1.0.0/verify_package.py
python theseus/presentations/2026-10-11-poster-session-v1.0.0/seal_package.py
```

These are presentation-export commands, not compatibility-runtime build or recovery instructions. Preserve an already delivered edition before changing its materials. No cloud voice service, upload, publishing or public deployment is used.

Utterance timings come from synthesized WAV files. Cue subdivisions within a sentence are character-proportional estimates, documented in the storyboard. Silence between scenes and end holds is included in the actual video duration. The voice is uniformly time-adjusted to fit the duration target; the production record records that factor.

The ZIP includes the mixed narration master and production sources. Regenerable utterance clips, the raw mix and temporary rendering checks remain outside the ZIP. The manifest and external receipt are unsigned local integrity records.

## Evidence and access

The exact primary paper and source index are included in `sources`. Their original relative links require the retained repository structure; consult the printed source paths, source ledger and full original archive for recovery. This is a presentation bundle, not a complete runtime restoration kit. It excludes credentials, private database state, game/platform binaries and most large raw reports. Unchanged screenshot copies and derived charts are in `assets`.

The package is a local commission deliverable. Original game imagery and platform material carry separate rights; no redistribution permission is implied by the compatibility-source license. Contributor credit remains with inherited and newly developed work. HEAV3NS's experimental cycle is closed; future researchers need suitable access, matching artifacts, permissions and a separately authorized workspace.

THE WORK NO LONGER DEMANDS AN AUTHOR.
''')


def main():
    if '--finalize' in sys.argv:
        documents()
        reading_html()
        render_book_only()
        return
    facts, micro = provenance()
    copy_sources()
    poster(facts, micro)
    write('assets/allocator-chart.svg', allocator_plot(micro))
    for s in SCENES:
        write('slides/scene-' + s['id'] + '.html', slide_html(s, micro))
    utterances()
    source_slate()
    documents()
    readme()
    reading_html()
    render_static()


def render_book_only():
    sys.path.insert(0, str(ROOT / 'theseus/tools/python'))
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='msedge', headless=True)
        try:
            page = browser.new_page()
            page.route('**/*', lambda route: route.continue_() if route.request.url.startswith(('file:', 'data:', 'about:')) else route.abort())
            page.goto((HERE / 'production-book.html').as_uri(), wait_until='load')
            page.evaluate('document.fonts.ready')
            page.pdf(path=str(HERE / 'production-book.pdf'), format='A4', print_background=True, prefer_css_page_size=True)
        finally:
            browser.close()


if __name__ == '__main__':
    main()
