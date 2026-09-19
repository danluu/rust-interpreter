"""Independent bounded read-only audit of the exact qualified-driver archive.

Actual receipt, wrapper record and summary digests are supplied only after
archive closure. This file does not import or execute the archive engine.
"""
import argparse
import fcntl
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import shutil
import stat
import sys
import tarfile
import time

R = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
A = Path('/Users/danluu/dev/rust-interp-runtime-application-admission-20260918')
X = Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
H = R/'experiments/hash-driver-success-evidence-02'
W = R/'.work/hash-driver-success-evidence-01'
E = R/'.work/hash-driver-success-retention-execution-02'
D = R/'results/hir-options-hash-driver-02'
OUT = A/'.work/hash-driver-success-retention-independent-verification-03.json'
PROPOSAL = A/'.work/hash-driver02-lossless-publication-scope-02.json'
PROPOSAL_SHA = 'f6ea57ce5485de96bcc00aa6bb872cf2560ba023df48affea533806e3fac7264'
ENGINE_SHA = 'c14818c16d8d3863bc9135203749f9ab75b46fe6b32b288e5357609627d4a39e'
WRAPPER_SHA = '8987c2eb72a52b2deb5c6304901d6c419c19d46f87132bdca89b9958a9d97de0'
OWNED = X/'experiments/stable-cgu/owned_stage.py'
OWNED_SHA = '7021a15d3b806ab908f03276051d9d9ca9c9e208bbf8933a60229c9fb35bb68e'
PYTHON = Path('/opt/homebrew/Cellar/python@3.14/3.14.7/Frameworks/Python.framework/Versions/3.14/bin/python3.14')
LOCK = Path('/Users/danluu/dev/rust-interp/.work/benchmark.lock')
ENVIRONMENT = dict(HOME='/Users/danluu', USER='danluu', LOGNAME='danluu', LANG='C', LC_ALL='C',
                   TZ='UTC', PATH='/usr/bin:/bin:/usr/sbin:/sbin', PYTHONDONTWRITEBYTECODE='1', PYTHONNOUSERSITE='1')
