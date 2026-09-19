"""Qualification-only capture helpers; no measured or substitute validator."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import sys

FLOOR = 16 * 1024 ** 3


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def setup():
    require(len(sys.argv) == 2, "one qualification descriptor required")
    config = json.loads(Path(sys.argv[1]).read_bytes())
    require(sys.dont_write_bytecode and sys.pycache_prefix == config["pycache_prefix"], "private -B regime required")
    def reject(event, args):
        if event in {"subprocess.Popen", "os.system", "os.posix_spawn", "os.exec", "os.fork", "os.forkpty", "os.spawn"}:
            raise RuntimeError("qualification attempted a child: " + event)
    sys.addaudithook(reject)
    return config


def owned(path, root):
    path, root = Path(path), Path(root)
    require(path.is_absolute() and root.resolve() == root and path.resolve() == path
            and path.is_relative_to(root) and path != root, "noncanonical/unowned output")
    return path


def guard(path):
    v = os.statvfs(path)
    require(v.f_bavail * v.f_frsize > FLOOR, "16 GiB disk floor")


def proof(path):
    before = path.lstat()
    stamp = lambda s: [s.st_dev, s.st_ino, s.st_mode, s.st_size, s.st_mtime_ns, s.st_ctime_ns, s.st_nlink]
    require(stat.S_ISREG(before.st_mode) and before.st_size <= 64 * 1024 ** 2 + 1, "regular bounded input required")
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK), "rb") as stream:
        require(stamp(os.fstat(stream.fileno())) == stamp(before), "opening identity changed")
        data = stream.read(64 * 1024 ** 2 + 2)
        require(stamp(os.fstat(stream.fileno())) == stamp(before), "read identity changed")
    require(len(data) == before.st_size and stamp(path.lstat()) == stamp(before), "input changed")
    return dict(path=str(path), bytes=len(data), sha256=hashlib.sha256(data).hexdigest(), stamp=stamp(before))


def load(root, tag):
    path = Path(root) / "scripts/allocation_trace.py"
    spec = importlib.util.spec_from_file_location("qualified_allocation_" + tag, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    require(Path(module.__file__).resolve() == path, "wrong implementation source")
    return module


def exception(error):
    result = dict(type=type(error).__module__ + "." + type(error).__qualname__,
                  message=str(error), args=error.args)
    if isinstance(error, json.JSONDecodeError):
        result["json"] = {k: getattr(error, k) for k in ("msg", "doc", "pos", "lineno", "colno")}
    if isinstance(error, UnicodeDecodeError):
        result["unicode"] = {k: getattr(error, k) for k in ("encoding", "object", "start", "end", "reason")}
    result["cause"] = None if error.__cause__ is None else exception(error.__cause__)
    return result


def capture(call):
    try:
        return dict(ok=True, value=call())
    except Exception as error:
        return dict(ok=False, error=exception(error))


def capture_depth(module, data, digest, depth):
    def descend(remaining):
        if remaining:
            return descend(remaining - 1)
        return module.validate_trace(data, digest)
    try:
        return dict(ok=True, value=descend(depth), api_entered=True)
    except Exception as error:
        entered, trace = False, error.__traceback__
        while trace is not None:
            entered = entered or trace.tb_frame.f_code is module.validate_trace.__code__
            trace = trace.tb_next
        return dict(ok=False, error=exception(error), api_entered=entered)


def compact(value):
    # Call only AFTER raw outcome equality; preserve error messages and all small fields.
    if isinstance(value, bytes):
        return dict(bytes=len(value), sha256=hashlib.sha256(value).hexdigest(), hex=value.hex() if len(value) <= 256 else None)
    if isinstance(value, str) and len(value) > 512:
        return dict(characters=len(value), utf8_sha256=hashlib.sha256(value.encode("utf-8", "surrogatepass")).hexdigest())
    if isinstance(value, dict):
        return {k: compact(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [compact(v) for v in value]
    return value



def lossless(value):
    # Transport reports cross process boundaries: retain complete text and bytes.
    if isinstance(value, bytes):
        return dict(raw_bytes_hex=value.hex())
    if isinstance(value, dict):
        return {k: lossless(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [lossless(v) for v in value]
    return value


def modules():
    return {name: dict(file=vars(m)["__file__"], cached=vars(m).get("__cached__"))
            for name, m in sorted(sys.modules.items()) if m is not None
            and isinstance(vars(m).get("__file__"), str)}
