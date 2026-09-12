"""Validate compiler-derived test names and attributes from Cargo's exact sidecar."""
import hashlib
import json


def read_listing(path):
    if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= 8*1024*1024:
        raise RuntimeError('missing or oversized test discovery report')
    payload=path.read_bytes()
    try:
        report=json.loads(payload)
        tests=report['tests']
        if (report['kind']!='test-discovery' or report['schema_version']!=1 or
                report['strict_frontend'] is not True or report['executed'] is not False or
                report['harness']!='libtest' or not isinstance(report['target'],str) or not report['target'] or
                not isinstance(tests,list) or len(tests)>16_384 or type(report['count']) is not int or report['count']!=len(tests)):
            raise ValueError('incompatible report header')
        names=[]
        for test in tests:
            name=test['name'];names.append(name)
            if (not isinstance(name,str) or not 0<len(name.encode())<=4096 or
                    test['status']!='classified' or test['harness']!='libtest' or
                    test['native_name']!=name or test['function']!=name or
                    not isinstance(test['descriptor'],str) or not test['descriptor'] or
                    type(test['ignored']) is not bool or type(test['should_panic']) is not bool or
                    type(test['ordinary_test']) is not bool or test['ordinary_test']!=(not test['ignored'] and not test['should_panic']) or
                    any(test[field] is not None and not isinstance(test[field],str) for field in ['ignore_reason','panic_message'])):
                raise ValueError('unclassified or inconsistent test attributes')
        if names!=sorted(set(names)):
            raise ValueError('test names are unsorted or repeated')
    except (ValueError,KeyError,TypeError,AttributeError) as error:
        raise RuntimeError('Cargo selected an invalid test discovery report: '+str(error)) from error
    return report,hashlib.sha256(payload).hexdigest()
