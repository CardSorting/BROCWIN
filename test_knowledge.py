"""Guard the maintenance checks against stale facts and rewritten evidence."""
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
from knowledge import contained, sync_outputs, check_links, seal_release, verify_release, digest, encoded, checked_current_evidence, checked_frozen_state, checked_manifest


class KnowledgeContract(unittest.TestCase):
    def test_frozen_inventory_rejects_source_or_record_mutation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root/'source.js').write_bytes(b'frozen')
            record = {'schema': 'brocwin.frozen-state/v1',
                      'files': {'source.js': digest(b'frozen')}}
            data = encoded(record)
            (root/'freeze.json').write_bytes(data)
            catalog = {'frozenState': {'path': 'freeze.json', 'sha256': digest(data)}}
            self.assertEqual(checked_frozen_state(catalog, root), record)
            (root/'source.js').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'Frozen file changed'):
                checked_frozen_state(catalog, root)
            (root/'freeze.json').write_bytes(b'{}')
            with self.assertRaisesRegex(ValueError, 'Frozen state record changed'):
                checked_frozen_state(catalog, root)

    def test_prepared_drift_requires_exact_recorded_pair(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            browser = root/'theseus/browser'
            dependency = root/'theseus/tools/wine-assembly'
            (browser/'generated').mkdir(parents=True)
            (browser/'patches').mkdir()
            dependency.mkdir(parents=True)
            (browser/'observer.py').write_bytes(b'new')
            runtime = {'sourceFiles': {}, 'integration': {'observer.py': digest(b'old')},
                       'wasm': {'url': 'main.wasm', 'sha256': digest(b'main')},
                       'compat': {'url': 'compat.wasm', 'sha256': digest(b'compat')},
                       'patchSha256': digest(b'patch')}
            (browser/'generated/manifest.json').write_bytes(encoded({'runtime': runtime}))
            (dependency/'main.wasm').write_bytes(b'main')
            (dependency/'compat.wasm').write_bytes(b'compat')
            for name in ('generated/runtime.patch', 'patches/wine-assembly.patch'):
                (browser/name).write_bytes(b'patch')
            with self.assertRaisesRegex(ValueError, 'Manifest source mismatch'):
                checked_manifest(root)
            pair = {'preparedSha256': digest(b'old'), 'frozenSha256': digest(b'new')}
            frozen = {'preparedSourceDrift': {'theseus/browser/observer.py': pair}}
            checked_manifest(root, frozen)
            (browser/'observer.py').write_bytes(b'later')
            with self.assertRaisesRegex(ValueError, 'Manifest source mismatch'):
                checked_manifest(root, frozen)
            (browser/'observer.py').write_bytes(b'old')
            with self.assertRaisesRegex(ValueError, 'drift no longer matches'):
                checked_manifest(root, frozen)

    def test_old_gameplay_cannot_be_attributed_to_new_build(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            runtime = {'wasm': {'sha256': 'old'}, 'compat': {'sha256': 'same'}, 'patchSha256': 'patch'}
            (root / 'review.json').write_text(json.dumps(runtime))
            catalog = {'currentBuildEvidence': 'review', 'evidence': [{'id': 'review', 'path': 'review.json'}]}
            self.assertEqual(checked_current_evidence(catalog, runtime, root), 'review')
            for field, replacement in [('wasm', {'sha256': 'new'}), ('compat', {'sha256': 'new'}), ('patchSha256', 'new')]:
                with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'different candidate'):
                    checked_current_evidence(catalog, {**runtime, field: replacement}, root)
            catalog['currentBuildEvidence'] = None
            self.assertIsNone(checked_current_evidence(catalog, runtime, root))

    def test_stale_output_is_detected(self):
        with tempfile.TemporaryDirectory() as temp:
            wiki = Path(temp)
            output = {'generated/identity.json': b'{"build":1}\n'}
            with self.assertRaisesRegex(ValueError, 'Stale'):
                sync_outputs(output, wiki=wiki)
            self.assertEqual(sync_outputs(output, True, wiki), 1)
            self.assertEqual(sync_outputs(output, wiki=wiki), 0)
            with self.assertRaisesRegex(ValueError, 'Stale'):
                sync_outputs({'generated/identity.json': b'{"build":2}\n'}, wiki=wiki)

    def test_evidence_cannot_be_reblessed(self):
        with tempfile.TemporaryDirectory() as temp:
            wiki = Path(temp)
            name = 'generated/evidence/control.json'
            sync_outputs({name:b'{"result":"failed"}'}, True, wiki)
            with self.assertRaisesRegex(ValueError, 'Preserved evidence changed'):
                sync_outputs({name:b'{"result":"passed"}'}, True, wiki)
            self.assertIn(b'failed', (wiki/name).read_bytes())

    def test_paths_and_links_cannot_escape_or_disappear(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with self.assertRaisesRegex(ValueError, 'escapes'):
                contained(root, '../private')
            (root/'home.md').write_text('[missing](lost.md)')
            with self.assertRaisesRegex(ValueError, 'Broken local links'):
                check_links(root, root)
            (root/'lost.md').write_text('# Present\n')
            self.assertEqual(check_links(root,root), 1)
            (root/'home.md').write_text('[missing anchor](lost.md#absent)')
            with self.assertRaisesRegex(ValueError, 'unknown anchor'):
                check_links(root,root)

    def test_release_overwrite_is_refused_before_packaging(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); wiki=root/'wiki'; (wiki/'releases').mkdir(parents=True)
            (wiki/'catalog.json').write_text(json.dumps({'version':'1.0.0'}))
            (wiki/'releases/1.0.0.json').write_bytes(b'original')
            with self.assertRaisesRegex(ValueError, 'already exists'):
                seal_release('1.0.0',wiki,root)
            self.assertEqual((wiki/'releases/1.0.0.json').read_bytes(),b'original')

    def test_release_verifies_archive_and_artifacts(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); wiki=root/'wiki'; (wiki/'releases').mkdir(parents=True)
            record={'version':'1.0.0','files':{'wiki/readme.md':digest(b'original')}}
            archive=root/'bundle.zip'
            def package(payload):
                with zipfile.ZipFile(archive,'w') as bundle:
                    bundle.writestr('wiki/readme.md',payload)
                    bundle.writestr('release.json',encoded(record))
                full={**record,'archive':{'path':'bundle.zip','sha256':digest(archive.read_bytes())}}
                (wiki/'releases/1.0.0.json').write_bytes(encoded(full))
            package(b'original')
            self.assertEqual(verify_release('1.0.0',wiki,root)['verifiedArtifacts'],1)
            package(b'changed')
            with self.assertRaisesRegex(ValueError,'artifact hash mismatch'):
                verify_release('1.0.0',wiki,root)
            archive.write_bytes(b'corrupt')
            with self.assertRaisesRegex(ValueError,'archive hash mismatch'):
                verify_release('1.0.0',wiki,root)


if __name__ == '__main__':
    unittest.main()
