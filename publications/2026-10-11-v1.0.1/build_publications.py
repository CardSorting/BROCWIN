"""Typeset and inventory this publication edition without opening the game.

Uses the already installed Markdown and local Playwright packages. Browser
navigation is restricted to static publication files; remote requests abort.
No runtime source, manifest, backend, capture or optimization is touched.
"""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import sys
import zipfile
import re
import html

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def save(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
def load(path):
    return json.loads(path.read_text(encoding='utf-8'))

GROUPS = [
('E01','Final control raw measurements',[
'theseus/reports/performance/heap-control-20261011/run-01/result.json',
'theseus/reports/performance/heap-control-20261011/run-02/result.json']),
('E02','Final control integrity and review',[
'theseus/reports/performance/heap-control-20261011/source-audit-review.json',
'theseus/reports/performance/heap-control-20261011/identity.json']),
('E03','Four retained control image files',[
'theseus/reports/performance/heap-control-20261011/run-01/first-visible-scene.png',
'theseus/reports/performance/heap-control-20261011/run-01/final-canvas.png',
'theseus/reports/performance/heap-control-20261011/run-02/first-visible-scene.png',
'theseus/reports/performance/heap-control-20261011/run-02/final-canvas.png']),
('E04','Allocator profile, contracts, microbenchmarks and candidate limits',[
'theseus/reports/performance/kernel-profile-control-20261011/source-audit-review.json',
'theseus/reports/performance/kernel-profile-control-20261011/profile-summary.json',
'theseus/reports/performance/heap-free-20261011/final-source-validation.json',
'theseus/reports/performance/heap-free-20261011/compiled-validation.json',
'theseus/reports/performance/heap-free-20261011/microbenchmark-summary.json',
'theseus/reports/performance/heap-candidate-20261011/source-audit-review.json',
'theseus/reports/performance/heap-candidate-20261011/run-01/result.json',
'theseus/reports/performance/heap-candidate-20261011/run-02/result.json',
'theseus/wiki/changes/0014-heap-free-ownership.md']),
('E05','Corrected closeout and observer limits',[
'theseus/wiki/closeout.md',
'theseus/reports/frozen-closeout-20261011/independent-review.json',
'theseus/reports/frozen-closeout-20261011/validation-1.4.1.json']),
('E06','Frozen source inventory and retained differences',[
'theseus/reports/frozen-closeout-20261011/frozen-state.json',
'theseus/wiki/frozen-sources/benchmark_startup.py',
'theseus/wiki/frozen-sources/test_benchmark_observation.py',
'theseus/wiki/frozen-sources/10-helpers.wat',
'theseus/wiki/frozen-sources/test-heap-reservation-rollback.js']),
('E07','Source-only reservation rollback',[
'theseus/reports/performance/heap-reservation-20261011/control.json',
'theseus/reports/performance/heap-reservation-20261011/candidate-source.json',
'theseus/reports/performance/heap-reservation-20261011/source-suites.json',
'theseus/wiki/changes/0015-heap-reservation-rollback.md']),
('E08','Historical final gameplay route and revival failure',[
'theseus/reports/browser/20261011T145806Z/review.json',
'theseus/reports/browser/20261011T145806Z/revival-failure.json',
'theseus/wiki/acceptance-session.md']),
('E09','Acceptance and open contracts',[
'theseus/wiki/compatibility.md','theseus/wiki/issues.md']),
('E10','Execution/loading implementation and account',[
'theseus/wiki/execution.md','theseus/wiki/loading.md',
'theseus/tools/wine-assembly/src/main.watx',
'theseus/tools/wine-assembly/src/07-decoder.wat',
'theseus/tools/wine-assembly/src/04-cache.wat',
'theseus/tools/wine-assembly/lib/pe.js',
'theseus/tools/wine-assembly/lib/dll-loader.js',
'theseus/tools/wine-assembly/host.js','theseus/browser/main.js']),
('E11','Graphics and input/audio account',[
'theseus/wiki/graphics.md','theseus/wiki/audio-input.md']),
('E12','Local native network boundary',[
'theseus/wiki/network.md','theseus/browser/local_server_wire.js',
'theseus/browser/network.py','theseus/compose.yml']),
('E13','Resource and persistence account',[
'theseus/wiki/storage.md','theseus/browser/serve.py']),
('E14','Memory contracts',[
'theseus/wiki/threads-memory.md',
'theseus/tools/wine-assembly/src/10-helpers.wat',
'theseus/tools/wine-assembly/src/09a-handlers2-runtime.wat']),
('E15','Earlier cache measurements and variation',[
'theseus/wiki/performance.md',
'theseus/wiki/changes/0013-runtime-startup-cache.md',
'theseus/reports/performance/validation-20261011/summary.json',
'theseus/reports/performance/baseline-visible-20261011/run-01/result.json',
'theseus/reports/performance/baseline-visible-20261011/run-02/result.json',
'theseus/reports/performance/candidate-20261011/run-01/result.json',
'theseus/reports/performance/candidate-20261011/run-02/result.json',
'theseus/reports/performance/control-repeat-20261011/run-01/result.json',
'theseus/reports/performance/control-repeat-20261011/run-02/result.json']),
('E16','Dependency/provenance and supplied installation',[
'theseus/provenance.json','theseus/browser/provenance.json',
'theseus/browser/dependencies.json','theseus/wiki/provenance.md']),
('E17','Mapped guest send intervention',[
'theseus/wiki/changes/0012-session-send-serialization.md',
'theseus/reports/serial-ownership-20261011T142300Z/candidate-integration-validation.json']),
('E18','Recovery and prepared identity/custody',[
'theseus/wiki/build-recovery.md','theseus/wiki/generated/identity.json',
'theseus/wiki/releases/1.4.1.json',
'theseus/checkpoints/brocwin-knowledge-1.4.1.zip',
'theseus/browser/generated/manifest.json',
'theseus/browser/patches/wine-assembly.patch']),
('E19','Actual retained observer implementation and sampling',[
'theseus/reports/performance/heap-control-20261011/observer/benchmark_startup.py',
'theseus/reports/performance/heap-control-20261011/observer/startup_telemetry.js',
'theseus/reports/performance/heap-control-20261011/run-01/samples.jsonl',
'theseus/reports/performance/heap-control-20261011/run-02/samples.jsonl'])]

def prepare_evidence():
    groups=[]
    for eid, title, names in GROUPS:
        records=[]
        for name in names:
            p=ROOT/name
            records.append({'path':name,'sha256':digest(p),'bytes':p.stat().st_size})
        groups.append({'id':eid,'title':title,'records':records})
    ledger={'schema':'heav3ns.brocwin.publication-evidence/v1',
            'date':'2026-10-11','version':'1.0.1','groups':groups,
            'scope':'Hashes of cited local records; original large/private artifacts are not embedded in the publication archive.'}
    save(HERE/'evidence-ledger.json',ledger)
    control=ROOT/'theseus/reports/performance/heap-control-20261011'
    runs=[load(control/f'run-0{i}/result.json') for i in (1,2)]
    audit=load(control/'source-audit-review.json')
    suites=load(ROOT/'theseus/reports/performance/heap-reservation-20261011/source-suites.json')
    assert audit['originalInputCount']==321 and audit['checked']==211 and not audit['mismatches']
    assert len(suites['suites'])==12 and all(x['exitCode']==0 for x in suites['suites'])
    facts={'schema':'heav3ns.brocwin.publication-facts/v1','version':'1.0.1',
           'date':'2026-10-11','knowledgeBaseline':'1.4.1','acceptance':'blocked',
           'currentBuildEvidence':None,'control':[],
           'inputEntries':321,'servedObserverIdentities':211,
           'reviewedImageFiles':len(audit['imagesReviewed']),
           'uniqueReviewedImageHashes':len({x['sha256'] for x in audit['imagesReviewed']}),
           'reservationSourceSuites':12,'frozenInventoryFiles':2229,
           'originalInputsBeforeAfterMatch':audit['originalInputsBeforeAfterMatch']}
    for d in runs:
        facts['control'].append({'condition':d['cacheCondition'],
          'firstVisibleLoginSeconds':round(d['firstVisibleSceneSeconds'],3),
          'browserVersion':d['browserVersion'],
          'progress':d['steadyObservation'],'reportedErrors':d['errors']})
    save(HERE/'publication-facts.json',facts)
    lines=['# Shared evidence index','',
      'HEAV3NS-BROCWIN publication edition 1.0.1 · 11 October 2026','',
      'This index supports all three papers. E-identifiers are shared across them. '
      'The [machine-readable ledger](evidence-ledger.json) records SHA-256 and size for every local source below. '
      'The [fact ledger](publication-facts.json) extracts the common control figures directly from retained JSON. '
      'Source files remain in their original locations; they are not silently relocated or republished.','',
      '## Evidence hierarchy and reading rules','',
      'Raw result records and their matching audits govern experimental claims. Wiki pages explain contracts and route readers to implementation. '
      'Corrected closeout 1.4.1 supersedes the earlier 1.4.0 summary: twelve final reservation suites pass, and the final observer refinements remain untested. '
      'Measured control, prepared allocator candidate, older gameplay builds and final working-source differences are separate conditions. '
      'File counts represent different enumerations, not compatibility scores.','',
      '## Local records','']
    for g in groups:
        lines += [f'### {g["id"]}. {g["title"]}','']
        for rec in g['records']:
            rel=Path(__import__('os').path.relpath(ROOT/rec['path'],HERE)).as_posix()
            lines.append(f'- [{rec["path"]}]({rel})')
        lines.append('')
    lines += ['## Interpretation and provenance','',
      'Publication I offers curatorial interpretation. Publication II proposes conditional future research. Publication III synthesizes retained technical evidence. '
      'None records new runtime experiments. MAJO supplies the commission and institutional framing; Dr. GPT prepares these publications. '
      'Original developers, CardSorting/JoySwordOnline contributors, Wine-Assembly human and agent contributors, Microsoft platform contributors, '
      'websockets contributors and Codex integration maintainers retain credit. The corrected rollback record identifies '
      'Codex /root/kernel_audit as implementer, /root/evidence_audit as independent reviewer and /root as closeout coordinator. '
      'The commissioning label is not a claim of academic credentials or exclusive engineering authorship.','',
      'Publication-time visual inspection examined the cold first-visible and warm final-canvas images in E03. '
      'Their visible empty credential fields and login buttons are consistent with the retained audit. '
      'The four audit records contain two unique image hashes; the record does not identify every reviewer. '
      'Image pixels and logos remain attributed to the original game; no game imagery is copied into this publication bundle.','',
      '## External primary references','',
      'External literature supplies context, not BROCWIN results. Consulted 11 October 2026. '
      'Links and bibliographic metadata are preserved; full external texts are not archived here.','',
      '- Rothenberg, Jeff (1999), *Avoiding Technological Quicksand*, CLIR report 77. [Publication](https://www.clir.org/pubs/reports/rothenberg/), [research agenda](https://www.clir.org/pubs/reports/rothenberg/research/).',
      '- UNESCO (2003), *Charter on the Preservation of Digital Heritage*, adopted 15 October. [Primary text](https://www.unesco.org/en/legal-affairs/charter-preservation-digital-heritage).',
      '- Variable Media Network, *The Variable Media Approach*. [Primary institutional account](https://www.variablemedia.net/e/welcome.html). The 2003 *Permanence Through Change* volume is identified as context; its PDF was not retrieved in full.',
      '- Bellard, Fabrice (2005), “QEMU, a Fast and Portable Dynamic Translator,” FREENIX/USENIX ATC, pp. 41–46. [Primary paper](https://www.usenix.org/events/usenix05/tech/freenix/full_papers/bellard/bellard.pdf).',
      '- WebAssembly Community Group, *Core Specification*, displayed 3.0 (2026-10-09). [Primary specification](https://webassembly.github.io/spec/core/). This is contextual, not BROCWIN conformance evidence.',
      '- Microsoft, *PE Format*, Win32 documentation. [Primary documentation](https://learn.microsoft.com/en-us/windows/win32/debug/pe-format).',
      '- Khronos WebGL Working Group, *WebGL Specification 1.0.3*. [Fixed-version specification](https://registry.khronos.org/webgl/specs/1.0.3/).',
      '- Wine Project, *About Wine*. [Primary project description](https://www.winehq.org/about). No Wine performance claims are transferred to BROCWIN.',
      '- Wine-Assembly contributors, dependency commit d7854bc6c6bd0319ca33b5f31a465602e2ce0686. [Pinned repository](https://github.com/vgrichina/wine-assembly/tree/d7854bc6c6bd0319ca33b5f31a465602e2ce0686). Local records establish the pin and patch; upstream online contents were not independently re-audited.','',
      '## Archive and access','',
      'The [archival manifest](archival-manifest.json) inventories the publication files and cited-source hashes. '
      'The publication ZIP includes authored documents, PDF/HTML copies, vector figure, ledgers and production/verification scripts. '
      'Original game/platform payloads, credentials, SQL contents and large report artifacts are excluded. '
      'Relative repository links require the original directory structure. URLs in PDF/HTML and the printed paths in this index provide alternative citation routes. '
      'No external upload or public hosting occurred.']
    (HERE/'evidence-index.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')

def diagram():
    folder=HERE/'figures';folder.mkdir(exist_ok=True)
    boxes=[(30,70,210,70,'Original client / DLLs','x86 instructions; KOM assets'),
           (300,70,220,70,'PE loader + x86 / Wasm','imports, TLS, dispatch'),
           (570,70,220,70,'Windows contracts','memory, threads, APIs'),
           (300,215,220,70,'Browser adapters','WebGL · input · audio'),
           (30,215,210,70,'Manifest + resource host','local files; range mounts'),
           (570,215,220,70,'Winsock + JS wire','vln/1 over WebSocket'),
           (30,380,210,75,'Local byte relay','Python host; fixed targets'),
           (300,380,490,75,'Original native services + isolated SQL','Local deployment; outside client-port scope')]
    parts=['<svg xmlns="http://www.w3.org/2000/svg" width="820" height="490" viewBox="0 0 820 490">',
      '<defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0 0 L8 4 L0 8" fill="#50647a"/></marker></defs>',
      '<rect width="820" height="490" fill="white"/>',
      '<rect x="285" y="35" width="520" height="285" rx="10" fill="#f3f6fa" stroke="#8ba0b5"/>',
      '<text x="300" y="57" font-family="Arial" font-size="15" fill="#21364c">Browser execution and reconstructed interfaces</text>']
    for x,y,w,h,t,s in boxes:
        parts += [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="5" fill="white" stroke="#344e68"/>',
          f'<text x="{x+w/2}" y="{y+27}" text-anchor="middle" font-family="Arial" font-size="16" font-weight="bold" fill="#183249">{html.escape(t)}</text>',
          f'<text x="{x+w/2}" y="{y+51}" text-anchor="middle" font-family="Arial" font-size="13" fill="#344e68">{html.escape(s)}</text>']
    for p in ['M240 105 H300','M520 105 H570','M410 140 V215',
              'M240 250 H270 V175 H410 V140','M680 140 V215',
              'M680 285 V340 H135 V380','M240 417 H300']:
        parts.append(f'<path d="{p}" fill="none" stroke="#50647a" stroke-width="2" marker-end="url(#arrow)"/>')
    parts += ['<text x="30" y="355" font-family="Arial" font-size="14" fill="#344e68">Native backend boundary: original packets; existing local state</text>',
              '<text x="30" y="480" font-family="Arial" font-size="12" fill="#50647a">Repository-derived architecture; arrows are relationships, not measured costs.</text></svg>']
    (folder/'architecture.svg').write_text('\n'.join(parts),encoding='utf-8')
    (folder/'architecture.mmd').write_text('''flowchart TB
  client[Original PE client / DLLs and KOM resources] --> loader
  resources[Manifest and local resource host] --> loader
  subgraph browser[Browser-hosted execution]
    loader[PE loading and x86 interpretation in Wasm] --> contracts[Reconstructed Windows contracts]
    contracts --> graphics[WebGL / DOM input / WebAudio adapters]
    contracts --> winsock[Winsock and vln/1 WebSocket wire]
  end
  winsock --> relay[Fixed local byte relay]
  relay --> native[Original native services and isolated SQL]
''',encoding='utf-8')

CSS='''
@page {size:A4; margin:19mm 17mm 21mm;}
body {font-family:Georgia, "Times New Roman", serif; font-size:10.4pt; line-height:1.46; color:#182431;}
h1,h2,h3 {font-family:Arial,sans-serif; color:#183249; line-height:1.18; break-after:avoid;}
h1 {font-size:24pt; margin:0 0 18pt;} h2 {font-size:15pt; margin:22pt 0 8pt;}
h3 {font-size:11.7pt; margin:14pt 0 7pt;} p {margin:0 0 9pt; orphans:3; widows:3;}
a {color:#245a81;text-decoration:none;} code {font-family:Consolas,monospace;font-size:8.2pt;overflow-wrap:anywhere;}
pre {background:#f1f4f7;padding:9pt;white-space:pre-wrap;overflow-wrap:anywhere;break-inside:avoid;}
table {border-collapse:collapse;width:100%;font-size:8.4pt;line-height:1.28;margin:12pt 0;}
th,td {border:0.5pt solid #bdc9d3;padding:5pt;vertical-align:top;overflow-wrap:anywhere;}
th {background:#eaf0f5;font-family:Arial,sans-serif;text-align:left;} thead {display:table-header-group;}
tr {break-inside:avoid;} img {max-width:100%;max-height:120mm;display:block;margin:10pt auto;}
ul,ol {padding-left:18pt;} li {margin-bottom:5pt;} blockquote {border-left:3pt solid #a6b8c7;padding-left:12pt;}
'''

def render():
    import markdown
    sys.path.insert(0,str(ROOT/'theseus/tools/python'))
    from playwright.sync_api import sync_playwright
    (HERE/'publication.css').write_text(CSS,encoding='utf-8')
    results=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='msedge',headless=True)
        try:
            for name in ['01-environment-as-executable-artifact','02-handoff-and-roadmap','03-technical-white-paper','evidence-index']:
                source=HERE/(name+'.md')
                body=markdown.markdown(source.read_text(encoding='utf-8'),extensions=['tables','fenced_code','toc'])
                title=re.search(r'^# (.+)',source.read_text(encoding='utf-8'),re.M)[1]
                document='<!doctype html><html lang="en"><head><meta charset="utf-8"><title>'+html.escape(title)+'</title><link rel="stylesheet" href="publication.css"></head><body>'+body+'</body></html>'
                target=HERE/(name+'.html');target.write_text(document,encoding='utf-8')
                page=browser.new_page()
                page.route('**/*',lambda route: route.continue_() if route.request.url.startswith(('file:','data:','about:')) else route.abort())
                page.goto(target.as_uri(),wait_until='load')
                page.evaluate('document.fonts.ready')
                page.pdf(path=str(HERE/(name+'.pdf')),format='A4',print_background=True,
                    display_header_footer=True,prefer_css_page_size=True,
                    header_template='<span></span>',
                    footer_template='<div style="font-family:Arial;font-size:8px;width:100%;text-align:center;color:#607286">HEAV3NS-BROCWIN · 11 October 2026 · <span class="pageNumber"></span> / <span class="totalPages"></span></div>')
                results.append({'file':name+'.pdf','browserVersion':browser.version,
                    'bodyTextCharacters':len(page.inner_text('body')),
                    'imageCount':page.locator('img').count(),
                    'imagesComplete':page.locator('img').evaluate_all('(imgs)=>imgs.every(i=>i.complete&&i.naturalWidth>0)')})
                page.close()
        finally:
            browser.close()
    save(HERE/'production-record.json',{'schema':'heav3ns.brocwin.publication-production/v1',
      'recordedAt':datetime.now(timezone.utc).isoformat(),'method':'Existing local Markdown package and headless Edge/Playwright; static local document rendering only; remote requests blocked.',
      'runtimeOrServiceLaunch':False,'newCompatibilityExperiments':False,'documents':results})

