"""Conservative static Mach-O route check; launches no metadata process."""
from pathlib import Path

import support as s


def closure(executable, *, cwd, dyld, admitted, macho):
    """Accept only uniquely resolved, already admitted provider bytes.

    DYLD_LIBRARY_PATH and encoded paths are treated as possible routes together.
    Distinct existing routes reject even when dyld would have a preference.
    This deliberately avoids guessing a new loader search precedence. Empty
    path components retain the recipe's working directory. System dyld-cache
    images retain the separately bound platform assumption.
    """
    executable=Path(executable);s.ordinary(executable);s.ordinary(cwd,True)
    search_dirs=[Path(value) if value else cwd for value in dyld.split(':')]
    for path in search_dirs:s.ordinary(path,True)
    result=dict(executable=str(executable),cwd=str(cwd),dyld_library_path=dyld,
                files={},searches={},nodes={},system_libraries=[],static_only=True)
    active=set();systems=set()
    def route(token,loaded):
        if token.startswith('@loader_path/'):return loaded.parent/token[len('@loader_path/'):]
        if token.startswith('@executable_path/'):return executable.parent/token[len('@executable_path/'):]
        if token.startswith('/'):return Path(token)
        raise RuntimeError('unproved loader token: '+token)
    def present(path):
        path=Path(path)
        exists=path.exists() or path.is_symlink();result['searches'][str(path)]=exists
        if exists:
            resolved=path.resolve(strict=True);s.ordinary(resolved)
            assert resolved.is_relative_to(s.N), 'provider escapes admitted owned namespace'
            return resolved
        return None
    def visit(path,inherited=()):
        path=path.resolve(strict=True);context=(str(path),inherited)
        if context in active:return
        active.add(context);assert len(active)<=128
        proof=s.file(path)
        if path!=executable:assert str(path) in admitted and admitted[str(path)]==proof, 'new/unadmitted loader provider'
        result['files'][str(path)]=proof
        deps,rpaths=macho(path,True)
        result['nodes'][str(path)]=dict(dependencies=deps,rpaths=rpaths)
        expanded=tuple(str(route(token,path)) for token in rpaths)+inherited
        for token in deps:
            overrides=[directory/Path(token).name for directory in search_dirs]
            if token.startswith(('/usr/lib/','/System/Library/')):
                assert not any(present(candidate) is not None for candidate in overrides), 'private system-library override'
                systems.add(token);continue
            candidates=list(overrides)
            if token.startswith('@rpath/'):
                candidates.extend(Path(base)/token[len('@rpath/'):] for base in expanded)
            else:candidates.append(route(token,path))
            existing={value for candidate in candidates if (value:=present(candidate)) is not None}
            assert len(existing)==1, ('missing or ambiguous native loader route',token,existing)
            target=next(iter(existing))
            if target!=path:visit(target,expanded)
        assert s.file(path)==proof, 'native image changed during static inspection'
    visit(executable)
    result['system_libraries']=sorted(systems)
    result['system_assumption']='System dyld-cache images are bound to the producer platform; no private file-hash or dynamic-loader trace claim.'
    return result
