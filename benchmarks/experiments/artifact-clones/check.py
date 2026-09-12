"""Verify actual APFS COW independence and failure-before-replacement behavior."""
import fcntl
import os
import run as driver


def main():
    root=driver.ROOT
    with (root/'.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        work=root/'.work/artifact-clone-controls-01';work.mkdir(exist_ok=False)
        source,target=work/'source.bin',work/'target.bin'
        payload=bytes(range(256))*1024
        source.write_bytes(payload);target.write_bytes(payload)
        os.chmod(source,0o600);os.chmod(target,0o640)
        os.utime(source,ns=(1_600_000_000_111111111,1_600_000_000_111111111))
        os.utime(target,ns=(1_600_000_001_222222222,1_600_000_001_222222222))
        a,b=driver.info(source),driver.info(target);digest=driver.sha(source)
        after=driver.replace_duplicate(source,target,a,b,digest,work/'staging.bin')
        driver.require(after['mode']==b['mode'] and after['mtime_ns']==b['mtime_ns'] and
            after['inode'] not in [a['inode'],b['inode']], 'metadata or distinct inode differs')
        with source.open('r+b') as stream:stream.write(b'SOURCE')
        driver.require(target.read_bytes()==payload,'source write changed clone')
        source_after=source.read_bytes()
        with target.open('r+b') as stream:stream.write(b'TARGET')
        driver.require(source.read_bytes()==source_after,'clone write changed source')
        source.write_bytes(payload);target.write_bytes(payload)
        rejected=0
        for case in ['wrong-digest','occupied-staging','bad-clone']:
            a,b=driver.info(source),driver.info(target)
            staging=work/(case+'.bin')
            original_clone=driver.clone
            if case=='occupied-staging':staging.write_bytes(b'reserved')
            if case=='bad-clone':
                driver.clone=lambda src,dst:dst.write_bytes(b'corrupted clone')
            try:
                try:driver.replace_duplicate(source,target,a,b,'0'*64 if case=='wrong-digest' else digest,staging)
                except RuntimeError:rejected+=1
                else:raise RuntimeError('invalid replacement accepted')
            finally:driver.clone=original_clone
            driver.same(target,b)
            driver.require(target.read_bytes()==payload,'rejection changed original')
        out=root/'results/artifact-clone-controls-01';out.mkdir(exist_ok=False)
        driver.write_json(out/'summary.json',dict(status='passed',independent_write_checks=2,
            metadata_preserved=True,distinct_inodes=True,rejections=rejected,originals_preserved_on_rejection=True,
            sources=driver.sources(),fixtures=str(work.relative_to(root)),real_artifact_mutations=0))
        print('two independent-write directions, metadata preservation and three pre-replacement rejections pass')


if __name__=='__main__':main()