FIELDS = ('dev', 'ino', 'mode', 'nlink', 'size', 'mtime_ns', 'ctime_ns')
STARTUP_ADDITIONS = {'__CF_USER_TEXT_ENCODING': '0x1F5:0x0:0x52'}
PREVIOUS_FILES = {'/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/hash-driver-success-evidence-01/archive.py': {'sha256': 'c0c4b601f7f7aeb5f57a31bafc6df75bd1ef7a28d36a0fd65bbdb14304a87c64', 'size': 32157, 'identity': {'dev': 16777229, 'ino': 1056074043, 'mode': 33152, 'nlink': 1, 'size': 32157, 'mtime_ns': 1789807548212958347, 'ctime_ns': 1789807548212958347}}, '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/hash-driver-success-evidence-01/execute.py': {'sha256': '7f2bcd3ce2aaf787805c24bad5e612931ab4d10f3cfc442dbcd41f319c35f252', 'size': 9206, 'identity': {'dev': 16777229, 'ino': 1056077820, 'mode': 33152, 'nlink': 1, 'size': 9206, 'mtime_ns': 1789807586035967861, 'ctime_ns': 1789807586035967861}}, '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/.work/hash-driver-success-retention-execution-01/record.json': {'sha256': 'f77467941c8b264b1a64904565bfff0151737e4ddcbf72f6cb8a3896884ac6c0', 'size': 2574, 'identity': {'dev': 16777229, 'ino': 1056081440, 'mode': 33152, 'nlink': 1, 'size': 2574, 'mtime_ns': 1789807749236538675, 'ctime_ns': 1789807749236640925}}, '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/.work/hash-driver-success-retention-execution-01/source/archive.py': {'sha256': 'c0c4b601f7f7aeb5f57a31bafc6df75bd1ef7a28d36a0fd65bbdb14304a87c64', 'size': 32157, 'identity': {'dev': 16777229, 'ino': 1056081429, 'mode': 33152, 'nlink': 1, 'size': 32157, 'mtime_ns': 1789807749147114561, 'ctime_ns': 1789807749147114561}}, '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/.work/hash-driver-success-retention-execution-01/source/execution.py': {'sha256': '7f2bcd3ce2aaf787805c24bad5e612931ab4d10f3cfc442dbcd41f319c35f252', 'size': 9206, 'identity': {'dev': 16777229, 'ino': 1056081432, 'mode': 33152, 'nlink': 1, 'size': 9206, 'mtime_ns': 1789807749149134357, 'ctime_ns': 1789807749149134357}}, '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/.work/hash-driver-success-retention-execution-01/source/owned_stage.py': {'sha256': '7021a15d3b806ab908f03276051d9d9ca9c9e208bbf8933a60229c9fb35bb68e', 'size': 9457, 'identity': {'dev': 16777229, 'ino': 1056081431, 'mode': 33152, 'nlink': 1, 'size': 9457, 'mtime_ns': 1789807749148908690, 'ctime_ns': 1789807749148908690}}, '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/.work/hash-driver-success-retention-execution-01/source/proposal.json': {'sha256': 'f6ea57ce5485de96bcc00aa6bb872cf2560ba023df48affea533806e3fac7264', 'size': 560242, 'identity': {'dev': 16777229, 'ino': 1056081430, 'mode': 33152, 'nlink': 1, 'size': 560242, 'mtime_ns': 1789807749147851146, 'ctime_ns': 1789807749147851146}}, '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/.work/hash-driver-success-retention-execution-01/stderr': {'sha256': '9a48ef671c19fa36edff79c0f6047950c46fdc0ea66a80f2b5686a38c69c5d52', 'size': 798, 'identity': {'dev': 16777229, 'ino': 1056081437, 'mode': 33152, 'nlink': 1, 'size': 798, 'mtime_ns': 1789807749217654633, 'ctime_ns': 1789807749217654633}}, '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/.work/hash-driver-success-retention-execution-01/stdout': {'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'size': 0, 'identity': {'dev': 16777229, 'ino': 1056081436, 'mode': 33152, 'nlink': 1, 'size': 0, 'mtime_ns': 1789807749150276693, 'ctime_ns': 1789807749150276693}}}
FAILURE_ARCHIVE_PUBLICATION = {'path': '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/hir-options-hash-driver-failure-01/evidence.tar.gz', 'archive_sha256': 'ff7870ea202cd33b7c91e2afe8b3784780fee1d9239a7df6394eaf0560417216', 'git_blob': '09c50202c9b3241d7c620053cd47c3f283136c88', 'commit': '075141b3d11a5172ab59ecbdeface0d340fac016', 'provenance': 'Root-reported completed publication; original scope02 retains its historical null Git reference. No Git object read is claimed by this archive.'}
PREVIOUS_AUDIT_FILES = {'/Users/danluu/dev/rust-interp-runtime-application-admission-20260918/.work/hash-driver-success-retention-audit-execution-02/record.json': {'identity': {'ctime_ns': 1789808501659774554, 'dev': 16777229, 'ino': 1056118399, 'mode': 33152, 'mtime_ns': 1789808501659706970, 'nlink': 1, 'size': 3230}, 'sha256': 'b8664ef82a249e224601327fb5df55520ef1e3f78e8a34f862fae8e3908d9858', 'size': 3230}, '/Users/danluu/dev/rust-interp-runtime-application-admission-20260918/.work/hash-driver-success-retention-audit-execution-02/source/archive-execution.py': {'identity': {'ctime_ns': 1789808501515910784, 'dev': 16777229, 'ino': 1056118388, 'mode': 33152, 'mtime_ns': 1789808501515910784, 'nlink': 1, 'size': 9605}, 'sha256': '8987c2eb72a52b2deb5c6304901d6c419c19d46f87132bdca89b9958a9d97de0', 'size': 9605}, '/Users/danluu/dev/rust-interp-runtime-application-admission-20260918/.work/hash-driver-success-retention-audit-execution-02/source/archive.py': {'identity': {'ctime_ns': 1789808501515671075, 'dev': 16777229, 'ino': 1056118387, 'mode': 33152, 'mtime_ns': 1789808501515671075, 'nlink': 1, 'size': 43421}, 'sha256': 'c14818c16d8d3863bc9135203749f9ab75b46fe6b32b288e5357609627d4a39e', 'size': 43421}, '/Users/danluu/dev/rust-interp-runtime-application-admission-20260918/.work/hash-driver-success-retention-audit-execution-02/source/audit.py': {'identity': {'ctime_ns': 1789808501515285616, 'dev': 16777229, 'ino': 1056118386, 'mode': 33152, 'mtime_ns': 1789808501515285616, 'nlink': 1, 'size': 44777}, 'sha256': '83091dcd44a00ef1294eaf177bf49146d61d98883b566fb7a107aa8607fe2bde', 'size': 44777}, '/Users/danluu/dev/rust-interp-runtime-application-admission-20260918/.work/hash-driver-success-retention-audit-execution-02/source/execution.py': {'identity': {'ctime_ns': 1789808501518027997, 'dev': 16777229, 'ino': 1056118391, 'mode': 33152, 'mtime_ns': 1789808501518027997, 'nlink': 1, 'size': 8472}, 'sha256': '96fe8467af0092ef6f2f9760ea1ccaf895b264057b6c96d4698abb484967c285', 'size': 8472}, '/Users/danluu/dev/rust-interp-runtime-application-admission-20260918/.work/hash-driver-success-retention-audit-execution-02/source/owned_stage.py': {'identity': {'ctime_ns': 1789808501517723496, 'dev': 16777229, 'ino': 1056118390, 'mode': 33152, 'mtime_ns': 1789808501517723496, 'nlink': 1, 'size': 9457}, 'sha256': '7021a15d3b806ab908f03276051d9d9ca9c9e208bbf8933a60229c9fb35bb68e', 'size': 9457}, '/Users/danluu/dev/rust-interp-runtime-application-admission-20260918/.work/hash-driver-success-retention-audit-execution-02/source/proposal.json': {'identity': {'ctime_ns': 1789808501516510827, 'dev': 16777229, 'ino': 1056118389, 'mode': 33152, 'mtime_ns': 1789808501516510827, 'nlink': 1, 'size': 560242}, 'sha256': 'f6ea57ce5485de96bcc00aa6bb872cf2560ba023df48affea533806e3fac7264', 'size': 560242}, '/Users/danluu/dev/rust-interp-runtime-application-admission-20260918/.work/hash-driver-success-retention-audit-execution-02/stderr': {'identity': {'ctime_ns': 1789808501635154500, 'dev': 16777229, 'ino': 1056118396, 'mode': 33152, 'mtime_ns': 1789808501635154500, 'nlink': 1, 'size': 1358}, 'sha256': '0d99a5cdeb295d87961fa2fd56a1477f3914401f61d69b017078f609d9359811', 'size': 1358}, '/Users/danluu/dev/rust-interp-runtime-application-admission-20260918/.work/hash-driver-success-retention-audit-execution-02/stdout': {'identity': {'ctime_ns': 1789808501519680334, 'dev': 16777229, 'ino': 1056118395, 'mode': 33152, 'mtime_ns': 1789808501519680334, 'nlink': 1, 'size': 0}, 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'size': 0}, '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/hash-driver-success-evidence-02/execute_verify.py': {'identity': {'ctime_ns': 1789808414052028072, 'dev': 16777229, 'ino': 1056107451, 'mode': 33152, 'mtime_ns': 1789808414052028072, 'nlink': 1, 'size': 8472}, 'sha256': '96fe8467af0092ef6f2f9760ea1ccaf895b264057b6c96d4698abb484967c285', 'size': 8472}, '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/hash-driver-success-evidence-02/verify.py': {'identity': {'ctime_ns': 1789808414049711400, 'dev': 16777229, 'ino': 1056107450, 'mode': 33152, 'mtime_ns': 1789808414049711400, 'nlink': 1, 'size': 44777}, 'sha256': '83091dcd44a00ef1294eaf177bf49146d61d98883b566fb7a107aa8607fe2bde', 'size': 44777}}
GIT_PUBLICATION_PROOF = {'report': {'path': '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/.work/published-failure-archive-git-proof-01/report.json', 'sha256': '38d5711a6550be87368ce98595e655d3c3de586c50f75d7a2702e0b5d47da38b', 'size': 36665, 'identity': {'dev': 16777229, 'ino': 1056124589, 'mode': 33152, 'nlink': 1, 'size': 36665, 'mtime_ns': 1789808887461457226, 'ctime_ns': 1789808887461457226}}, 'source': {'path': '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/.work/verify_published_failure_archive_git_01.py', 'sha256': '8b758427668a1fd6fc26aae802164fa477b5354c77243627762dd567d6be08e7', 'size': 7988, 'identity': {'dev': 16777229, 'ino': 1056124445, 'mode': 33152, 'nlink': 1, 'size': 7988, 'mtime_ns': 1789808867707247499, 'ctime_ns': 1789808867707247499}}, 'files': [{'identity': {'ctime_ns': 1789808887410153532, 'dev': 16777229, 'ino': 1056124571, 'mode': 33152, 'mtime_ns': 1789808887410153532, 'nlink': 1, 'size': 529}, 'path': '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/.work/published-failure-archive-git-proof-01/commands/blob-content/launch.json', 'sha256': '0dbe44c335f6426c556db1cf6f1570a6cbb41c4356885e1c253eb3496998bf0d', 'size': 529}, {'identity': {'ctime_ns': 1789808887425756607, 'dev': 16777229, 'ino': 1056124573, 'mode': 33152, 'mtime_ns': 1789808887425756607, 'nlink': 1, 'size': 983}, 'path': '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/.work/published-failure-archive-git-proof-01/commands/blob-content/record.json', 'sha256': '81b0eb4496266bb597b0663c6a7f5bc587d7281b05e563922aff0e154af71758', 'size': 983}, {'identity': {'ctime_ns': 1789808887425672357, 'dev': 16777229, 'ino': 1056124572, 'mode': 33152, 'mtime_ns': 1789808887425672357, 'nlink': 1, 'size': 0}, 'path': '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/.work/published-failure-archive-git-proof-01/commands/blob-content/stderr', 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'size': 0}, {'identity': {'ctime_ns': 1789808887400022593, 'dev': 16777229, 'ino': 1056124566, 'mode': 33152, 'mtime_ns': 1789808887400022593, 'nlink': 1, 'size': 528}, 'path': '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/.work/published-failure-archive-git-proof-01/commands/blob-size/launch.json', 'sha256': 'd0edaa45730f95548466ee6e7dc5c59dd7e8d3ca9d9068f9447b7a58a6241381', 'size': 528}, {'identity': {'ctime_ns': 1789808887408764529, 'dev': 16777229, 'ino': 1056124569, 'mode': 33152, 'mtime_ns': 1789808887408764529, 'nlink': 1, 'size': 974}, 'path': '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/.work/published-failure-archive-git-proof-01/commands/blob-size/record.json', 'sha256': '956d5997502cb4b2fdc3aba6f743ee2dcd6513fa2c9afd6884507457df88aaef', 'size': 974}, {'identity': {'ctime_ns': 1789808887408681487, 'dev': 16777229, 'ino': 1056124568, 'mode': 33152, 'mtime_ns': 1789808887408681487, 'nlink': 1, 'size': 0}, 'path': '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/.work/published-failure-archive-git-proof-01/commands/blob-size/stderr', 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'size': 0}, {'identity': {'ctime_ns': 1789808887408607237, 'dev': 16777229, 'ino': 1056124567, 'mode': 33152, 'mtime_ns': 1789808887408607237, 'nlink': 1, 'size': 9}, 'path': '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/.work/published-failure-archive-git-proof-01/commands/blob-size/stdout', 'sha256': '7b5e442e47ae1ba9adb3f14606e4c1204f3056c3dd7ef6514f4a2a393927c78d', 'size': 9}, {'identity': {'ctime_ns': 1789808887389057361, 'dev': 16777229, 'ino': 1056124561, 'mode': 33152, 'mtime_ns': 1789808887389057361, 'nlink': 1, 'size': 527}, 'path': '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/.work/published-failure-archive-git-proof-01/commands/blob-type/launch.json', 'sha256': 'addaeb5597a8a818951b64d9a4a37ce01f04f21e0931e12b56a130f858b0d734', 'size': 527}, {'identity': {'ctime_ns': 1789808887398230089, 'dev': 16777229, 'ino': 1056124564, 'mode': 33152, 'mtime_ns': 1789808887398230089, 'nlink': 1, 'size': 973}, 'path': '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/.work/published-failure-archive-git-proof-01/commands/blob-type/record.json', 'sha256': '352221616aaa7272457df8aaedba55d32d83386ff31498ef77e8c0818d64fb76', 'size': 973}, {'identity': {'ctime_ns': 1789808887398152631, 'dev': 16777229, 'ino': 1056124563, 'mode': 33152, 'mtime_ns': 1789808887398152631, 'nlink': 1, 'size': 0}, 'path': '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/.work/published-failure-archive-git-proof-01/commands/blob-type/stderr', 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'size': 0}, {'identity': {'ctime_ns': 1789808887398092006, 'dev': 16777229, 'ino': 1056124562, 'mode': 33152, 'mtime_ns': 1789808887398092006, 'nlink': 1, 'size': 5}, 'path': '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/.work/published-failure-archive-git-proof-01/commands/blob-type/stdout', 'sha256': 'bc103b4a84971ef6459b294a2b98568a2bfb72cded09d4acd1e16366a401f95b', 'size': 5}, {'identity': {'ctime_ns': 1789808887378112837, 'dev': 16777229, 'ino': 1056124556, 'mode': 33152, 'mtime_ns': 1789808887378112837, 'nlink': 1, 'size': 541}, 'path': '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/.work/published-failure-archive-git-proof-01/commands/current-blob/launch.json', 'sha256': '06bf45689636774d4ddac52964d7ee5d171133503bc68480a5524b3d39ed14ac', 'size': 541}, {'identity': {'ctime_ns': 1789808887387761108, 'dev': 16777229, 'ino': 1056124559, 'mode': 33152, 'mtime_ns': 1789808887387761108, 'nlink': 1, 'size': 987}, 'path': '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/.work/published-failure-archive-git-proof-01/commands/current-blob/record.json', 'sha256': '863cc6c066fbb8950c02d8df2e5ed3749455c17c336425eae717fcbd983a8ec3', 'size': 987}, {'identity': {'ctime_ns': 1789808887387673983, 'dev': 16777229, 'ino': 1056124558, 'mode': 33152, 'mtime_ns': 1789808887387673983, 'nlink': 1, 'size': 0}, 'path': '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/.work/published-failure-archive-git-proof-01/commands/current-blob/stderr', 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'size': 0}, {'identity': {'ctime_ns': 1789808887387600191, 'dev': 16777229, 'ino': 1056124557, 'mode': 33152, 'mtime_ns': 1789808887387600191, 'nlink': 1, 'size': 41}, 'path': '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/.work/published-failure-archive-git-proof-01/commands/current-blob/stdout', 'sha256': '6df25a6130089d0a948c93b9a2687d0078cfda092b7d6ab23a9e0b51a7ad7823', 'size': 41}, {'identity': {'ctime_ns': 1789808887446408860, 'dev': 16777229, 'ino': 1056124585, 'mode': 33152, 'mtime_ns': 1789808887446408860, 'nlink': 1, 'size': 555}, 'path': '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/.work/published-failure-archive-git-proof-01/commands/entry-after/launch.json', 'sha256': '8e6c9ba1871941851c007e447fb5072439e5302497b016fad846eacf1299e382', 'size': 555}, {'identity': {'ctime_ns': 1789808887459531055, 'dev': 16777229, 'ino': 1056124588, 'mode': 33152, 'mtime_ns': 1789808887459531055, 'nlink': 1, 'size': 1003}, 'path': '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/.work/published-failure-archive-git-proof-01/commands/entry-after/record.json', 'sha256': '125fe2cd5824fbb908dc6551bbb4b1da59c44e4f512f5636ebe2f4c54f94c1d6', 'size': 1003}, {'identity': {'ctime_ns': 1789808887459460389, 'dev': 16777229, 'ino': 1056124587, 'mode': 33152, 'mtime_ns': 1789808887459460389, 'nlink': 1, 'size': 0}, 'path': '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/.work/published-failure-archive-git-proof-01/commands/entry-after/stderr', 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'size': 0}, {'identity': {'ctime_ns': 1789808887459386430, 'dev': 16777229, 'ino': 1056124586, 'mode': 33152, 'mtime_ns': 1789808887459386430, 'nlink': 1, 'size': 61}, 'path': '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/.work/published-failure-archive-git-proof-01/commands/entry-after/stdout', 'sha256': '1229deac011833dbf71e1b724965e60fa8106ad40ac999d743af6f3013db9fb7', 'size': 61}, {'identity': {'ctime_ns': 1789808887348815149, 'dev': 16777229, 'ino': 1056124546, 'mode': 33152, 'mtime_ns': 1789808887348815149, 'nlink': 1, 'size': 555}, 'path': '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/.work/published-failure-archive-git-proof-01/commands/entry-before/launch.json', 'sha256': '9865179c6300cb59eebb96da962d86e41ed560e19bdcefe36606e2e68eab43fc', 'size': 555}, {'identity': {'ctime_ns': 1789808887364593433, 'dev': 16777229, 'ino': 1056124549, 'mode': 33152, 'mtime_ns': 1789808887364593433, 'nlink': 1, 'size': 1002}, 'path': '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/.work/published-failure-archive-git-proof-01/commands/entry-before/record.json', 'sha256': 'd8572dd00ae30108657ba367e00367d5e873dd8b45b8df2829376443b342664c', 'size': 1002}, {'identity': {'ctime_ns': 1789808887364513975, 'dev': 16777229, 'ino': 1056124548, 'mode': 33152, 'mtime_ns': 1789808887364513975, 'nlink': 1, 'size': 0}, 'path': '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/.work/published-failure-archive-git-proof-01/commands/entry-before/stderr', 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'size': 0}, {'identity': {'ctime_ns': 1789808887364449766, 'dev': 16777229, 'ino': 1056124547, 'mode': 33152, 'mtime_ns': 1789808887364449766, 'nlink': 1, 'size': 61}, 'path': '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/.work/published-failure-archive-git-proof-01/commands/entry-before/stdout', 'sha256': '1229deac011833dbf71e1b724965e60fa8106ad40ac999d743af6f3013db9fb7', 'size': 61}, {'identity': {'ctime_ns': 1789808887427254194, 'dev': 16777229, 'ino': 1056124575, 'mode': 33152, 'mtime_ns': 1789808887427254194, 'nlink': 1, 'size': 482}, 'path': '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/.work/published-failure-archive-git-proof-01/commands/head-after/launch.json', 'sha256': 'ddcf415b51d3d00bc16b9aac77790620954a4382123e8649a60a30c6235c6d9d', 'size': 482}, {'identity': {'ctime_ns': 1789808887435702212, 'dev': 16777229, 'ino': 1056124578, 'mode': 33152, 'mtime_ns': 1789808887435702212, 'nlink': 1, 'size': 928}, 'path': '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/.work/published-failure-archive-git-proof-01/commands/head-after/record.json', 'sha256': '21e5ad244fe2f6f38d1b873bbbe048bf2cbc0c2c5b4a9df279c053327f02dac9', 'size': 928}, {'identity': {'ctime_ns': 1789808887435490587, 'dev': 16777229, 'ino': 1056124577, 'mode': 33152, 'mtime_ns': 1789808887435490587, 'nlink': 1, 'size': 0}, 'path': '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/.work/published-failure-archive-git-proof-01/commands/head-after/stderr', 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'size': 0}, {'identity': {'ctime_ns': 1789808887435417711, 'dev': 16777229, 'ino': 1056124576, 'mode': 33152, 'mtime_ns': 1789808887435417711, 'nlink': 1, 'size': 41}, 'path': '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/.work/published-failure-archive-git-proof-01/commands/head-after/stdout', 'sha256': '5e1b1125100ca006bd3f32f9c77a4bd7d50a6b4a625a6b4ee1d8117511684cd4', 'size': 41}, {'identity': {'ctime_ns': 1789808887327921020, 'dev': 16777229, 'ino': 1056124536, 'mode': 33152, 'mtime_ns': 1789808887327921020, 'nlink': 1, 'size': 482}, 'path': '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/.work/published-failure-archive-git-proof-01/commands/head-before/launch.json', 'sha256': 'f897f01ae140aaf0c96c163639f4aa0be14bd035fcf38fa87f5ed8ef276b73e0', 'size': 482}, {'identity': {'ctime_ns': 1789808887337450124, 'dev': 16777229, 'ino': 1056124539, 'mode': 33152, 'mtime_ns': 1789808887337450124, 'nlink': 1, 'size': 927}, 'path': '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/.work/published-failure-archive-git-proof-01/commands/head-before/record.json', 'sha256': 'afb71634eaa921013853c020511cc24c940b3170ff85cd3229e87c153a1201aa', 'size': 927}, {'identity': {'ctime_ns': 1789808887337328207, 'dev': 16777229, 'ino': 1056124538, 'mode': 33152, 'mtime_ns': 1789808887337328207, 'nlink': 1, 'size': 0}, 'path': '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/.work/published-failure-archive-git-proof-01/commands/head-before/stderr', 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'size': 0}, {'identity': {'ctime_ns': 1789808887337216624, 'dev': 16777229, 'ino': 1056124537, 'mode': 33152, 'mtime_ns': 1789808887337216624, 'nlink': 1, 'size': 41}, 'path': '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/.work/published-failure-archive-git-proof-01/commands/head-before/stdout', 'sha256': '5e1b1125100ca006bd3f32f9c77a4bd7d50a6b4a625a6b4ee1d8117511684cd4', 'size': 41}, {'identity': {'ctime_ns': 1789808887366343728, 'dev': 16777229, 'ino': 1056124551, 'mode': 33152, 'mtime_ns': 1789808887366343728, 'nlink': 1, 'size': 577}, 'path': '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/.work/published-failure-archive-git-proof-01/commands/published-blob/launch.json', 'sha256': '8bd5ec8f6f93cf0f2c9e1c6bf2b6a98ee0759c730fb069ab4b35ab0439a8fd92', 'size': 577}, {'identity': {'ctime_ns': 1789808887376615876, 'dev': 16777229, 'ino': 1056124554, 'mode': 33152, 'mtime_ns': 1789808887376615876, 'nlink': 1, 'size': 1024}, 'path': '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/.work/published-failure-archive-git-proof-01/commands/published-blob/record.json', 'sha256': '58ea517f63bffb369e7202970023c90392d57d6b431c141635e5faa89c397f09', 'size': 1024}, {'identity': {'ctime_ns': 1789808887376526292, 'dev': 16777229, 'ino': 1056124553, 'mode': 33152, 'mtime_ns': 1789808887376526292, 'nlink': 1, 'size': 0}, 'path': '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/.work/published-failure-archive-git-proof-01/commands/published-blob/stderr', 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'size': 0}, {'identity': {'ctime_ns': 1789808887376451334, 'dev': 16777229, 'ino': 1056124552, 'mode': 33152, 'mtime_ns': 1789808887376451334, 'nlink': 1, 'size': 41}, 'path': '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/.work/published-failure-archive-git-proof-01/commands/published-blob/stdout', 'sha256': '6df25a6130089d0a948c93b9a2687d0078cfda092b7d6ab23a9e0b51a7ad7823', 'size': 41}, {'identity': {'ctime_ns': 1789808887436991090, 'dev': 16777229, 'ino': 1056124580, 'mode': 33152, 'mtime_ns': 1789808887436991090, 'nlink': 1, 'size': 507}, 'path': '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/.work/published-failure-archive-git-proof-01/commands/sparse-after/launch.json', 'sha256': '33040806538e368fe29a64e731453ca43afda722f885d270394d0100c3bd175f', 'size': 507}, {'identity': {'ctime_ns': 1789808887445036149, 'dev': 16777229, 'ino': 1056124583, 'mode': 33152, 'mtime_ns': 1789808887445036149, 'nlink': 1, 'size': 953}, 'path': '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/.work/published-failure-archive-git-proof-01/commands/sparse-after/record.json', 'sha256': '94362868d20cc86ad759529493f3d821a5c909bb71a76eae660eaaa18714c5e8', 'size': 953}, {'identity': {'ctime_ns': 1789808887444890607, 'dev': 16777229, 'ino': 1056124582, 'mode': 33152, 'mtime_ns': 1789808887444890607, 'nlink': 1, 'size': 0}, 'path': '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/.work/published-failure-archive-git-proof-01/commands/sparse-after/stderr', 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'size': 0}, {'identity': {'ctime_ns': 1789808887444831190, 'dev': 16777229, 'ino': 1056124581, 'mode': 33152, 'mtime_ns': 1789808887444831190, 'nlink': 1, 'size': 5}, 'path': '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/.work/published-failure-archive-git-proof-01/commands/sparse-after/stdout', 'sha256': 'a17fcf0a2f50e2d495e4f90ce263410edc183add6c62699a2facbccf60410f74', 'size': 5}, {'identity': {'ctime_ns': 1789808887338961711, 'dev': 16777229, 'ino': 1056124541, 'mode': 33152, 'mtime_ns': 1789808887338961711, 'nlink': 1, 'size': 507}, 'path': '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/.work/published-failure-archive-git-proof-01/commands/sparse-before/launch.json', 'sha256': '81ba2017bc95904bc15c6eda09fd2ffc1fef5eca20b6023b4dc990d2604708a3', 'size': 507}, {'identity': {'ctime_ns': 1789808887347228771, 'dev': 16777229, 'ino': 1056124544, 'mode': 33152, 'mtime_ns': 1789808887347228771, 'nlink': 1, 'size': 953}, 'path': '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/.work/published-failure-archive-git-proof-01/commands/sparse-before/record.json', 'sha256': 'aeee67829fcad2e46bcfb1ebba08a65fa1cfa929527ffed9c1c32a5dce0dc8ae', 'size': 953}, {'identity': {'ctime_ns': 1789808887347139229, 'dev': 16777229, 'ino': 1056124543, 'mode': 33152, 'mtime_ns': 1789808887347139229, 'nlink': 1, 'size': 0}, 'path': '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/.work/published-failure-archive-git-proof-01/commands/sparse-before/stderr', 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'size': 0}, {'identity': {'ctime_ns': 1789808887347057812, 'dev': 16777229, 'ino': 1056124542, 'mode': 33152, 'mtime_ns': 1789808887347057812, 'nlink': 1, 'size': 5}, 'path': '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/.work/published-failure-archive-git-proof-01/commands/sparse-before/stdout', 'sha256': 'a17fcf0a2f50e2d495e4f90ce263410edc183add6c62699a2facbccf60410f74', 'size': 5}, {'identity': {'ctime_ns': 1789808887326173850, 'dev': 16777229, 'ino': 1056124534, 'mode': 33152, 'mtime_ns': 1789808887326173850, 'nlink': 1, 'size': 7988}, 'path': '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/.work/published-failure-archive-git-proof-01/source.py', 'sha256': '8b758427668a1fd6fc26aae802164fa477b5354c77243627762dd567d6be08e7', 'size': 7988}]}
START = time.monotonic()
READ = 0


def check(ok, message):
    if not ok:
        raise RuntimeError(message)


def guard():
    check(time.monotonic()-START <= 300 and shutil.disk_usage(A).free >= 9*2**30, 'finite read-only time and live floor')


def count(size):
    global READ
    guard(); READ += size
    check(READ <= 512*2**20, 'bounded total audit reads')


def identity(path):
    s = Path(path).lstat()
    return {key: getattr(s, 'st_'+key) for key in FIELDS}


def raw(path, row=None):
    path = Path(path); before = identity(path)
    check(path.resolve(strict=True) == path and stat.S_ISREG(before['mode']) and before['size'] <= 64*2**20, 'ordinary bounded audit input')
    if row is not None:
        check(before == row['identity'], 'selected input identity')
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK), 'rb') as stream:
        held = os.fstat(stream.fileno())
        check({k: getattr(held, 'st_'+k) for k in FIELDS} == before, 'opened audit input')
        data = stream.read(64*2**20+1); count(len(data))
        held = os.fstat(stream.fileno())
        check({k: getattr(held, 'st_'+k) for k in FIELDS} == before, 'held audit input unchanged')
    check(len(data) == before['size'] and path.resolve(strict=True) == path and identity(path) == before, 'stable complete audit input')
    if row is not None:
        check(len(data) == row['size'] and hashlib.sha256(data).hexdigest() == row['sha256'], 'selected source bytes')
    return data


