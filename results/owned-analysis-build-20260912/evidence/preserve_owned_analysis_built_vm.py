from pathlib import Path
import hashlib,json,shutil,time
root=Path(__file__).resolve().parents[2];b=Path(__file__).resolve().parent
manifest=json.loads((b/'owned-analysis-tools.json').read_text())
original=Path(manifest['built_binaries']['rust-interp-vm']['path']);expected=manifest['built_binaries']['rust-interp-vm']['sha256']
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(original)==expected
folder=b/'owned-analysis-built-vm';folder.mkdir(exist_ok=False)
copy=folder/'rust-interp-vm';shutil.copy2(original,copy);assert sha(copy)==expected
copy.chmod(0o555)
receipt={'original_path':str(original),'retained_path':str(copy),'sha256':expected,'bytes':copy.stat().st_size,'selected_for_benchmarks':False,'selected_vm_sha256':manifest['binaries']['rust-interp-vm'],'preserved_at':time.time()}
(b/'owned-analysis-built-vm-preservation.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))
