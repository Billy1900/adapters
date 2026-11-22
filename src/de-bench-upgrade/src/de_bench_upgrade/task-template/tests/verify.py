"""Capture delivered changes, rebuild a clean tree, then invoke upstream scoring."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / 'upstream'))
from de_bench.scoring import score_workspace


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], stderr=subprocess.PIPE)


def unpack(root):
    with tarfile.open(HERE / 'workspace.tar') as archive:
        archive.extractall(root, filter='data')


def verify(workspace, output):
    workspace, output = Path(workspace).resolve(), Path(output)
    output.mkdir(parents=True, exist_ok=True)
    (output / 'reward.txt').unlink(missing_ok=True)
    config = json.loads((HERE / 'config.json').read_text())
    if any(c['kind'] != 'scoring_primitive' for c in config['checks']):
        raise ValueError('Unsupported check: refusing to omit runtime semantics')
    with tempfile.TemporaryDirectory(prefix='de-bench-score-') as temporary:
        root = Path(temporary)
        unpack(root)
        git(root, 'init', '-q')
        git(root, 'add', '-A', *config['add_excludes'])
        git(root, '-c', 'user.name=bench', '-c', 'user.email=bench@localhost', 'commit', '-qm', 'baseline')
        # Use the private original tree as the baseline, never the agent's HEAD.
        for child in root.iterdir():
            if child.name == '.git': continue
            if child.is_dir() and not child.is_symlink(): shutil.rmtree(child)
            else: child.unlink()
        shutil.copytree(workspace, root, dirs_exist_ok=True, symlinks=True,
                        ignore=shutil.ignore_patterns('.git'))
        # Mirror upstream recovery of edits left in stashes, but only in a copy.
        if (workspace / '.git').is_dir():
            stash_copy = root / '.agent-git'
            shutil.copytree(workspace / '.git', stash_copy)
            command = ['git', '--git-dir', str(stash_copy), '--work-tree', str(root)]
            def agent_git(*args):
                return subprocess.run(command + list(args), capture_output=True, cwd=root)
            stashes = agent_git('stash', 'list').stdout.splitlines()
            for _ in stashes:
                if agent_git('stash', 'apply', '-q').returncode:
                    for path in agent_git('diff','--name-only','--diff-filter=U').stdout.decode().splitlines():
                        agent_git('checkout','--ours','--',path)
                agent_git('stash','drop','-q')
            shutil.rmtree(stash_copy)
        git(root, 'add', '-A', *config['add_excludes'])
        patch = git(root, 'diff', '--cached', '--binary', 'HEAD')
        (output / 'changes.patch').write_bytes(patch)
        # Upstream discards runtime outputs and grades only a fresh tree + patch.
        for child in root.iterdir():
            if child.is_dir() and not child.is_symlink(): shutil.rmtree(child)
            else: child.unlink()
        unpack(root)
        if patch.strip():
            git(root, 'init', '-q')
            git(root, 'apply', '--binary', '--whitespace=nowarn', str((output / 'changes.patch').resolve()))
        result = score_workspace(str(root), config['checks'], config['protected'],
                    patch.decode(errors='replace'), baseline_dags=[], replay_dags=config['replay_dags'],
                    oracle_dir=str(HERE / 'oracle'))
        (output / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
        (output / 'reward.txt').write_text('1\n' if result['pass'] else '0\n')
        return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--workspace', required=True)
    parser.add_argument('--output-dir', required=True)
    args = parser.parse_args()
    verify(args.workspace, args.output_dir)
