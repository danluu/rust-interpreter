"""No-follow compiler-build sysroot inventory, separate from the SDK policy.

compile.rs Sysroot creates lib/rustlib/rustc-src/rust pointing to builder.src
when download-rustc is disabled. Its ordinary rust-src link is stage>0 only.
The one stage0 source route may leave stage0-sysroot only for the exact owned
compiler source; its target is never walked by this code.
The caller separately guards the complete immutable compiler source closure.
"""
import os
from pathlib import Path
import stat

HOST = 'aarch64-apple-darwin'
SOURCE_LINKS = frozenset({'lib/rustlib/rustc-src/rust'})


def require(value, message):
    if not value:
        raise ValueError(message)


def link_allowed(relative, resolved, root, source):
    root, source, resolved = map(Path, (root, source, resolved))
    require(root == source/'build'/HOST/'stage0-sysroot', 'exact compiler-build sysroot required')
    require(not Path(relative).is_absolute() and '..' not in Path(relative).parts,
            'ordinary relative source-link name required')
    if relative in SOURCE_LINKS:
        require(resolved == source, 'compiler-build source alias does not name its exact source')
        return True
    require(relative != 'lib/rustlib/src/rust' and resolved.is_relative_to(root),
            'compiler-build link escapes its exact source contract')
    return True


def inventory(root, source, stamp, file):
    root, source = Path(root), Path(source)
    require(root == source/'build'/HOST/'stage0-sysroot' and source.resolve(strict=True) == source
            and root.resolve(strict=True) == root and root.is_dir(), 'ordinary fixed sysroot/source required')
    result = {'': dict(kind='directory', stamp=stamp(root))}
    def inaccessible(error):
        raise error
    for parent, directories, files in os.walk(root, followlinks=False, onerror=inaccessible):
        for name in sorted(directories+files):
            path = Path(parent)/name
            require(path.parent.resolve(strict=True) == path.parent, 'sysroot ancestor became a link')
            before = stamp(path); mode = before[2]; relative = str(path.relative_to(root))
            require(len(result) < 20000, 'bounded compiler-build sysroot membership required')
            if stat.S_ISLNK(mode):
                resolved = path.resolve(strict=True)
                link_allowed(relative, resolved, root, source)
                result[relative] = dict(kind='link', stamp=before, target=os.readlink(path), resolved=str(resolved))
            elif stat.S_ISREG(mode):
                result[relative] = dict(kind='file', **file(path))
            else:
                require(stat.S_ISDIR(mode), 'special compiler-build sysroot entry')
                result[relative] = dict(kind='directory', stamp=before)
            require(stamp(path) == before, 'sysroot entry changed during inventory')
    require(SOURCE_LINKS <= set(result) and all(result[name]['kind'] == 'link' for name in SOURCE_LINKS),
            'required bootstrap source alias absent')
    # Reject directory/entry mutations over the whole no-follow traversal.
    for relative, row in result.items():
        require(stamp(root/relative) == row['stamp'], 'sysroot changed during complete inventory')
    return result