def seal():
    paths=sorted(p for p in HERE.rglob('*') if p.is_file() and p.name not in
        ('archival-manifest.json','archive-record.json','brocwin-publications-1.0.1.zip') and '__pycache__' not in p.parts)
    source=load(HERE/'evidence-ledger.json')
    manifest={'schema':'heav3ns.brocwin.publication-archive/v1','version':'1.0.1',
      'publicationDate':'2026-10-11','sealedAt':datetime.now(timezone.utc).isoformat(),
      'title':'HEAV3NS-BROCWIN Curatorial Research and Publication Commission',
      'issuingAuthority':'MAJO, Executive Chair, HEAV3NS','commissionedResearcher':'Dr. GPT',
      'engineeringState':'closed-frozen','clientAcceptance':'blocked','knowledgeBaseline':'1.4.1',
      'files':{p.relative_to(HERE).as_posix():{'sha256':digest(p),'bytes':p.stat().st_size} for p in paths},
      'repositoryRootAtPublication':str(ROOT),
      'citedEvidence':{r['path']:r['sha256'] for g in source['groups'] for r in g['records']},
      'originalArtifactLocations':['client/data','theseus/reports','theseus/checkpoints','theseus/browser/reference','theseus/tools/wine-assembly'],
      'excluded':['credentials and private configuration','database contents','original game/platform binaries','large original evidence','full dependency checkout'],
      'provenance':'Contributor distinctions in evidence-index.md and project provenance records; commissioned researcher is not sole engineering author.',
      'distribution':'Local publication delivery only; no external upload or public hosting.',
      'integrityScope':'SHA-256 verifies enumerated bytes; no digital signature, peer-review endorsement or archival-format certification claimed.'}
    save(HERE/'archival-manifest.json',manifest)
    archive=HERE/'brocwin-publications-1.0.1.zip'
    with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED) as z:
        for p in paths+[HERE/'archival-manifest.json']:
            z.write(p,p.relative_to(HERE).as_posix())
    save(HERE/'archive-record.json',{'version':'1.0.1','path':archive.name,
      'sha256':digest(archive),'bytes':archive.stat().st_size,
      'manifestSha256':digest(HERE/'archival-manifest.json')})
    print(json.dumps({'archive':str(archive),'publicationFiles':len(paths),'sourceRecords':len(manifest['citedEvidence'])}))

if __name__=='__main__':
    if (HERE/'archival-manifest.json').exists():
        raise SystemExit('Edition already sealed; create a new version instead of overwriting.')
    prepare_evidence(); diagram(); render(); seal()