def digest(path):
    return hashlib.sha256(raw(path)).hexdigest()


def read(path):
    return json.loads(raw(path))


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def membership(path):
    path = Path(path)
    check(path.resolve(strict=True) == path and path.is_dir(), 'ordinary closed evidence root')
    found = []; total = 0
    for root, dirs, files in os.walk(path, followlinks=False, onerror=lambda e: (_ for _ in ()).throw(e)):
        guard()
        for name in dirs+files:
            p = Path(root)/name; s = p.lstat(); total += 1
            check(total <= 1024 and (stat.S_ISDIR(s.st_mode) or stat.S_ISREG(s.st_mode)), 'bounded closed ordinary membership')
            if stat.S_ISREG(s.st_mode):
                found.append(str(p.relative_to(path)))
    return sorted(found)


def previous_audit():
    # This saved failure is distinct from the archive01 schema failure.
    for name, row in PREVIOUS_AUDIT_FILES.items():
        raw(name, row)
    old = A/'.work/hash-driver-success-retention-audit-execution-02'
    row = read(old/'record.json')
    check(row['status']=='finished' and type(row['returncode']) is int and row['returncode']==1
          and row['pid']==82609 and row['parent_pid']==80569 and row['cwd']==str(A) and row['environment']==ENVIRONMENT
          and row['execution_source_sha256']==PREVIOUS_AUDIT_FILES[str(H/'execute_verify.py')]['sha256']
          and row['source_hashes'][str(H/'verify.py')]==PREVIOUS_AUDIT_FILES[str(H/'verify.py')]['sha256']
          and row['command']==[str(PYTHON),'-B',str(H/'verify.py'),'--receipt-sha256',
              'a53d103bb9b4072699870502506ecf8776a7d2f2f83364c349c691235c9c4e1b','--execution-record-sha256',
              'e6eabc1215529605254a42fa5ffe0068200e2681b1fcd2054f52147db8f53237','--summary-sha256',
              '0a33a5b5eafa2224f325452c3518c0a3a547e23aec718c410f2ae877d45b2cb0','--canonical-fd','3']
          and row['started_at']<=row['admitted_at']<=row['child_started_at']<=row['observation_finished_at']<=row['finished_at']
          and row['execution_error']=="RuntimeError('actual archive audit failed; preserve evidence')"
          and 'canonical_released_at' not in row, 'exact closed original archive-audit02 failure')
    check(raw(old/'stdout')==b'' and raw(old/'stderr').decode('utf-8').endswith(
              "FileNotFoundError: [Errno 2] No such file or directory: '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/hir-options-hash-driver-failure-01/evidence.tar.gz'\n")
          and all(row[k+'_sha256']==PREVIOUS_AUDIT_FILES[str(old/k)]['sha256'] for k in ['stdout','stderr']), 'original missing working-copy failure raw')
    for source, name in [(H/'verify.py','audit.py'),(H/'archive.py','archive.py'),(H/'execute.py','archive-execution.py'),(PROPOSAL,'proposal.json'),(OWNED,'owned_stage.py'),(H/'execute_verify.py','execution.py')]:
        check(raw(source)==raw(old/'source'/name),'retained actual failed-audit source capsule')
    absent=A/'.work/hash-driver-success-retention-independent-verification-02.json'
    check(not absent.exists() and not absent.is_symlink(),'failed audit02 did not publish qualification')
    return dict(status='retained-closed-read-only-audit-failure',record=dict(path=str(old/'record.json'),sha256=PREVIOUS_AUDIT_FILES[str(old/'record.json')]['sha256']),
                files=PREVIOUS_AUDIT_FILES,actual_audit_children=1,archive_processing_children=0,workload_children=0,
                audit_report_absent=True,canonical_release_timestamp_recorded=False,
                meaning='Original auditor required a current inode for the now sparse-omitted historical archive. Original audit02 failure remains unchanged.')


