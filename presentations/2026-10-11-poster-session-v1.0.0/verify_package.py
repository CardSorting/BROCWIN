"""Verify the rendered delivery and retained-source identities, without experiments."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    required = ['research-poster.svg', 'research-poster.pdf', 'research-poster.png', 'presenter-script.md', 'storyboard.md', 'storyboard.csv', 'glossary.md', 'audience-qa.md', 'captions.srt', 'captions.vtt', 'transcript.md', 'transcript.txt', 'source-and-attribution-slate.md', 'production-book.html', 'production-book.pdf', 'brocwin-poster-session.mp4', 'source-ledger.json', 'timeline.json', 'session.json']
    assert all((HERE / name).is_file() and (HERE / name).stat().st_size > 0 for name in required)
    ledger = json.loads((HERE / 'source-ledger.json').read_text(encoding='utf-8'))
    changes = [r['path'] for r in ledger['records'] if sha(ROOT / r['path']) != r['sha256']]
    assert not changes, 'Retained-source drift: ' + str(changes)
    assert all(sha(HERE / r['copy']) == r['sha256'] for r in ledger['assets'])
    static = json.loads((HERE / 'static-render-record.json').read_text(encoding='utf-8'))
    assert len(static['scenes']) == 28
    assert not any(s['layoutIssues'] for s in static['scenes']), 'Resolve recorded layout issues'
    probe = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_format', '-show_streams', '-show_chapters', '-of', 'json', str(HERE / 'brocwin-poster-session.mp4')]))
    duration = float(probe['format']['duration'])
    assert abs(duration - 885) <= .1 and 720 <= duration <= 900
    video = next(s for s in probe['streams'] if s['codec_type'] == 'video')
    audio = next(s for s in probe['streams'] if s['codec_type'] == 'audio')
    assert (video['width'], video['height']) == (1920, 1080)
    assert video['codec_name'] == 'h264' and audio['codec_name'] == 'aac'
    assert len(probe['chapters']) == 28
    timeline = json.loads((HERE / 'timeline.json').read_text(encoding='utf-8'))
    assert len(timeline['scenes']) == 28 and abs(timeline['scenes'][-1]['end'] - duration) <= .1
    assert timeline['scenes'][0]['start'] == 0
    for first, second in zip(timeline['scenes'], timeline['scenes'][1:]):
        assert abs(first['end'] - second['start']) < .0001
    cues = json.loads((HERE / 'caption-timing.json').read_text(encoding='utf-8'))['cues']
    assert len({c['utterance'] for c in cues}) == len(timeline['utterances'])
    for i, cue in enumerate(cues):
        assert 0 <= cue['start'] < cue['end'] <= duration
        assert len(cue['text'].splitlines()) <= 2
        assert max(map(len, cue['text'].splitlines())) <= 42
        if i:
            assert cue['start'] >= cues[i - 1]['end'] - .0001
    session = json.loads((HERE / 'session.json').read_text(encoding='utf-8'))
    assert session['scenes'][0]['speech'][0]['text'].startswith('What does it mean for a Windows application to exist outside Windows?')
    assert session['scenes'][-1]['speech'][-1]['text'].endswith('THE WORK NO LONGER DEMANDS AN AUTHOR.')
    assert sum(s['kind'] == 'qa' for s in session['scenes']) == 8
    pdf = (HERE / 'research-poster.pdf').read_bytes()
    assert re.search(rb'/MediaBox\s*\[\s*0\s+0\s+3456\s+2592\s*\]', pdf), 'Poster must be 48 × 36 inches'
    assert len(re.findall(rb'/Type\s*/Page\b', pdf)) == 1
    poster_pixels = None
    from PIL import Image
    with Image.open(HERE / 'research-poster.png') as p:
        poster_pixels = list(p.size)
    assert poster_pixels == [5760, 4320]
    srt_count = len(re.findall(r'^\d+\n\d\d:\d\d:', (HERE / 'captions.srt').read_text(encoding='utf-8'), re.M))
    assert srt_count == len(cues)
    checks = []
    for arguments in [
        ['python', 'theseus/publications/2026-10-11-v1.0.1/verify_publications.py'],
        ['python', 'theseus/knowledge.py', '--check'],
        ['python', 'theseus/knowledge.py', '--verify-release', '1.4.1']]:
        r = subprocess.run(arguments, cwd=ROOT, capture_output=True, text=True)
        checks.append({'command': arguments, 'exitCode': r.returncode, 'stdout': r.stdout.strip(), 'stderr': r.stderr.strip()})
        assert r.returncode == 0, r.stdout + r.stderr
    record = {'schema': 'heav3ns.brocwin.poster-verification/v1', 'verifiedUtc': datetime.now(timezone.utc).isoformat(), 'status': 'passed', 'requiredDeliverables': len(required), 'retainedSourceHashesMatched': len(ledger['records']), 'unchangedCopiedAssets': len(ledger['assets']), 'videoDurationSeconds': duration, 'videoDimensions': [1920, 1080], 'videoFramesPerSecond': video['avg_frame_rate'], 'videoBytes': (HERE / 'brocwin-poster-session.mp4').stat().st_size, 'captionCues': len(cues), 'captionBoundaryScope': 'Measured utterance boundaries; proportional subdivisions within an utterance', 'posterInches': [48, 36], 'posterPixels': poster_pixels, 'posterPages': 1, 'sceneLayoutChecks': 'passed', 'runtimeOrServiceActions': 0, 'existingPublicationAndFrozenKnowledgeChecks': checks}
    (HERE / 'verification-record.json').write_text(json.dumps(record, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in record.items() if k != 'existingPublicationAndFrozenKnowledgeChecks'}, ensure_ascii=False))


if __name__ == '__main__':
    main()
