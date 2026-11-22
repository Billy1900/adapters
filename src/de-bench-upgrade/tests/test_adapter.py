import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from de_bench_upgrade.adapter import DeBenchUpgradeAdapter, TEMPLATE


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


class OverlayTest(unittest.TestCase):
    def test_deleted_globs_and_overlay(self):
        apply = module(TEMPLATE / 'solution/apply.py', 'overlay').apply
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); work = root / 'work'; solution = root / 'solution'
            work.mkdir(); solution.mkdir()
            (work / 'old.py').write_text('old')
            (work / 'keep.txt').write_text('keep')
            (solution / '.deleted').write_text('# comment\n*.py\n')
            (solution / 'new.py').write_text('new')
            apply(solution, work)
            self.assertFalse((work / 'old.py').exists())
            self.assertFalse((work / '.deleted').exists())
            self.assertEqual((work / 'new.py').read_text(), 'new')
            self.assertEqual((work / 'keep.txt').read_text(), 'keep')

    def test_deletion_cannot_escape(self):
        apply = module(TEMPLATE / 'solution/apply.py', 'overlay').apply
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); work = root / 'work'; solution = root / 'solution'
            work.mkdir(); solution.mkdir()
            (solution / '.deleted').write_text('../outside')
            with self.assertRaises(ValueError): apply(solution, work)


@unittest.skipUnless(os.environ.get('DE_BENCH_ROOT'), 'Set DE_BENCH_ROOT to pinned checkout')
class CorpusTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.output = Path(self.temp.name) / 'generated'
        self.root = Path(os.environ['DE_BENCH_ROOT'])

    def adapter(self, **kwargs):
        return DeBenchUpgradeAdapter(self.root, self.output, environment_profile='scoring-smoke', **kwargs)

    def test_inventory_and_deterministic_generation(self):
        adapter = self.adapter(split='smoke')
        inventory = adapter.inventory()
        self.assertEqual((inventory['total'], inventory['compatible']), (62,62))
        self.assertEqual(sum(len(t['checks']) for t in inventory['tasks']),214)
        adapter.run()
        def hashes():
            return {str(p.relative_to(self.output)):hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in self.output.rglob('*') if p.is_file()}
        before = hashes()
        self.adapter(split='smoke', overwrite=True).run()
        self.assertEqual(before, hashes())
        for task_id in json.loads((self.output / 'selection.json').read_text())['task_ids']:
            env = self.output / task_id / 'environment'
            self.assertFalse(list(env.rglob('solution')))
            self.assertFalse(list(env.rglob('checks.yaml')))
            self.assertNotIn('COPY . ', (env / 'Dockerfile').read_text())

    def test_unknown_task_and_existing_destination_rejected(self):
        with self.assertRaises(ValueError): self.adapter(task_ids=['../bad']).run()
        self.assertFalse(self.output.exists())
        self.adapter(limit=1).run()
        with self.assertRaises(FileExistsError): self.adapter(limit=1).run()
        (next(p for p in self.output.iterdir() if p.is_dir()) / 'provenance.json').unlink()
        with self.assertRaises(ValueError): self.adapter(limit=1, overwrite=True).run()

    def test_subset_generation_cannot_leave_stale_tasks(self):
        self.adapter(limit=1).run()
        with self.assertRaisesRegex(ValueError, 'Unselected tasks'):
            self.adapter(task_ids=['task-upgrade-v2-a1b2c3'], overwrite=True).run()

    def test_stashed_oracle_edits_are_recovered_without_mutating_agent(self):
        task_id = self.adapter(task_ids=['task-upgrade-v2-a1b2c3']).run()[0]
        task = self.output / task_id
        work = Path(self.temp.name) / 'work'
        shutil.copytree(task / 'environment/workspace', work)
        def git(*args):
            return subprocess.check_output(['git', '-C', str(work), *args], stderr=subprocess.PIPE)
        git('init', '-q'); git('add', '-A')
        git('-c','user.name=test','-c','user.email=test@localhost','commit','-qm','baseline')
        module(task / 'solution/apply.py', 'overlay').apply(task / 'solution/overlay', work)
        git('stash', 'push', '-u', '-m', 'unfinished validation')
        before = git('stash', 'list')
        result_dir = Path(self.temp.name) / 'result'
        subprocess.run([sys.executable, '-I', str(task / 'tests/verify.py'),
                        '--workspace',str(work),'--output-dir',str(result_dir)], check=True, capture_output=True)
        self.assertTrue(json.loads((result_dir / 'result.json').read_text())['pass'])
        self.assertEqual(before, git('stash', 'list'))
        self.assertEqual(git('status', '--porcelain'), b'')

    def test_verifier_protected_paths_and_excluded_outputs(self):
        task_id = self.adapter(task_ids=['task-upgrade-v2-a1b2c3']).run()[0]
        task = self.output / task_id
        work = Path(self.temp.name) / 'work'
        shutil.copytree(task / 'environment/workspace', work)
        config_path = task / 'tests/config.json'
        config = json.loads(config_path.read_text())
        config['protected'] = ['NOTES.txt']
        config_path.write_text(json.dumps(config))
        (work / 'NOTES.txt').write_text('protected modification')
        result_dir = Path(self.temp.name) / 'result'
        def verify():
            subprocess.run([sys.executable, '-I', str(task / 'tests/verify.py'),
                            '--workspace',str(work),'--output-dir',str(result_dir)], check=True, capture_output=True)
            return json.loads((result_dir / 'result.json').read_text())
        self.assertFalse(verify()['checks']['do_not_modify']['passed'])
        (work / 'NOTES.txt').unlink()
        (work / 'logs').mkdir()
        (work / 'logs/generated.log').write_text('not delivered')
        self.assertFalse(verify()['checks']['delivered']['passed'])


if __name__ == '__main__': unittest.main()
