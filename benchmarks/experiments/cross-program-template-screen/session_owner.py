"""Own and reap only explicitly created benchmark sessions; no process signals."""
import json,os,resource,struct,subprocess,time
from pathlib import Path

def read_frame(stream,wire):
    def exact(n):
        data=bytearray()
        while len(data)<n:
            part=stream.read(n-len(data))
            if not part:raise RuntimeError('owned session closed before a complete frame')
            data.extend(part);wire.write(part)
        return data
    n,=struct.unpack('<I',exact(4));assert 0<n<=4*1024**2
    return json.loads(exact(n))

class Session:
    def __init__(self,binary,cwd,endpoint,folder,capacity,write,sha):
        self.child=None;self.closed=False;self.write=write;self.sha=sha;self.folder=folder;self.endpoint=endpoint;self.record={}
        folder.mkdir(exist_ok=False);self.wire=(folder/'stdout').open('xb');self.stderr=(folder/'stderr').open('xb')
        command=[str(binary),'--serve-socket',str(endpoint),'--history-bytes',str(capacity)]
        before=resource.getrusage(resource.RUSAGE_CHILDREN);parent=time.process_time();start=time.perf_counter()
        try:
            self.child=subprocess.Popen(command,cwd=cwd,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.stderr)
            self.record=dict(pid=self.child.pid,parent_pid=os.getpid(),command=command,cwd=str(cwd),started_epoch=time.time())
            self.record['identity']=subprocess.check_output(['ps','-p',str(self.child.pid),'-o','pid,ppid,lstart,tty,command'],text=True)
            write(folder/'identity.json',self.record)
            ready=read_frame(self.child.stdout,self.wire);assert ready['kind']=='ready' and ready['schema']==1 and ready['pid']==self.child.pid
            assert ready['executable_sha256']==sha(binary) and ready['workers']==2 and ready['verify_hits'] is False
            assert ready['history_bytes_per_worker']==capacity and ready['cwd']==str(cwd)
            after=resource.getrusage(resource.RUSAGE_CHILDREN)
            self.record.update(startup_wall_seconds=time.perf_counter()-start,startup_parent_cpu_seconds=time.process_time()-parent,
                startup_helper_cpu_seconds=after.ru_utime-before.ru_utime+after.ru_stime-before.ru_stime,
                executable_sha256=ready['executable_sha256'],history_bytes_per_worker=capacity,verify_hits=False,cpu_at_ready=ready['cpu_at_ready'])
            write(folder/'ready.json',ready);write(folder/'identity.json',self.record)
        except BaseException:
            self.close();raise

    def close(self):
        if self.closed:return
        self.closed=True;closed=None;error=None;start=time.perf_counter();parent=time.process_time()
        if self.child is None:
            self.wire.close();self.stderr.close();return
        try:
            if self.child is not None:
                self.child.stdin.close();closed=read_frame(self.child.stdout,self.wire)
                if closed.get('kind')=='ready':closed=read_frame(self.child.stdout,self.wire)
                assert closed['kind']=='closed' and closed['reason']=='owner_eof' and closed['pid']==self.child.pid
        except BaseException as exc:error=repr(exc)
        finally:
            if self.child is not None:
                self.child.stdin.close();self.wire.write(self.child.stdout.read());self.wire.flush();self.stderr.flush()
                pid,status,usage=os.wait4(self.child.pid,0);assert pid==self.child.pid;self.child.returncode=os.waitstatus_to_exitcode(status)
                self.record.update(returncode=self.child.returncode,kernel_cpu=dict(user_seconds=usage.ru_utime,system_seconds=usage.ru_stime),
                    teardown_wall_seconds=time.perf_counter()-start,teardown_parent_cpu_seconds=time.process_time()-parent,
                    requests_consumed=closed['requests_consumed'] if closed else None,closed=closed,error=error,
                    stdout_sha256=self.sha(self.folder/'stdout'),stderr_sha256=self.sha(self.folder/'stderr'))
                if closed:
                    for field,kernel in [('user_us',usage.ru_utime),('system_us',usage.ru_stime)]:assert closed['cpu_at_close'][field]<=kernel*1_000_000+1000
                self.write(self.folder/'terminal.json',self.record)
            self.wire.close();self.stderr.close()
        if error:raise RuntimeError(error)
        assert self.child is not None and self.child.returncode==0
