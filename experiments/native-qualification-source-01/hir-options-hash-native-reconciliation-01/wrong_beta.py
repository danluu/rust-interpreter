"""Source-bound E0514 interpretation of saved wrong-B3 diagnostic pairs.

No process, compiler, fixture mutation or provider discovery occurs here. The
caller supplies the original frozen observation parser, the unchanged std/core
selection, the complete selected B3 provider rows, and a mandatory callback that
revalidates each actually named provider against its frozen bytes. Qualification
requires the enclosing reconciliation to verify the complete original history.
"""
import json
from pathlib import Path
import re
import stat

FIELDS = {'dev', 'ino', 'mode', 'size', 'mtime_ns', 'ctime_ns', 'nlink'}


def require(value, message):
    if not value:
        raise ValueError(message)


def provider_rows(rows, beta_lib, beta_std_paths):
    require(type(rows) is list and 0 < len(rows) <= 128, 'bounded explicit beta provider rows required')
    root = Path(beta_lib)
    require(root.is_absolute() and str(root) == beta_lib and '..' not in root.parts,
            'canonical beta standard-library directory required')
    result = {}
    for row in rows:
        require(type(row) is dict and set(row) == {'path','size','sha256','identity'},
                'exact beta provider fields required')
        name = row['path']; stamp = row['identity']
        require(type(name) is str and str(Path(name)) == name and Path(name).parent == root
                and '..' not in Path(name).parts and not any(ord(c) < 32 or ord(c) == 127 for c in name)
                and re.fullmatch(r'lib(?:std|std_detect|core|compiler_builtins)-[a-f0-9]+\.(?:rlib|rmeta|dylib)',Path(name).name),
                'foreign or unsafe beta provider route')
        require(name not in result and type(row['size']) is int and 0 < row['size'] <= 2**30
                and type(row['sha256']) is str and re.fullmatch('[a-f0-9]{64}',row['sha256'])
                and type(stamp) is dict and set(stamp) == FIELDS
                and all(type(v) is int for v in stamp.values())
                and stat.S_ISREG(stamp['mode']) and stamp['nlink'] == 1 and stamp['size'] == row['size'],
                'ambiguous or malformed beta provider identity')
        result[name] = row
    require(type(beta_std_paths) is list and beta_std_paths and len(beta_std_paths) == len(set(beta_std_paths))
            and all(name in result and re.fullmatch(r'lib(?:std|core)-[a-f0-9]+\.(?:rlib|rmeta|dylib)',Path(name).name)
                    for name in beta_std_paths), 'unchanged admitted std/core selection required')
    return result


def wrong_pair(ordinary, candidate, *, observed, beta_lib, beta_std_paths,
               providers, beta_version, native_version, verify_provider):
    """Parse full saved parity and verify every path named by a coded E0514.

`verify_provider(row)` must return exactly the supplied row after current
identity/hash verification. It is mandatory; there is no metadata-only success
fallback. Tiny controls substitute an explicit fixture callback and make no
claim about real provider qualification.
"""
    require(callable(verify_provider), 'frozen provider byte verifier required')
    require(all(type(v) is str and re.fullmatch(r'rustc [^\r\n\x00]+',v)
                for v in [beta_version,native_version]) and beta_version != native_version,
            'distinct exact observed beta/native compiler identities required')
    require(all(type(pair) in [tuple,list] and len(pair) == 2
                and all(type(raw) is bytes and len(raw) <= 2**20 for raw in pair)
                for pair in [ordinary,candidate]), 'bounded complete raw diagnostic pair required')
    result = observed.error_pair(ordinary,candidate,'E0514')
    require(1 <= len(result['errors']) <= 3, 'bounded E0514 crate set required')
    catalog = provider_rows(providers,beta_lib,beta_std_paths)
    records = [json.loads(line) for line in ordinary[1].splitlines()]
    require(len(records) <= 8, 'bounded complete diagnostic record set required')
    crates = []; matched = {}; primary = set(); builtins = set()
    for row in result['errors']:
        match = re.fullmatch(r'found crate `(std|core|compiler_builtins)` compiled by an incompatible version of rustc',row['message'])
        require(match is not None, 'unknown incompatible-crate diagnostic')
        crate = match.group(1)
        require(crate not in crates, 'duplicate incompatible-crate diagnostic')
        crates.append(crate)
        children = row.get('children')
        require(type(children) is list and len(children) == 2
                and children[0].get('level') == 'note' and children[1].get('level') == 'help',
                'complete source-defined incompatible-version note/help required')
        require(children[1].get('message') == 'please recompile that crate using this compiler ('+native_version+') (consider running `cargo clean` first)',
                'native compiler help identity differs')
        lines = children[0].get('message','').splitlines()
        require(2 <= len(lines) <= 129 and lines[0] == 'the following crate versions were found:',
                'complete source-defined provider note required')
        note_paths = []
        prefix = 'crate `'+crate+'` compiled by '+beta_version+': '
        for line in lines[1:]:
            require(line.startswith(prefix), 'provider note crate/version differs')
            path = line[len(prefix):]
            require(path in catalog and path not in note_paths, 'unknown, foreign or duplicate beta provider note')
            expression = (r'libstd(?:_detect)?-[a-f0-9]+\.(?:rlib|rmeta|dylib)' if crate == 'std'
                          else r'lib'+crate+r'-[a-f0-9]+\.(?:rlib|rmeta|dylib)')
            require(re.fullmatch(expression,Path(path).name), 'provider artifact does not belong to diagnosed crate')
            row_proof = catalog[path]
            require(verify_provider(row_proof) == row_proof, 'actual frozen beta provider bytes differ')
            matched[path] = row_proof; note_paths.append(path)
        if crate in ['std','core']:
            selected = set(note_paths) & set(beta_std_paths)
            require(selected, 'diagnostic lacks an original admitted std/core provider')
            primary.update(selected)
        else:
            builtins.update(note_paths)
    require(primary and any(crate in ['std','core'] for crate in crates),
            'compiler_builtins cannot substitute for the required std/core failure')
    # These optional consequences are emitted after the rejected prelude and
    # lang-item crates. Preserve complete records and reject unrelated errors.
    optional = {'cannot resolve a prelude import', 'requires `sized` lang_item'}
    uncoded_errors = [row for row in records if row['level'] == 'error' and row.get('code') is None]
    consequences = [row['message'] for row in uncoded_errors if row['message'] in optional]
    require(len(consequences) == len(set(consequences)), 'duplicate downstream diagnostic')
    count = len(result['errors'])+len(consequences)
    abort = 'aborting due to '+str(count)+' previous '+('error' if count == 1 else 'errors')
    require([row['message'] for row in uncoded_errors if row['message'] not in optional] == [abort],
            'unknown uncoded diagnostic or incomplete error summary')
    require(all(row.get('code') is None for row in records if row['level'] == 'failure-note')
            and [row['message'] for row in records if row['level'] == 'failure-note']
            == ['For more information about this error, try `rustc --explain E0514`.'],
            'complete E0514 explanatory footer required')
    result.update(beta_std_paths=sorted(primary), compiler_builtins_paths=sorted(builtins),
                  coded_crates=crates, provider_files=[matched[name] for name in sorted(matched)],
                  beta_version=beta_version,native_version=native_version,
                  full_raw_parity=True,all_named_provider_bytes_verified=True)
    return result