def publication_transition(ref):
    # The old physical identity remains historical. This proves recovery of the
    # same compressed bytes from the published immutable Git object instead.
    binding = GIT_PUBLICATION_PROOF; root = R/'.work/published-failure-archive-git-proof-01'
    report = json.loads(raw(binding['report']['path'], binding['report']))
    source = raw(binding['source']['path'], binding['source'])
    check(report['schema']=='published-sparse-archive-git-proof-v1' and report['status']=='verified'
          and report['parent_pid']==11309 and report['parent_parent_pid']==80990 and report['cwd']==str(R)
          and report['started_at']<=report['finished_at']
          and encoded(report['source'])==encoded(binding['source'])
          and encoded(report['files'])==encoded(binding['files'])
          and type(report['actual_git_children']) is int and report['actual_git_children']==11
          and report['all_children_closed'] is report['full_git_blob_read'] is True
          and report['signals_sent']==[] and report['blob_stdout_retained'] is report['original_inode_claimed'] is False,
          'exact actual bounded Git proof owner/source/report')
    publication=dict(commit='075141b3d11a5172ab59ecbdeface0d340fac016',
        relative_path='results/hir-options-hash-driver-failure-01/evidence.tar.gz',path=FAILURE_ARCHIVE_PUBLICATION['path'],
        git_blob='09c50202c9b3241d7c620053cd47c3f283136c88',
        sha256='ff7870ea202cd33b7c91e2afe8b3784780fee1d9239a7df6394eaf0560417216',bytes=13134758)
    check(encoded(report['publication'])==encoded(publication)
          and ref['path']==publication['path'] and ref['sha256']==publication['sha256'] and ref['size']==publication['bytes']
          and encoded(report['working_copy'])==encoded(dict(absent_before=True,absent_after=True,sparse_enabled=True,index_skip_worktree=True,restored=False)),
          'explicit exact historical publication transition')
    path=Path(publication['path']); check(not path.exists() and not path.is_symlink(), 'sparse archive must remain absent; no invented old inode')
    check(encoded(report['retained_source'])==encoded(next(r for r in binding['files'] if r['path']==str(root/'source.py')))
          and raw(root/'source.py',report['retained_source'])==source,'full executed Git proof source copy')
    rows={r['path']:r for r in binding['files']}
    check(len(rows)==len(binding['files'])==44,'exact retained Git command/source closure')
    for name,row in rows.items():
        check(Path(name).is_relative_to(root),'proof file outside exact evidence root')
        raw(name,row)
    relative=publication['relative_path'];blob=publication['git_blob']
    commands=[('head-before',['rev-parse','HEAD']),('sparse-before',['config','--get','core.sparseCheckout']),
              ('entry-before',['ls-files','-t','--',relative]),('published-blob',['rev-parse',publication['commit']+':'+relative]),
              ('current-blob',['rev-parse','HEAD:'+relative]),('blob-type',['cat-file','-t',blob]),
              ('blob-size',['cat-file','-s',blob]),('blob-content',['cat-file','blob',blob]),
              ('head-after',['rev-parse','HEAD']),('sparse-after',['config','--get','core.sparseCheckout']),
              ('entry-after',['ls-files','-t','--',relative])]
    check(set(report['commands'])=={name for name,_ in commands}
          and set(report['text_outputs'])=={name for name,_ in commands if name!='blob-content'},'all11 exact actual Git commands')
    environment=dict(HOME='/Users/danluu',PATH='/usr/bin:/bin:/usr/sbin:/sbin',LANG='C',LC_ALL='C',TZ='UTC',GIT_OPTIONAL_LOCKS='0',GIT_TERMINAL_PROMPT='0')
    wanted={'.','source.py','report.json','commands'};previous=report['started_at']
    for name,args in commands:
        directory=root/'commands'/name; row=report['commands'][name]
        check(encoded(read(directory/'record.json'))==encoded(row)
              and encoded(read(directory/'launch.json'))==encoded({k:row[k] for k in ['argv','cwd','environment','parent_pid','child_pid','started_at','command_timeout_seconds','signals_sent']})
              and row['argv']==['/usr/bin/git',*args] and row['cwd']==str(R) and encoded(row['environment'])==encoded(environment)
              and row['parent_pid']==report['parent_pid'] and type(row['child_pid']) is int and row['child_pid']>0
              and row['status']=='closed' and type(row['returncode']) is int and row['returncode']==0
              and previous<=row['started_at']<=row['finished_at']<=report['finished_at'] and row['finished_at']-row['started_at']<=30
              and row['command_timeout_seconds']==30 and row['signals_sent']==[]
              and row['full_stdout_eof'] is row['full_stderr_eof'] is True,'actual Git argv/env/PID/ordered closure/EOF')
        previous=row['finished_at'];streams=row['streams'];check(set(streams)=={'stdout','stderr'},'complete Git stream metadata')
        for channel in ['stdout','stderr']:
            value=streams[channel];check(type(value['bytes']) is int and value['bytes']>=0,'typed Git stream length')
            if name=='blob-content' and channel=='stdout':
                check(encoded(value)==encoded(dict(bytes=publication['bytes'],sha256=publication['sha256'],retained=False))
                      and not (directory/'stdout').exists() and not (directory/'stdout').is_symlink(), 'complete hashed blob stream without restoration or retained payload')
            else:
                data=raw(directory/channel,rows[str(directory/channel)])
                check(value['retained'] is True and len(data)==value['bytes']<=65536 and hashlib.sha256(data).hexdigest()==value['sha256'],'full retained Git raw stream')
                if channel=='stderr':check(data==b'','clean actual Git stderr')
                else:check(data.decode('utf-8')==report['text_outputs'][name],'actual Git text output association')
        base='commands/'+name;wanted.update([base,base+'/launch.json',base+'/record.json',base+'/stderr'])
        if name!='blob-content':wanted.add(base+'/stdout')
    text=report['text_outputs']
    check(re.fullmatch('[0-9a-f]{40}',report['head']) is not None
          and text['head-before']==text['head-after']==report['head']+'\n'
          and text['sparse-before']==text['sparse-after']=='true\n'
          and text['entry-before']==text['entry-after']=='S '+relative+'\n'
          and text['published-blob']==text['current-blob']==blob+'\n'
          and text['blob-type']=='blob\n' and text['blob-size']==str(publication['bytes'])+'\n', 'exact committed/current Git object and sparse omission observations')
    check(set(tree_stamps(root))==wanted,'complete closed Git proof membership')
    check(raw(binding['source']['path'],binding['source'])==source
          and encoded(json.loads(raw(binding['report']['path'],binding['report'])))==encoded(report)
          and not path.exists() and not path.is_symlink(),'publication proof and honest absence stable')
    return True


