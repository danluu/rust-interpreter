#!/usr/bin/env python3
"""Assemble reviewed B2, then prove its auxiliary loader and real DWARF removal."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import sys
import time

import readmit

OWNER, HERE = readmit.OWNER, readmit.HERE
WORK = OWNER / '.work/beta-auxiliary-assembly-01'
INPUTS = HERE / 'assembly-inputs.json'
PLAN = HERE / 'assembly-plan.json'
require, sha, read, load, identity = readmit.require, readmit.sha, readmit.read, readmit.load, readmit.identity


def object_sections(data):
    """Read ordinary arm64 MH_OBJECT sections, preserving all non-DWARF bytes."""
    require(32 <= len(data) <= 16 * 2**20, 'bounded Mach-O object required')
    magic, cpu, _, kind, commands, command_bytes, _, _ = struct.unpack_from('<IiiIIIII', data)
    require(magic == 0xfeedfacf and cpu == 0x100000c and kind == 1
            and 0 < commands <= 256 and 32 + command_bytes <= len(data), 'arm64 Mach-O object header differs')
    offset = 32
    result = {}
    for _ in range(commands):
        require(offset + 8 <= 32 + command_bytes, 'truncated Mach-O command')
        command, size = struct.unpack_from('<II', data, offset)
        require(size >= 8 and size % 8 == 0 and offset + size <= 32 + command_bytes, 'invalid load-command bounds')
        if command == 0x19:  # LC_SEGMENT_64
            require(size >= 72, 'truncated segment')
            count = struct.unpack_from('<I', data, offset + 64)[0]
            require(size == 72 + count * 80, 'segment section count differs')
            for index in range(count):
                values = struct.unpack_from('<16s16sQQIIIIIIII', data, offset + 72 + index * 80)
                name, segment = (value.split(b'\0', 1)[0].decode('ascii') for value in values[:2])
                length, location, flags = values[3], values[4], values[8]
                zero_fill = flags & 255 in (1, 12, 18)
                require(name and segment and (segment, name) not in result, 'empty/duplicate section identity')
                require(zero_fill or location + length <= len(data), 'section exceeds object bounds')
                payload = None if zero_fill else data[location:location + length]
                result[(segment, name)] = dict(size=length, flags=flags,
                    sha256=None if payload is None else hashlib.sha256(payload).hexdigest())
        offset += size
    require(offset == 32 + command_bytes and result, 'incomplete object command table')
    return result


def check_strip(before, after):
    before_sections, after_sections = object_sections(before), object_sections(after)
    def debug(key):
        return key[0] == '__DWARF' or key[1].startswith(('__debug_', '__zdebug_'))
    prior_debug = {key: value for key, value in before_sections.items() if debug(key)}
    require(('__DWARF', '__debug_info') in prior_debug and any(value['size'] for value in prior_debug.values()),
            'real embedded DWARF required before strip')
    require(not any(debug(key) for key in after_sections), 'debug sections remain after strip')
    native = {key: value for key, value in before_sections.items() if not debug(key)}
    require(native and native == after_sections and len(after) < len(before), 'non-debug sections changed or no strip occurred')
    return dict(debug_sections=[dict(segment=k[0], name=k[1], **v) for k, v in sorted(prior_debug.items())],
                retained_sections=[dict(segment=k[0], name=k[1], **v) for k, v in sorted(native.items())],
                before_bytes=len(before), after_bytes=len(after),
                before_sha256=hashlib.sha256(before).hexdigest(), after_sha256=hashlib.sha256(after).hexdigest())


class Assembly(readmit.Stage):
    def __init__(self, args):
        self.args = args
        require(sha(INPUTS) == args.inputs_sha256, 'assembly source freeze differs')
        self.frozen = read(INPUTS)
        require(sha(PLAN) == self.frozen['plan_sha256'], 'reviewed assembly plan differs')
        self.assembly = read(PLAN)
        self.plan = read(self.assembly['metadata_admission']['path'])
        self.meta = read(self.assembly['metadata_plan']['path'])
        for path in self.frozen['import_sources']:
            require(sha(path) == self.frozen['files'][path], 'assembly import changed')
        self.owned = load('b2_assembly_owned', OWNER / 'experiments/stable-cgu/owned_stage.py')
        self.previous = load('b2_assembly_prior_metadata', readmit.BASE / '.work/beta-auxiliary-metadata-source-01/check.py')
        self.stock = load('b2_assembly_stock', self.previous.STOCK_CODE)
        self.comp = load('b2_assembly_compositor', self.previous.COMPOSITOR)
        self.stage2 = load('b2_assembly_native_source', self.stock.STAGE2 / 'experiments/hir-stage2-package/check.py')
        self.env = self.stock.environment()
        self.old = read(self.stock.PLAN)
        self.current = read(self.assembly['current_inputs']['path'])
        self.assembled = None
        self.runtime_environment = dict(os.environ)
        expected = self.frozen['launch_environment']
        extra = set(self.runtime_environment) - set(expected)
        require(all(self.runtime_environment.get(k) == v for k, v in expected.items())
                and extra <= {'__CF_USER_TEXT_ENCODING'}, 'unexpected assembly environment')
        if extra:
            cf = self.runtime_environment['__CF_USER_TEXT_ENCODING'].split(':')
            require(len(cf) == 3 and all(re.fullmatch(r'(?:0[xX][0-9a-fA-F]{1,8}|[0-9]{1,10})', p) for p in cf)
                    and int(cf[0], 16 if cf[0].lower().startswith('0x') else 10) == os.getuid() == 501,
                    'unexpected Darwin CF context')
        require(not WORK.exists() and not readmit.OUTPUT.exists(), 'fresh assembly work/output required')
        WORK.mkdir()
        self.record = dict(schema_version=1, policy='beta-auxiliary-assembly-strip-v1', status='waiting', owner=str(OWNER),
            pid=os.getpid(), parent_pid=os.getppid(), started_at=time.time(), commands=[],
            inputs_sha256=args.inputs_sha256, assembly_plan_sha256=self.frozen['plan_sha256'],
            metadata_plan_sha256=self.assembly['metadata_plan']['sha256'], environment=self.runtime_environment,
            capacity=dict(entry_gib=16, stop_gib=9, floor_gib=8), original_B_unchanged=False,
            assemblies=0, debug_object_compilations=0, compiler_builds=0, exporter_rebuild=False,
            current_platform_stock_compatibility=False, benchmark=False, publication=False)
        self.save()

    def save(self):
        self.owned.write(WORK / 'receipt.json', self.record)

    def check_sources(self):
        require(sha(INPUTS) == self.args.inputs_sha256 and readmit.platform() == self.plan['current_platform']
                and dict(os.environ) == self.runtime_environment, 'assembly source/platform/environment changed')
        require(str(Path(sys.executable).resolve()) == self.frozen['python']['resolved']
                and sha(sys.executable) == self.frozen['python']['sha256'], 'assembly Python changed')
        for path, expected in self.frozen['files'].items():
            p = Path(path)
            require(p.is_file() and not p.is_symlink() and p.resolve(strict=True) == p and sha(p) == expected,
                    'frozen assembly source/proof changed: ' + path)
        for module in list(sys.modules.values()):
            path = getattr(module, '__file__', None)
            if path and path.startswith('/Users/danluu/dev/rust-interp'):
                require(str(Path(path).resolve()) in self.frozen['files'], 'unfrozen assembly import: ' + path)

    def b2_barrier(self, contents=False):
        if self.assembled is None:
            return
        for name, row in self.assembled.items():
            require(identity(readmit.B2 / name) == row['identity'], 'new B2 input changed: ' + name)
        if contents:
            require(self.comp.output_inventory(readmit.B2) == self.assembled, 'complete B2 bytes/membership changed')

    def command(self, argv, *, cwd=None, env=None):
        self.check_sources(); self.current_barrier(); self.b2_barrier()
        self.owned.disk(OWNER, 9)
        index = len(self.record['commands'])
        wanted = self.assembly['children'][index]
        cwd, env = str(cwd or OWNER), env or self.env
        require(argv == wanted['argv'] and cwd == wanted['cwd'] and env == wanted['environment'], 'unreviewed assembly child')
        executor = '/usr/bin/git' if argv[0] == 'git' else argv[0]
        expected = (self.assembled[readmit.TOOL]['sha256'] if executor == str(readmit.B2 / readmit.TOOL)
                    else self.plan['executors'][executor]['sha256'])
        require(sha(executor) == expected, 'assembly executor bytes changed')
        out = WORK / 'commands' / f'{index:03d}'
        try:
            child = self.owned.run(argv, cwd=cwd, env=env, out=out, capacity_root=OWNER)
        finally:
            if (out / 'receipt.json').exists():
                child = read(out / 'receipt.json')
                self.record['commands'].append(dict(path=str(out / 'receipt.json'), sha256=sha(out / 'receipt.json'),
                    command=child['command'], pid=child.get('pid'), returncode=child.get('returncode')))
                self.save()
        require(sha(executor) == expected, 'assembly executor changed during child')
        self.current_barrier(); self.b2_barrier(); self.check_sources()
        return dict(receipt=child, path=str(out / 'receipt.json'),
                    stdout=(out / 'stdout').read_bytes(), stderr=(out / 'stderr').read_bytes())

    def check_metadata(self):
        terminal = read(self.assembly['metadata_receipt']['path'])
        require(terminal['status'] == 'passed' and terminal['metadata_only']
                and terminal['source_unchanged'] and terminal['runtime_unchanged'] and terminal['original_B_unchanged']
                and terminal['plan_sha256'] == self.assembly['metadata_plan']['sha256']
                and terminal['current_inputs_sha256'] == self.assembly['current_inputs']['sha256'], 'passed exact metadata required')
        require(len(terminal['commands']) == len(self.plan['children']) == 39, 'all metadata commands required')
        for ref, expected in zip(terminal['commands'], self.plan['children'], strict=True):
            child = read(ref['path'])
            require(sha(ref['path']) == ref['sha256'] and child['status'] == 'finished' and child['returncode'] == 0
                    and child['command'] == ref['command'] == expected['argv'] and child['cwd'] == expected['cwd']
                    and child['environment'] == expected['environment'] and child['pid'] == ref['pid']
                    and child['supervisor_pid'] == terminal['pid'] and child['parent_pid'] == terminal['parent_pid']
                    and terminal['admitted_at'] <= child['started_at'] <= child['finished_at'] <= terminal['finished_at'],
                    'metadata child association changed')
            for stream in ['stdout', 'stderr']:
                require(sha(Path(ref['path']).parent / stream) == child[stream + '_sha256'], 'metadata raw stream changed')
        readmit.check_composition(self.old['composition'], self.meta['composition'], self.current)

    def auxiliary_load(self, result):
        allowed = {str(readmit.B2 / readmit.TOOL), str(readmit.B2 / readmit.COPY['destination'])}
        return self.stock.parse_dyld(result['stderr'].decode(), result['receipt']['pid'], allowed,
                                     str(readmit.B2 / readmit.COPY['destination']))

    def run_assembly(self):
        self.check_sources(); self.check_metadata(); self.current_barrier(contents=True)
        snapshot_dir = WORK / 'source-snapshots'
        snapshot_dir.mkdir()
        snapshots = {}
        for path in self.frozen['snapshot_inputs'] + [str(INPUTS)]:
            expected = self.args.inputs_sha256 if path == str(INPUTS) else self.frozen['files'][path]
            data = Path(path).read_bytes()
            require(hashlib.sha256(data).hexdigest() == expected, 'assembly snapshot source changed')
            copy = snapshot_dir / expected
            if not copy.exists():
                self.comp.write_new(copy, data, lambda: self.owned.disk(OWNER, 9))
            require(sha(copy) == expected, 'assembly snapshot readback failed')
            snapshots[path] = dict(path=str(copy), sha256=expected)
        self.owned.write(WORK / 'source-snapshots.json', snapshots)
        self.source_guard()
        original_B = self.original_B()
        self.owned.write(WORK / 'original-B334-before.json', original_B)
        self.owned.disk(OWNER, 9)
        readmit.OUTPUT.mkdir()
        assembled = self.comp.assemble(self.meta['composition'],
            expected_plan_sha256=self.meta['composition_sha256'], destination=readmit.B2,
            evidence=Path(self.meta['evidence']), capacity_guard=lambda: self.owned.disk(OWNER, 9))
        self.assembled = self.comp.output_inventory(readmit.B2)
        require(assembled['files'] == len(self.assembled) == 335
                and assembled['copied_bytes'] == self.meta['copy_payload_bytes'], 'complete assembly differs')
        self.record.update(assemblies=1, assembly=assembled)
        self.save()
        selection = self.command(self.plan['sdk_queries'][-1][1])
        require(not selection['stderr'] and selection['stdout'].decode() == self.plan['sdk_outputs']['otool'], 'selected otool changed')
        future = self.meta['future']
        auxiliary = {}
        for argv, original in zip(future['auxiliary_declarations'], [readmit.TOOL, readmit.COPY['source_destination']], strict=True):
            result = self.command(argv)
            require(not result['stderr'], 'new auxiliary declaration diagnostics')
            declaration = self.previous.declarations(result['stdout'].decode())
            old = self.meta['actual_original_auxiliary_declarations'][original]
            require(declaration['rpaths'] == old['rpaths'] and declaration['loads'] == old['loads'], 'assembled auxiliary Mach-O edges changed')
            auxiliary[argv[-1]] = dict(receipt=result['path'], **declaration)
        version = self.command(future['auxiliary_version'], env=future['auxiliary_environment'])
        require(version['stdout'] and b'LLVM' in version['stdout'], 'auxiliary version output missing')
        version_load = self.auxiliary_load(version)
        debug = Path(future['debug_source']['path']).parent
        debug.mkdir()
        source = Path(future['debug_source']['path'])
        self.comp.write_new(source, future['debug_source']['text'].encode(), lambda: self.owned.disk(OWNER, 9))
        require(sha(source) == future['debug_source']['sha256'], 'debug source differs')
        built = self.command(future['debug_build'], env=future['debug_environment'])
        require(not built['stdout'] and not built['stderr'], 'debug object compilation emitted diagnostics')
        self.record['debug_object_compilations'] = 1
        before, after = debug / 'before.o', debug / 'after.o'
        before_file = self.comp.check_file(dict(path=str(before), sha256=sha(before)))
        source_file = self.comp.check_file(dict(path=str(source), sha256=future['debug_source']['sha256']))
        before_declarations = self.command(future['debug_declarations'][0])
        require(not before_declarations['stderr'] and b'__debug_info' in before_declarations['stdout'], 'embedded debug declaration missing')
        require(not after.exists(), 'fresh stripped output required')
        stripped = self.command(future['strip'], env=future['strip_environment'])
        require(not stripped['stdout'], 'strip emitted unexpected stdout')
        strip_load = self.auxiliary_load(stripped)
        after_declarations = self.command(future['debug_declarations'][1])
        require(not after_declarations['stderr'] and b'__debug_' not in after_declarations['stdout'], 'debug declaration remains after strip')
        require(self.comp.check_file(before_file) == before_file and self.comp.check_file(source_file) == source_file,
                'strip changed original object or source')
        after_file = self.comp.check_file(dict(path=str(after), sha256=sha(after)))
        stripped_proof = check_strip(before.read_bytes(), after.read_bytes())
        self.owned.write(WORK / 'strip-proof.json', dict(**stripped_proof, source=source_file, before=before_file, after=after_file,
            source_unchanged=True, original_object_unchanged=True, nondebug_section_bytes_unchanged=True,
            version_loader=version_load, strip_loader=strip_load, auxiliary_declarations=auxiliary,
            object_executed=False, version_receipt=version['path'], build_receipt=built['path'], strip_receipt=stripped['path']))
        selection = self.command(self.plan['sdk_queries'][-1][1])
        require(not selection['stderr'] and selection['stdout'].decode() == self.plan['sdk_outputs']['otool'], 'selected otool changed afterward')
        self.source_guard()
        require(self.original_B() == original_B, 'original B334 changed during assembly')
        self.current_barrier(contents=True); self.b2_barrier(contents=True); self.check_sources()
        require(len(self.record['commands']) == len(self.assembly['children']) == 19, 'exact nineteen assembly/control children required')
        self.record.update(status='passed', finished_at=time.time(), original_B_unchanged=True, source_unchanged=True,
            runtime_unchanged=True, auxiliary_beta_llvm_loaded=True, real_dwarf_strip_passed=True,
            source_snapshots_sha256=sha(WORK / 'source-snapshots.json'),
            strip_proof_sha256=sha(WORK / 'strip-proof.json'), free_bytes_after=self.owned.disk(OWNER))
        self.save()

    def execute(self):
        try:
            with self.owned.workload_lock(self.owned.CANONICAL_LOCK, 600):
                self.record.update(status='running', admitted_at=time.time(), free_bytes_before=self.owned.disk(OWNER, 16))
                self.save()
                self.run_assembly()
        except BaseException as exc:
            self.record.update(status='failed', error=repr(exc), finished_at=time.time(), free_bytes_after=shutil.disk_usage(OWNER).free)
            self.save()
            raise


def main():
    require(sys.dont_write_bytecode and not sys.flags.optimize and Path.cwd() == OWNER, 'fixed Python -B/cwd required')
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--inputs-sha256', required=True)
    Assembly(parser.parse_args()).execute()


if __name__ == '__main__':
    main()
