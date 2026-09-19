"""Losslessly bind ordinary dyld load/delayed-list events to one child.

Apple RuntimeState::partitionDelayLoads moves images in both directions, logging
leafName() rather than the full path. Resolve only an unambiguous prior load.
https://github.com/apple-oss-distributions/dyld/blob/main/dyld/DyldRuntimeState.cpp
"""
import hashlib
import re

_UUID = r'[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}'
_LOAD = re.compile(r'dyld\[([1-9][0-9]*)\]: <('+_UUID+r')> (/[^\x00\r\n]+)')
_MOVE = re.compile(r'dyld\[([1-9][0-9]*)\]: move (loaded to delayed|delayed to loaded): ([^/\x00\r\n]+)')


def loaded_libraries(c, raw, pid, allowed, driver):
    """Parse bytes only; never inspect paths, import providers, or run a child.

    ``loaded`` and ``delayed`` are dyld's list states, not mapping/unmapping
    assertions. The admitted driver must end in the loaded/active list.
    """
    require=c.require
    require(type(raw) is bytes and type(pid) is int and pid>0,'dyld raw bytes/actual PID required')
    require(type(driver) is str and driver in allowed and driver.startswith('/'),'admitted exact driver required')
    images={};basenames={};events=[];position=0
    for number, line in enumerate(raw.splitlines(keepends=True),1):
        require(line.endswith(b'\n') and not line.endswith(b'\r\n'),'complete LF dyld row required')
        try:body=line[:-1].decode('utf-8')
        except UnicodeDecodeError as error:raise RuntimeError('invalid UTF-8 dyld row') from error
        event=dict(line=number,start=position,end=position+len(line),raw_hex=line.hex())
        match=_LOAD.fullmatch(body)
        if match is not None:
            require(int(match[1])==pid,'dyld load belongs to another process')
            uuid,path=match[2],match[3];name=path.rsplit('/',1)[-1]
            require(name not in ('','.','..') and path not in images,'duplicate or invalid dyld image load')
            system=path.startswith(('/usr/lib/','/System/Library/'))
            require(system or path in allowed,'unadmitted loaded non-system library: '+path)
            images[path]=dict(path=path,uuid=uuid,state='loaded',system=system,load_event=len(events))
            basenames.setdefault(name,[]).append(path)
            event.update(kind='load',path=path,uuid=uuid,state='loaded')
        else:
            match=_MOVE.fullmatch(body)
            require(match is not None,'unrecognized actual dyld observation')
            require(int(match[1])==pid,'dyld transition belongs to another process')
            direction,name=match[2],match[3];matches=basenames.get(name,[])
            require(len(matches)==1,'dyld transition has missing or ambiguous prior basename: '+name)
            path=matches[0];before,after=direction.split(' to ')
            require(images[path]['state']==before,'dyld transition has incompatible prior state: '+name)
            images[path]['state']=after
            event.update(kind='transition',path=path,basename=name,before=before,after=after)
        events.append(event);position+=len(line)
    require(position==len(raw) and b''.join(bytes.fromhex(e['raw_hex']) for e in events)==raw,
            'dyld events were not retained losslessly')
    require(driver in images and images[driver]['state']=='loaded','selected driver is not active at end of dyld observations')
    return dict(policy='dyld-loaded-delayed-events-v1',pid=pid,raw_sha256=hashlib.sha256(raw).hexdigest(),
        raw_bytes=len(raw),events=events,images=list(images.values()),
        loaded=[p for p,row in images.items() if row['state']=='loaded'],
        delayed=[p for p,row in images.items() if row['state']=='delayed'],
        selected_driver=driver,selected_driver_active=True)
