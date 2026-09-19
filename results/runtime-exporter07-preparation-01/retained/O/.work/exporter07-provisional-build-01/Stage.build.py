    def build(self):
        c=self.c
        c.require(self.args.metadata_receipt_sha256 is not None,'actual closed metadata pin required')
        receipt=c.read(c.WORK/'receipt.json',self.args.metadata_receipt_sha256)
        c.require(receipt['status']=='passed' and receipt['phase']=='metadata'
            and receipt['inputs_sha256']==self.args.inputs_sha256 and receipt['sources_sha256']==self.args.sources_sha256
            and len(receipt['commands'])==len(self.plan['children']),'complete actual metadata required')
        for saved,wanted in zip(receipt['commands'],self.plan['children'],strict=True):
            path=Path(saved['path']);actual=c.read(path,saved['sha256'])
            c.require(actual['status']=='finished' and actual['returncode']==0
                and actual['command']==wanted['command'] and actual['environment']==wanted['environment']
                and actual['cwd']==wanted['cwd'] and actual['supervisor_pid']==receipt['pid']
                and receipt['admitted_at']<=actual['started_at']<=actual['finished_at']<=receipt['finished_at'],
                'metadata command closure association differs')
            for stream in ('stdout','stderr'):c.file(path.parent/stream,actual[stream+'_sha256'])
        metadata=c.read(c.WORK/'planned.json',receipt['result']['sha256'])
        c.require(metadata['binding']==self.plan['binding'],'metadata role binding differs')
        for row in metadata['loader_observations']:
            path=Path(row['receipt']);raw=c.read(path)
            c.file(path.parent/'stdout',row['stdout_sha256'])
            self.cache[(row['path'],row['flag'])]=dict(stdout=(path.parent/'stdout').read_bytes(),stderr=b'')
        checks=imported('build_checks');parser=imported('cargo_output')
        future=self.plan['future_build']
        build=self.command(dict(label='cargo-build',command=future['command'],cwd=future['cwd'],
            environment=future['environment'],expected=[0]))
        checks.check_build_diagnostics(build['stderr'])
        parsed=parser.parse_cargo_output(build['stdout'],metadata['dependencies']['packages'])
        compiles=checks.cargo_compiles(build['stderr'],self.plan['binding'],c.PREFIX,set(self.plan['files']))
        names=['rust-interp-mir-export','rust-interp-rustc-wrapper']
        self.binaries={name:c.file(c.TARGET/'release'/name) for name in names}
        actual={r.get('executable') for r in parsed['messages'] if r.get('reason')=='compiler-artifact'
                and 'bin' in r.get('target',{}).get('kind',[]) and r.get('executable')}
        c.require(actual=={r['path'] for r in self.binaries.values()},'Cargo executable set differs')
        generated=[]
        for message in parsed['messages']:
            if message.get('reason')=='build-script-executed' and message.get('out_dir'):
                path=Path(message['out_dir'])/'compiler_roles.rs'
                if path.is_file():
                    c.require(path.is_relative_to(c.TARGET),'generated binding outside owned target')
                    generated.append(c.file(path))
        c.require(len(generated)==1,'exact generated role binding required')
        environment=self.plan['launch_environment']
        def command(label,argv,env=environment):
            return self.command(dict(label=label,command=argv,environment=env,cwd=str(c.X),expected=[0]))
        tool_closures={}
        for name in names:
            path=self.binaries[name]['path']
            for flag in ('-L','-l'):
                self.cache[(path,flag)]=command(name+flag,['/usr/bin/otool','-arch','arm64',flag,path])
            tool_closures[name]=self.closure(path)
        exporter=self.binaries[names[0]]['path'];wrapper=self.binaries[names[1]]['path']
        caps=command('exporter-capabilities',[exporter,'--rust-interp-capabilities'],environment|{'DYLD_PRINT_LIBRARIES':'1'})
        capabilities=json.loads(caps['stdout']);driver=self.plan['binding']['runtime_driver']['path']
        allowed={exporter}|{r['resolved'] for r in tool_closures[names[0]]['identity']['libraries']}
        loaded=loaded_libraries(c,caps['stderr'],caps['receipt']['pid'],allowed,driver)
        c.require(capabilities['schema_version']==1 and capabilities['bytecode_version']==5
            and capabilities['compiler_sysroot']==str(c.RUNTIME) and capabilities['compiler_roles']==self.plan['binding'],
            'built exporter capability/role binding differs')
        wrapper_result=command('wrapper-roles',[wrapper,'--rust-interp-compiler-roles'])
        c.require(not wrapper_result['stderr'],'wrapper role diagnostics')
        binary_map={name:row['sha256'] for name,row in self.binaries.items()}
        vm=self.plan['adopted_VM']['binary'];c.file(vm['path'],vm['sha256']);binary_map['rust-interp-vm']=vm['sha256']
        compiler=self.mods.runtime.load_runtime_compiler(c.R,c.KEY)
        self.mods.tools.bind_recorded_wrapper(capabilities,binary_map,compiler,wrapper_result['stdout'])
        evidence=c.write(self.work/'cargo-build-evidence.json',dict(parsed=parsed,compilers=compiles,generated=generated,
            cargo_receipt=build['path'],strip_failures=0,build_script_compiler_identity_probes=4))
        self.guard(full=True)
        for row in self.binaries.values():c.require(c.file(row['path'])==row,'built tool changed after qualification')
        self.record['exporter_builds']=1
        return c.write(self.work/'built-tools.json',dict(status='build-passed-frontend-unexecuted',binaries=binary_map,
            built_files=self.binaries,capabilities=capabilities,compiler_roles=self.plan['binding'],
            generated=generated,loader=loaded,tool_closures=tool_closures,evidence=evidence,
            VM=self.plan['adopted_VM'],runtime_owner=str(c.R),runtime_key=c.KEY,
            frontend_qualified=False,application_qualified=False,published=False))