def tree_stamps(root):
    root = Path(root); check(root.resolve(strict=True) == root and root.is_dir(), 'ordinary original tree')
    result = {}
    for parent, dirs, files in os.walk(root, followlinks=False, onerror=lambda e: (_ for _ in ()).throw(e)):
        guard()
        for name in ['.', *dirs, *files]:
            p = Path(parent) if name == '.' else Path(parent)/name
            row = identity(p)
            check(p.resolve(strict=True) == p and (stat.S_ISREG(row['mode']) or stat.S_ISDIR(row['mode'])), 'ordinary original tree entry')
            result[str(p.relative_to(root))] = dict(kind='directory' if stat.S_ISDIR(row['mode']) else 'file', identity=row)
            check(len(result) <= 1024, 'finite original tree')
    return dict(sorted(result.items()))


def verify_external(proposal, original_manifest, rows):
    def doc(path): return json.loads(raw(path, rows[str(path)]))
    catalogs = {}
    for role, ref in proposal['prior_archives'].items():
        docs = {}
        for name in ['manifest', 'summary', 'independent_audit']:
            row = rows[ref[name]['path']]
            check(encoded({k:row[k] for k in ['sha256','size','identity']}) == encoded({k:ref[name][k] for k in ['sha256','size','identity']}), 'exact archived proof row')
            docs[name] = doc(row['path'])
        m, summary, audit = (docs[k] for k in ['manifest','summary','independent_audit'])
        check(summary['status'] == 'passed' and audit['status'] == 'verified'
              and summary['archive']['sha256'] == ref['sha256'] and summary['archive']['bytes'] == ref['size']
              and summary['manifest_sha256'] == audit['manifest_sha256'] == ref['manifest']['sha256']
              and audit['summary_sha256'] == ref['summary']['sha256'], 'closed prior archive metadata association')
        if role == 'failed_driver01':
            check(audit['archive']['sha256'] == ref['sha256'] and audit['archive']['full_gzip_eof_crc'] is audit['archive']['full_member_readback'] is True
                  and audit['original_status'] == 'failed' and audit['hash_driver_qualified'] is False
                  and m['proposal_sha256'] == summary['proposal_sha256'] == audit['proposal_sha256']
                  and len(m['members']) == audit['selected_files'] == 168 and publication_transition(ref) is True, 'failed archive retains failure status and complete EOF proof')
            receipt, execution, audit_execution = [doc(ref[k]['path']) for k in ['receipt','execution_record','audit_execution_record']]
            check(receipt['status'] == 'passed' and execution['status'] == audit_execution['status'] == 'finished'
                  and type(execution['returncode']) is type(audit_execution['returncode']) is int and execution['returncode'] == audit_execution['returncode'] == 0
                  and receipt['archive_sha256'] == ref['sha256'] and receipt['summary_sha256'] == ref['summary']['sha256']
                  and audit['receipt_sha256'] == ref['receipt']['sha256'] and audit['execution_record_sha256'] == ref['execution_record']['sha256']
                  and audit_execution['result_sha256'] == ref['independent_audit']['sha256']
                  and execution['finished_at'] <= execution['canonical_released_at'] and audit_execution['finished_at'] <= audit_execution['canonical_released_at'], 'actual failed archive processing and independent audit both closed')
            catalogs[role] = {r['member']:dict(bytes=r['size'],sha256=r['sha256']) for r in m['members']}
            check(len(catalogs[role]) == 168, 'unique failed archive members')
        else:
            check(role in ['beta','native'] and audit['archive_sha256'] == ref['sha256']
                  and audit['full_gzip_eof_crc'] is audit['full_member_readback'] is True
                  and type(ref['git_blob']) is str and re.fullmatch('[0-9a-f]{40}',ref['git_blob']) is not None, 'published prior full-EOF qualification')
            catalogs[role] = m

    def resolve(ref, path, expected_sha, size):
        check(ref['logical_member'] == path.lstrip('/') and ref['sha256'] == expected_sha and ref['size'] == size
              and ref['archive_sha256'] == proposal['prior_archives'][ref['archive']]['sha256'], 'original-to-archive byte association')
        current = ref['logical_member']; chain = []; catalog = catalogs[ref['archive']]
        while True:
            check(current in catalog and current not in chain and len(chain) < 256, 'finite archive alias chain')
            chain.append(current); row = catalog[current]
            check(row['sha256'] == expected_sha and row['bytes'] == size, 'complete alias byte association')
            if 'linkname' not in row: break
            current = row['linkname']
        check(chain == ref['alias_chain'] and current == ref['physical_member'], 'exact complete physical archive member')

    snapshots = proposal['snapshots']; seen = set()
    for ref in snapshots['reused_archive_associations']:
        source = ref['source']; key = ref['logical_sha256']
        check(key not in seen and key == source['blob']['logical_sha256'] and ref['logical_bytes'] == source['blob']['logical_bytes']
              and encoded(source) == encoded(original_manifest['reuse'][key])
              and original_manifest['storage'][key] == dict(kind='reused',path=source['path']), 'exact unique reused blob metadata')
        seen.add(key); resolve(ref['recovery'],source['path'],source['blob']['sha256'],source['blob']['compressed_bytes'])
    check(len(seen) == snapshots['reused_blobs'] == 93 and seen == set(original_manifest['reuse']), 'all93 reused physical blobs')
    expected_logical = [dict(source=p,sha256=r['sha256'],size=r['size'],physical_blob=r['path'],storage=original_manifest['storage'][r['sha256']]['kind']) for p,r in sorted(original_manifest['files'].items())]
    check(encoded(expected_logical) == encoded(snapshots['logical_alias_map']), 'all158 logical aliases retained')
    base = snapshots['compact_base_archive_association']; compact = doc(R/'experiments/hir-options-hash-driver-stage-03/inputs.json')
    check(encoded(base['reference']) == encoded(compact['file_table_base']), 'exact native03 file table base')
    resolve(base['archived'],base['reference']['path'],base['reference']['sha256'],compact['files'][base['reference']['path']]['size'])
    wire = doc(R/'experiments/hir-options-hash-driver-stage-03/plan.json'); external = snapshots['external_metadata_plan_recovery']
    check(encoded(wire['reference']) == encoded(external['reference']) and len(external['steps']) == 2, 'exact external metadata plan recovery')
    refs = [r for r in snapshots['reused_archive_associations'] if r['logical_sha256'] == external['reference']['sha256']]
    check(len(refs) == 1, 'one external metadata physical witness')
    ref=refs[0]; first,last=external['steps']
    check(first['operation'] == 'read-authenticated-archive-member' and first['archive'] == ref['recovery']['archive'] == 'failed_driver01'
          and first['archive_sha256'] == ref['recovery']['archive_sha256'] and first['member'] == first['physical_member'] == ref['recovery']['physical_member']
          and first['alias_chain'] == ref['recovery']['alias_chain'] and first['sha256'] == ref['source']['blob']['sha256'] and first['bytes'] == ref['source']['blob']['compressed_bytes']
          and encoded(last) == encoded(dict(operation='bounded-gzip-full-eof-crc-and-sha256',logical_sha256=external['reference']['sha256'],logical_bytes=external['logical_bytes']))
          and last['logical_bytes'] == ref['logical_bytes'], 'complete authenticated outer archive member and inner gzip route')
    check(not proposal['missing_recovery_references'] and not proposal['forthcoming_archives'], 'no path-only pending recovery reference')
    return dict(reused_blobs=93,new_blobs=54,logical_aliases=158,referenced_native_base=True,referenced_external_metadata_plan=True,
                prior_archive_payloads_reread=False, reference_semantics='Full original published manifest and closed full-EOF audit associations. Prior archive payloads and live provider bytes are not reread or duplicated.')


