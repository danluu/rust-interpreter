"""Retain Cargo JSON and -vv package-prefixed build-script output separately."""
import json


def parse_cargo_output(raw,packages):
    labels={}
    for package in packages:
        label=f"[{package['name']} {package['version']}] "
        if label in labels:raise ValueError('ambiguous Cargo package prefix')
        labels[label]=package['id']
    messages=[];forwarded=[];rows=[]
    for number,line in enumerate(raw.decode('utf-8').splitlines(keepends=True),1):
        if line.startswith('{'):
            message=json.loads(line)
            if not isinstance(message,dict) or message.get('reason') not in {
                'compiler-artifact','build-script-executed','compiler-message','build-finished','future-incompat-report'}:
                raise ValueError('unknown Cargo JSON message')
            messages.append(message);rows.append(dict(line=number,kind='cargo-json',raw=line,message=message))
        else:
            matched=[(prefix,package) for prefix,package in labels.items() if line.startswith(prefix)]
            if len(matched)!=1:raise ValueError('unrecognized Cargo verbose stdout row')
            prefix,package=matched[0]
            row=dict(line=number,kind='build-script-stdout',raw=line,package_id=package,prefix=prefix)
            rows.append(row);forwarded.append(row)
    if not rows or rows[-1]['kind']!='cargo-json' or messages[-1].get('reason')!='build-finished' or messages[-1].get('success') is not True:
        raise ValueError('successful terminal Cargo build-finished required')
    executed={message['package_id'] for message in messages if message['reason']=='build-script-executed'}
    if any(row['package_id'] not in executed for row in forwarded):
        raise ValueError('verbose stdout package has no actual build-script-executed record')
    if ''.join(row['raw'] for row in rows).encode('utf-8')!=raw:raise ValueError('raw Cargo row preservation failed')
    return dict(messages=messages,forwarded=forwarded,rows=rows)
