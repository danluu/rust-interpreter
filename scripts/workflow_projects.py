"""Opt-in public edit workflows outside the executable-probe corpus.

These projects require a case file. Registering one does not enroll it in any
default corpus, choose a test selection, or claim interpreter compatibility.
"""
import json
from pathlib import Path


WORKFLOW_ONLY_PROJECTS = {
    'oxc': {
        'revision': '4d5c812d6b16c23fa71d106cf87f7f20ddee69b1',
        'source': 'https://github.com/oxc-project/oxc.git',
    },
}


def project_revision(root, project):
    if project in WORKFLOW_ONLY_PROJECTS:
        return WORKFLOW_ONLY_PROJECTS[project]['revision']
    return json.loads((Path(root) / 'benchmarks/corpus.json').read_text())['projects'][project]['revision']