def qualified_history(proposal, rows):
    work=R/'.work/hir-options-hash-driver-02'; source=R/'experiments/hir-options-hash-driver-stage-03'
    def doc(path):return json.loads(raw(path,rows[str(path)]))
    def h(path):return rows[str(path)]['sha256']
    audit_path=R/'.work/hir-options-hash-driver-independent-verification-02.json';audit=doc(audit_path);terminal=doc(work/'receipt.json');result=doc(work/'result.json');wire=doc(source/'plan.json');launch=doc(source/'launch.json')
    check(h(audit_path) == proposal['history']['audit']['sha256'] == '9540ad45b5423f793e323bac31d593f1c1b030fe0e1dd5fc3665565277885ebb'
          and audit['status']=='verified' and terminal['status']=='passed-awaiting-independent-audit' and result['status']=='hash-driver-observations-passed-awaiting-independent-audit', 'exact independently qualified driver02')
    check(audit['receipt_sha256']==h(work/'receipt.json')==proposal['history']['receipt_sha256']
          and audit['result_sha256']==terminal['result_sha256']==h(work/'result.json')==proposal['history']['result_sha256']
          and audit['launch_sha256']==h(source/'launch.json') and audit['inputs_sha256']==terminal['inputs_sha256']==launch['inputs_sha256']==h(source/'inputs.json')
          and audit['snapshot_plan_sha256']==terminal['snapshot_plan_sha256']==launch['snapshot_plan_sha256']==h(source/'snapshot-plan.json')
          and launch['plan_sha256']==h(source/'plan.json'), 'qualified owner complete packet association')
    for key,value in dict(actual_children=3,compilation_count=1,driver_process_count=2,contexts_per_process=8,stdout_records_per_process=9,historical_failed_compiler_children=1,total_actual_hash_children=4).items():
        check(type(audit[key]) is int and audit[key]==value,'qualified history counts')
    check(audit['hash_driver_qualified'] is audit['full_frozen_byte_rehash'] is audit['full_provider_inventories'] is audit['static_and_actual_loaders_verified'] is True
          and all(audit[k] is False for k in ['application_qualified','performance_measurement','runtime_installation']), 'qualification scope remains precise')
    check(encoded(audit['metadata_plan_reference'])==encoded(wire['reference'])
          and all(encoded(audit['continuation_controls'])==encoded(v['continuation_controls']) and encoded(audit['failed_predecessor']['owner'])==encoded(v['failed_driver']) for v in [terminal,result,wire['remainder']])
          and audit['failed_predecessor']['actual_children']==1 and audit['failed_predecessor']['qualified_children']==0, 'prior failure stays separate')
    outer_root=R/'.work/experiments/hir-options-hash-driver-supervisor-02';launch_root=R/'.work/hash-driver-launch-execution-02';audit_root=R/'.work/hash-driver-independent-verification-execution-02'
    outer=doc(outer_root/'status.json');dispatch=doc(launch_root/'record.json');execution=doc(audit_root/'record.json');handoff=doc(launch_root/'stdout')
    check(outer['status']=='finished' and outer['returncode']==0 and outer['child_pid']==terminal['pid'] and outer['supervisor_pid']==terminal['parent_pid']
          and outer['command']==launch['command'][6:] and outer['cwd']==str(R) and outer['plan_sha256']==h(outer_root/'plan.json') and outer['log_sha256']==h(outer_root/'command.log')
          and outer['child_started_at']<=terminal['started_at']<=terminal['admitted_at']<=terminal['finished_at']<=outer['finished_at'], 'actual driver outer closure')
    check(dispatch['status']=='terminal-observed' and dispatch['returncode']==dispatch['launcher_returncode']==0 and dispatch['outer_sha256']==h(outer_root/'status.json')
          and dispatch['launch_sha256']==h(source/'launch.json') and dispatch['launcher_source_path']==str(source/'launch.py') and dispatch['launcher_source_sha256']==h(source/'launch.py')
          and dispatch['command']==launch['command'] and dispatch['environment']==launch['environment'] and dispatch['cwd']==str(R) and dispatch['controller_pid']==terminal['pid']
          and dispatch['started_at']<=dispatch['launcher_finished_at']<=dispatch['finished_at'] and outer['finished_at']<=dispatch['terminal_observed_at']<=dispatch['finished_at']
          and encoded(handoff)==encoded(dispatch['supervisor_handoff']) and handoff['directory']==str(outer_root) and handoff['supervisor_pid']==dispatch['supervisor_pid']==outer['supervisor_pid'], 'actual driver launcher closure')
    for stream in ['stdout','stderr']:check(dispatch[stream+'_sha256']==h(launch_root/stream) and execution[stream+'_sha256']==h(audit_root/stream),'original launcher and auditor raw')
    check(execution['status']=='finished' and execution['returncode']==0 and execution['report_sha256']==h(audit_path)
          and execution['source_sha256']==audit['verifier_sha256']==h(source/'verify.py') and execution['finished_at']<=execution['canonical_released_at']
          and execution['verified_output']==doc(audit_root/'stdout') and execution['actual_closure']=={str(p):h(p) for p in [work/'receipt.json',work/'result.json',outer_root/'status.json',launch_root/'record.json']},'independent driver audit actual closure')
    wanted=wire['remainder']['children'];compiled=doc(work/'compile/receipt.json');pids=[]
    check(len(wanted)==3 and len(result['processes'])==len(audit['processes'])==2 and compiled['status']=='finished'
          and type(compiled['returncode']) is int and compiled['returncode']==0 and compiled['expected']==[0] and h(work/'compile/receipt.json')==result['compile_receipt_sha256']
          and terminal['admitted_at']<=compiled['started_at']<=compiled['finished_at']<=terminal['finished_at'],'actual compile receipt schema')
    previous=compiled['finished_at']
    for i,mode in enumerate(['compile','serial','parallel']):
        row=doc(work/mode/'receipt.json');pids.append(row['pid']);command=wanted[i]
        check(row['supervisor_pid']==terminal['pid'] and row['parent_pid']==terminal['parent_pid'] and encoded(row['command'])==encoded(command['argv'])
              and row['cwd']==command['cwd'] and encoded(row['environment'])==encoded(command['environment']), 'exact retained child recipe and owner')
        for stream in ['stdout','stderr']:check(row[stream+'_sha256']==h(work/mode/stream),'exact original child raw')
        if i==0:continue
        ref=result['processes'][i-1];wait=row['wait'];proof=doc(work/mode/'validated-readback.json')
        check(row['status']=='passed' and row['mode']==ref['mode']==mode and row['pid']==ref['pid'] and h(work/mode/'receipt.json')==ref['receipt_sha256']
              and previous<=row['started_at']<=row['controller_finished_at']<=row['child_finished_at']<=terminal['finished_at'] and row['errors']==[]
              and row['child_may_be_live'] is row['probe_may_be_live'] is row['real_driver_qualification'] is False,'actual driver observation receipt')
        check(wait['status']=='exited' and type(wait['returncode']) is int and wait['returncode']==0 and wait['reason'] is None and wait['errors']==[] and wait['child_may_be_live'] is False,'nested driver wait closure')
        check(h(work/mode/'validated-readback.json')==ref['readback_sha256'] and encoded(proof)==encoded(audit['processes'][i-1])
              and proof['mode']==mode and proof['pid']==row['pid'] and proof['observations']['contexts']==8
              and proof['observations']['stdout_sha256']==row['stdout_sha256'] and proof['loader']['stderr_sha256']==row['stderr_sha256'], 'independently qualified saved process readback')
        previous=row['child_finished_at']
    check(pids==audit['child_pids'],'actual three child identities')
    for name,row in audit['artifacts'].items():
        if row['kind']=='file':
            path=X/'.work/hir-options-hash-compiler-01/hash-driver-02'/name
            check(h(path)==row['sha256'] and rows[str(path)]['size']==row['stamp'][3],'full executed artifact retained')
    for ref in audit['driver_source_derivation'].values():
        if isinstance(ref,dict) and 'path' in ref:check(h(ref['path'])==ref['sha256'],'retained driver source derivation')
    return audit


