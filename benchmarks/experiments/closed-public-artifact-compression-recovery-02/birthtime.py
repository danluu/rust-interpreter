"""Darwin file creation time, using the installed SDK's attrlist ABI."""
import ctypes,os,struct,sys
from pathlib import Path
class AttrList(ctypes.Structure):
    _fields_=[('bitmapcount',ctypes.c_uint16),('reserved',ctypes.c_uint16),
        ('commonattr',ctypes.c_uint32),('volattr',ctypes.c_uint32),
        ('dirattr',ctypes.c_uint32),('fileattr',ctypes.c_uint32),('forkattr',ctypes.c_uint32)]
assert sys.platform=='darwin' and ctypes.sizeof(AttrList)==24 and ctypes.sizeof(ctypes.c_long)==8
LIB=ctypes.CDLL('/usr/lib/libSystem.B.dylib',use_errno=True)
for name in ['fgetattrlist','fsetattrlist']:
    f=getattr(LIB,name);f.argtypes=[ctypes.c_int,ctypes.POINTER(AttrList),ctypes.c_void_p,ctypes.c_size_t,ctypes.c_uint];f.restype=ctypes.c_int
def call(name,fd,buffer):
    attrs=AttrList(5,0,0x200,0,0,0,0)
    if getattr(LIB,name)(fd,ctypes.byref(attrs),buffer,ctypes.sizeof(buffer),0)!=0:
        code=ctypes.get_errno();raise OSError(code,os.strerror(code))
def birthtime(path):
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
    try:
        buf=ctypes.create_string_buffer(20);call('fgetattrlist',fd,buf)
        size,sec,nsec=struct.unpack('=Iqq',buf.raw);assert size==20 and 0<=nsec<10**9
        return sec,nsec
    finally:os.close(fd)
def set_birthtime(path,value):
    # Only disposable fixtures or the exact operation's adjacent temporary copies.
    p=Path(path);assert p.name.endswith(('.fixture','.tmp')) and not p.is_symlink()
    sec,nsec=value;assert type(sec) is type(nsec) is int and 0<=nsec<10**9
    fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW)
    try:
        payload=struct.pack('=qq',sec,nsec);buf=ctypes.create_string_buffer(payload,len(payload));call('fsetattrlist',fd,buf)
    finally:os.close(fd)
    assert birthtime(p)==tuple(value)