def archive_members(selected, expected_sha):
    path = D/'evidence.tar.gz'; before = identity(path)
    check(path.resolve(strict=True) == path and stat.S_ISREG(before['mode']) and before['size'] <= 16*2**20, 'exact bounded ordinary archive')
    check(digest(path) == expected_sha, 'actual summary authenticates compressed bytes before parsing')
    expanded = 0
    # Establish a finite complete gzip stream before decoding tar metadata.
    with gzip.open(path, 'rb') as stream:
        while block := stream.read(2**20):
            count(len(block)); expanded += len(block)
            check(expanded <= 40*2**20, 'finite full expanded gzip stream')
    check(identity(path) == before, 'archive changed during bounded preliminary EOF check')
    class BoundedTarReader:
        def __init__(self, stream):
            self.stream = stream
            self.total = 0
        def read(self, size):
            check(type(size) is int and 0 <= size <= 2**20, 'bounded tar decoder input request')
            block = self.stream.read(size)
            count(len(block)); self.total += len(block)
            check(self.total <= 40*2**20, 'finite tar metadata and payload expansion')
            return block
    count_members = 0; logical = 0
    with gzip.open(path, 'rb') as source:
        bounded = BoundedTarReader(source)
        with tarfile.open(fileobj=bounded, mode='r|') as archive:
            for member in archive:
                guard()
                check(count_members < 241, 'bounded actual archive members')
                row = selected[count_members]
                check(member.name == row['member'] and member.isfile() and member.size == row['size']
                      and member.mode == 0o644 and member.mtime == member.uid == member.gid == 0
                      and member.uname == member.gname == member.linkname == '', 'exact deterministic ordered ordinary member')
                stream = archive.extractfile(member); h = hashlib.sha256(); size = 0
                while block := stream.read(2**20):
                    guard(); size += len(block); h.update(block)
                check(size == row['size'] and h.hexdigest() == row['sha256'], 'independent complete archive member hash')
                logical += size; count_members += 1
            while block := archive.fileobj.read(2**20):
                check(not any(block), 'nonzero tar trailer')
        check(source.read(1) == b'' and bounded.total == expanded, 'complete independent bounded tar and gzip EOF')
    check(count_members == 241 and logical == 13880266 and expanded >= logical and identity(path) == before
          and path.resolve(strict=True) == path, 'complete stable archive and full gzip EOF')
    return dict(members=count_members, logical_bytes=logical, expanded_bytes=expanded,
                bytes=before['size'], sha256=digest(path), full_member_readback=True, full_gzip_eof_crc=True)


def main(args):
    check(Path.cwd() == A and Path(sys.executable).resolve() == PYTHON and sys.dont_write_bytecode and not sys.flags.optimize,
          'fixed independent audit owner and Python')
    check(not OUT.exists() and not OUT.is_symlink(), 'fresh independent audit result')
    resource.setrlimit(resource.RLIMIT_CPU, (180, 180)); resource.setrlimit(resource.RLIMIT_FSIZE, (2*2**20, 2*2**20))
    opened = os.fstat(args.canonical_fd); current = LOCK.stat()
    check((opened.st_dev, opened.st_ino) == (current.st_dev, current.st_ino) and LOCK.resolve(strict=True) == LOCK, 'held canonical descriptor')
    fcntl.flock(args.canonical_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    with LOCK.open('r+') as competing:
        try:
            fcntl.flock(competing, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            pass
        else:
            raise RuntimeError('canonical descriptor was not held')
    started = time.time(); guard()
    prior_audit = previous_audit()
    for value in [args.receipt_sha256, args.execution_record_sha256, args.summary_sha256]:
        check(re.fullmatch('[0-9a-f]{64}', value) is not None, 'explicit actual closure digest')
    check(digest(W/'receipt.json') == args.receipt_sha256 and digest(E/'record.json') == args.execution_record_sha256
          and digest(D/'summary.json') == args.summary_sha256, 'exact actual closed archive bindings')
    check(digest(H/'archive.py') == ENGINE_SHA and digest(H/'execute.py') == WRAPPER_SHA and digest(OWNED) == OWNED_SHA
          and digest(PROPOSAL) == PROPOSAL_SHA and raw(PROPOSAL) == raw(D/'proposal.json'), 'reviewed source and exact retained proposal')
    proposal = read(PROPOSAL); selected = proposal['files']; rows = {r['path']: r for r in selected}
    check(len(rows) == len(selected) == 241 and sum(r['size'] for r in selected) == 13880266, 'exact proposal census')
    check(len(proposal['complete_scoped_directories']) == 10 and proposal['archive_source'] == str(R/'experiments/hash-driver-success-evidence-01')
          and proposal['work'] == str(W) and proposal['destination'] == str(D), 'exact scope owner and ten trees')
    for row in selected:
        raw(row['path'], row)
    for root, expected in proposal['complete_scoped_directories'].items():
        check(encoded(tree_stamps(root)) == encoded(expected), 'complete closed original tree identities')
    terminal = read(W/'receipt.json'); execution = read(E/'record.json'); summary = read(D/'summary.json'); manifest = read(D/'manifest.json')
    check(execution['status'] == 'finished' and execution['returncode'] == 0 and execution['result_sha256'] == args.summary_sha256
          and execution['execution_source_sha256'] == WRAPPER_SHA and execution['source_hashes'] == {str(H/'archive.py'): ENGINE_SHA, str(OWNED): OWNED_SHA, str(PROPOSAL): PROPOSAL_SHA}
          and execution['cwd'] == str(R) and execution['environment'] == ENVIRONMENT
          and execution['command'][:3] == [str(PYTHON), '-B', str(H/'archive.py')]
          and len(execution['command']) == 5 and execution['command'][3] == '--canonical-fd'
          and execution['command'][4].isdigit(), 'actual explicit archive child owner and argv')
    check(terminal['status'] == summary['status'] == 'passed' and terminal['children'] == []
          and terminal['workload_children'] == summary['workload_children'] == 0
          and terminal['pid'] == execution['pid'] and terminal['parent_pid'] == execution['parent_pid']
          and execution['started_at'] <= execution['admitted_at'] <= terminal['started_at'] <= terminal['finished_at'] <= execution['finished_at']
          <= execution['canonical_released_at'] <= started and not execution.get('may_be_live')
          and not execution.get('execution_error') and not execution.get('initial_child_publication_error'), 'closed actual archive lifetime and release')
    check(execution['canonical_lock'] == str(LOCK) and execution['wait_seconds'] == 600
          and execution['maximum_child_cpu_seconds'] == 300 and execution['maximum_child_read_seconds'] == 600
          and execution['maximum_observation_seconds'] == 650 and execution['maximum_file_bytes'] == 16*2**20
          and execution['capacity'] == dict(entry_bytes=9*2**30+64*2**20, stop_gib=9, floor_gib=8, reservation_bytes=64*2**20)
          and execution['entry_free_bytes'] >= 9*2**30+64*2**20 and execution['free_bytes_before'] >= 9*2**30+64*2**20
          and execution['free_bytes_after'] >= 9*2**30 and all(r['free_bytes'] >= 9*2**30 for r in execution['disk_samples']), 'unchanged actual capacity gates')
    for name in ['stdout', 'stderr']:
        check(digest(E/name) == execution[name+'_sha256'], 'actual archive raw association')
    check(not raw(E/'stderr'), 'clean archive child stderr')
    check(read(E/'stdout') == dict(status='passed', receipt=str(W/'receipt.json'), receipt_sha256=args.receipt_sha256,
                                  archive_sha256=terminal['archive_sha256'], workload_children=0), 'actual archive child output')
    for original, name in [(H/'archive.py', 'archive.py'), (PROPOSAL, 'proposal.json'), (OWNED, 'owned_stage.py'), (H/'execute.py', 'execution.py')]:
        check(raw(original) == raw(E/'source'/name), 'full retained source capsule')
    check(set(tree_stamps(E)) == {'.','source','record.json','stderr','stdout','source/archive.py','source/proposal.json','source/owned_stage.py','source/execution.py'}
          and set(tree_stamps(W)) == {'.','receipt.json'} and set(tree_stamps(D)) == {'.','evidence.tar.gz','manifest.json','previous-attempt.json','proposal.json','summary.json'}, 'complete current retention output membership including directories')
    check(encoded(summary['limits']) == encoded(proposal['limits']) == encoded(dict(maximum_members=512,maximum_file_bytes=8*2**20,maximum_logical_bytes=32*2**20,maximum_physical_bytes=32*2**20,maximum_compressed_bytes=16*2**20,maximum_expanded_tar_bytes=40*2**20,maximum_metadata_bytes=2*2**20)), 'unchanged finite archive bounds')
    expected_manifest = dict(policy='closed-qualified-driver-evidence-v1', proposal_sha256=PROPOSAL_SHA,
                             members=selected, original_history=proposal['history'], prior_archives=proposal['prior_archives'],
                             snapshots=proposal['snapshots'], complete_scoped_directories=proposal['complete_scoped_directories'],
                             exclusions=proposal['exclusions'], recovery_requirements=proposal['recovery_requirements'])
    check(encoded(manifest) == encoded(expected_manifest) and terminal['manifest_sha256'] == summary['manifest_sha256'] == digest(D/'manifest.json')
          and terminal['summary_sha256'] == args.summary_sha256 and terminal['engine_sha256'] == ENGINE_SHA
          and terminal['proposal_sha256'] == summary['proposal_sha256'] == PROPOSAL_SHA, 'complete manifest/source/summary association')
    previous = read(D/'previous-attempt.json')
    check(set(previous['files']) == set(PREVIOUS_FILES), 'complete retained archive schema-failure scope')
    for name, expected in PREVIOUS_FILES.items():
        row = previous['files'][name]
        check(set(row) == {'sha256', 'size', 'identity', 'utf8'} and {k: row[k] for k in expected} == expected,
              'exact previous failure metadata')
        check(row['utf8'].encode('utf-8') == raw(name, expected), 'lossless previous failure source/raw bytes')
    first = R/'.work/hash-driver-success-retention-execution-01'
    prior = json.loads(previous['files'][str(first/'record.json')]['utf8'])
    old_source=R/'experiments/hash-driver-success-evidence-01'
    check(previous['status']=='retained-pre-output-archive-schema-failure' and previous['actual_archive_processing_children']==1
          and previous['actual_workload_children']==0 and previous['archive_work_created'] is previous['result_created'] is False
          and prior['status']=='finished' and type(prior['returncode']) is int and prior['returncode']==1
          and prior['pid']==41790 and prior['parent_pid']==39778 and prior['environment']==ENVIRONMENT and prior['cwd']==str(R)
          and prior['command'][:4]==[str(PYTHON),'-B',str(old_source/'archive.py'),'--canonical-fd'] and len(prior['command'])==5 and prior['command'][4].isdigit()
          and prior['execution_source_sha256']==PREVIOUS_FILES[str(old_source/'execute.py')]['sha256']
          and prior['source_hashes'][str(old_source/'archive.py')]==PREVIOUS_FILES[str(old_source/'archive.py')]['sha256']
          and prior['source_hashes'][str(PROPOSAL)]==PROPOSAL_SHA
          and prior['started_at']<=prior['admitted_at']<=prior['child_started_at']<=prior['observation_finished_at']<=prior['finished_at']
          and prior['execution_error']=="RuntimeError('actual archive failed; preserve evidence')" and 'canonical_released_at' not in prior,
          'honest original finished schema-failure child; no invented release timestamp')
    check(previous['files'][str(first/'stdout')]['utf8']=='' and previous['files'][str(first/'stderr')]['utf8'].endswith("KeyError: 'returncode'\n")
          and 'validate_history' in previous['files'][str(first/'stderr')]['utf8']
          and all(prior[k+'_sha256']==PREVIOUS_FILES[str(first/k)]['sha256'] for k in ['stdout','stderr']), 'complete original schema-failure raw')
    for original,name in [(old_source/'archive.py','archive.py'),(old_source/'execute.py','execution.py')]:
        check(PREVIOUS_FILES[str(original)]['sha256']==PREVIOUS_FILES[str(first/'source'/name)]['sha256'],'original executed source copies')
    check(PREVIOUS_FILES[str(first/'source/proposal.json')]['sha256']==PROPOSAL_SHA
          and PREVIOUS_FILES[str(first/'source/owned_stage.py')]['sha256']==prior['source_hashes'][str(OWNED)], 'old proposal and owned helper source copies')
    check(terminal['passed_environment'] == summary['passed_environment'] == execution['environment'] == ENVIRONMENT
          and terminal['observed_environment'] == summary['observed_environment'] == {**ENVIRONMENT, **STARTUP_ADDITIONS}
          and terminal['startup_environment_additions'] == summary['startup_environment_additions'] == STARTUP_ADDITIONS,
          'exact passed versus actual startup environment contract')
    check(terminal['previous_attempt_sha256']==summary['previous_attempt_sha256']==digest(D/'previous-attempt.json')
          and previous['original_execution_record_sha256']==PREVIOUS_FILES[str(first/'record.json')]['sha256']
          and terminal['previous_archive_schema_failure']==dict(record_sha256=previous['original_execution_record_sha256'],actual_archive_processing_children=1), 'complete immutable previous schema-failure binding')
    check(encoded(summary['failure_archive_publication'])==encoded(FAILURE_ARCHIVE_PUBLICATION)
          and proposal['prior_archives']['failed_driver01']['path']==FAILURE_ARCHIVE_PUBLICATION['path']
          and proposal['prior_archives']['failed_driver01']['sha256']==FAILURE_ARCHIVE_PUBLICATION['archive_sha256'], 'additive root-reported publication reference')
    proof = archive_members(selected, summary['archive']['sha256'])
    check(encoded(proof) == encoded(summary['archive']) and terminal['archive_sha256'] == proof['sha256']
          and terminal['member_count'] == 241 and terminal['logical_bytes'] == 13880266
          and terminal['full_member_readback'] is terminal['full_gzip_eof_crc'] is summary['source_bytes_and_identities_unchanged'] is True,
          'independent actual readback equals claimed result')
    owner = qualified_history(proposal,rows)
    check(summary['original_status']==terminal['original_status']=='passed-awaiting-independent-audit'
          and summary['original_independent_audit_status']==terminal['original_independent_audit_status']=='verified','retained original successful qualification')
    for key,value in dict(retained_current_qualified_children=3,retained_compilation_count=1,retained_driver_process_count=2,
                          retained_contexts_per_process=8,retained_historical_failed_compiler_children=1,retained_total_actual_hash_children=4).items():
        check(type(summary[key]) is type(terminal[key]) is int and summary[key]==terminal[key]==value,'precise current and historical retained counts')
    check(summary['hash_driver_qualified'] is terminal['hash_driver_qualified'] is True
          and all(summary[k] is terminal[k] is False for k in ['application_qualified','performance_measurement','runtime_installation']), 'no additional workload scope')
    old_manifest=read(R/'.work/hir-options-hash-driver-02/source-snapshots.json')
    check(digest(R/'.work/hir-options-hash-driver-02/source-snapshots.json') == read(R/'.work/hir-options-hash-driver-02/receipt.json')['source_snapshots_sha256']
          and old_manifest['full_gzip_eof'] is old_manifest['full_logical_readback'] is owner['compressed_snapshots']['full_gzip_eof_crc'] is owner['compressed_snapshots']['full_logical_hashes'] is True
          and set(old_manifest['storage']) == set(old_manifest['blobs']), 'exact original completed snapshot and qualified EOF proof')
    check(len(old_manifest['files'])==owner['compressed_snapshots']['logical_files']==proposal['snapshots']['logical_files']==158 and len(old_manifest['blobs'])==owner['compressed_snapshots']['physical_blobs']==proposal['snapshots']['physical_blobs']==147,'complete original logical and physical selection')
    stored={k:v for k,v in old_manifest['storage'].items() if v['kind']=='stored'}
    check(len(stored)==proposal['snapshots']['new_stored_blobs']==54 and sum(old_manifest['blobs'][k]['compressed_bytes'] for k in stored)==proposal['snapshots']['new_stored_bytes']==690903,'all54 newly stored gzip blobs')
    for key,value in stored.items():
        row=rows[value['path']];blob=old_manifest['blobs'][key]
        check(row['sha256']==blob['sha256'] and row['size']==blob['compressed_bytes'],'full selected new gzip payload')
    references=verify_external(proposal,old_manifest,rows)
    for key in ['reused_blobs','new_blobs','logical_aliases','referenced_native_base','referenced_external_metadata_plan']:
        check(encoded(references[key])==encoded(summary['external_references'][key]),'claimed complete recovery map')
    for row in selected:raw(row['path'],row)
    for root,expected in proposal['complete_scoped_directories'].items():
        check(encoded(tree_stamps(root))==encoded(expected),'ten original complete trees unchanged')
    for path,row in PREVIOUS_FILES.items():raw(path,row)
    check(encoded(previous_audit())==encoded(prior_audit),'original failed-audit evidence unchanged')
    check(publication_transition(proposal['prior_archives']['failed_driver01']) is True,'published recovery proof remains unchanged')
    check(digest(H/'archive.py')==ENGINE_SHA and digest(H/'execute.py')==WRAPPER_SHA and digest(PROPOSAL)==PROPOSAL_SHA
          and digest(D/'manifest.json')==summary['manifest_sha256'] and digest(D/'previous-attempt.json')==summary['previous_attempt_sha256']
          and raw(D/'proposal.json')==raw(PROPOSAL), 'all retained publication/source bytes stable')
    check(digest(W/'receipt.json')==args.receipt_sha256 and digest(E/'record.json')==args.execution_record_sha256
          and digest(D/'summary.json')==args.summary_sha256 and digest(D/'evidence.tar.gz')==proof['sha256'],'actual closure/archive stable through independent audit')
    report=dict(status='verified',pid=os.getpid(),parent_pid=os.getppid(),started_at=started,finished_at=time.time(),
                verifier_sha256=digest(Path(__file__)),proposal_sha256=PROPOSAL_SHA,engine_sha256=ENGINE_SHA,wrapper_sha256=WRAPPER_SHA,
                receipt_sha256=args.receipt_sha256,execution_record_sha256=args.execution_record_sha256,summary_sha256=args.summary_sha256,
                previous_attempt_sha256=summary['previous_attempt_sha256'],manifest_sha256=summary['manifest_sha256'],archive=proof,
                passed_environment=ENVIRONMENT,observed_environment=summary['observed_environment'],
                prior_archive_schema_failure=dict(record_sha256=previous['original_execution_record_sha256'],historical_archive_processing_children=1,historical_workload_children=0),
                complete_selected_source_bytes_and_identities=True,complete_tree_stamps=10,closed_archive_processing_children=1,workload_children=0,
                original_status='passed-awaiting-independent-audit',retained_current_qualified_children=3,retained_compilation_count=1,
                retained_driver_process_count=2,retained_contexts_per_process=8,retained_historical_failed_compiler_children=1,retained_total_actual_hash_children=4,
                hash_driver_qualified=True,application_qualified=False,performance_measurement=False,runtime_installation=False,
                selected_files=241,logical_bytes=13880266,new_gzip_blobs=54,external_references=references,
                original_driver_audit_sha256=proposal['history']['audit']['sha256'],failure_archive_publication=FAILURE_ARCHIVE_PUBLICATION,
                read_bytes=READ,identity_limitation=execution['identity_limitation'],
                previous_archive_audit=prior_audit,git_publication_transition=GIT_PUBLICATION_PROOF)
    data = (json.dumps(report, sort_keys=True, indent=2)+'\n').encode()
    check(len(data) <= 2*2**20, 'bounded independent report')
    with OUT.open('xb') as stream:
        stream.write(data); stream.flush(); os.fsync(stream.fileno())
    print(json.dumps(dict(report=str(OUT), sha256=digest(OUT), status='verified')), flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--receipt-sha256', required=True)
    p.add_argument('--execution-record-sha256', required=True)
    p.add_argument('--summary-sha256', required=True)
    p.add_argument('--canonical-fd', required=True, type=int)
    main(p.parse_args())
