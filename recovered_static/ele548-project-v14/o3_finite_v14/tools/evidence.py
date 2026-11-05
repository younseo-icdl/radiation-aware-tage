#!/usr/bin/env python3
"""Audit frozen source versions or export a local evidence ZIP; never run CPU."""
from pathlib import Path
import argparse, hashlib, importlib.util, json, sys, zipfile
sys.dont_write_bytecode=True
BASE=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('bounded',BASE/'tools/prepare.py')
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
DRAFT_GAP=(''+str(BASE/'tools/run_cpu.py'),'eb010e366d8dbf5fa4aa6e3919782981a9bf1897b7c87c3b28d218b8a4f74f92')
def load(p):return json.loads(Path(p).read_text())
def budget(extra_MiB=0):
    name='resources_followon.py' if (BASE/'reports/INTERNAL_CPU_ALLOCATION_R1.lock.json').exists() else 'resources.py'
    spec=importlib.util.spec_from_file_location('export_resources',BASE/'tools'/name)
    resource=importlib.util.module_from_spec(spec);spec.loader.exec_module(resource)
    return resource.snapshot(0,extra_MiB)
def audit():
    records={}
    def scan(value,owner):
        if isinstance(value,dict):
            if isinstance(value.get('path'),str) and isinstance(value.get('sha256'),str):
                records.setdefault((value['path'],value['sha256']),set()).add(str(owner))
            for child in value.values():scan(child,owner)
        elif isinstance(value,list):
            for child in value:scan(child,owner)
    for p in (BASE/'reports').glob('*.json'):scan(load(p),p)
    for p in (BASE/'runtime').rglob('EXECUTION.json'):scan(load(p),p)
    frozen={m.sha(p):p for p in (BASE/'runtime/frozen').glob('*') if p.is_file()}
    result=[];missing=[]
    for (path,digest),owners in sorted(records.items()):
        p=Path(path)
        item={'original_path':path,'sha256':digest,'referenced_by':sorted(owners)}
        if p.is_file() and m.sha(p)==digest:item.update(status='CURRENT_BYTES_MATCH',verified_bytes=str(p))
        elif digest in frozen:item.update(status='HISTORICAL_BYTES_PRESERVED',verified_bytes=str(frozen[digest]))
        else:
            assert (path,digest)==DRAFT_GAP and all(Path(o).name=='CPU_EXECUTION_PROPOSAL.lock.json' for o in owners),('UNEXPECTED_PROVENANCE_GAP',item)
            item.update(status='UNEXECUTED_SUPERSEDED_DRAFT_SOURCE_NOT_RETAINED',verified_bytes=None)
            missing.append(item)
        result.append(item)
    # The gap above is never allowed in the actual approved/executed producer.
    actual=load(BASE/'reports/MEASURED_BINARY_B1.json')
    for ref in actual['actual_dependencies']+[actual['binary']]:assert m.sha(ref['path'])==ref['sha256']
    plan=load(BASE/'reports/CPU24_PLAN.lock.json')
    for key in ['runner','binary','config','proposal','authorization']:assert m.sha(plan[key]['path'])==plan[key]['sha256']
    for ref in load(BASE/'reports/PRESERVATION.lock.json')['preserved']:assert m.sha(ref['path'])==ref['sha256']
    target=BASE/'reports/FINAL_BINDINGS.json'
    m.put(target,{'status':'PASS_EXECUTED_PRODUCER_BINDINGS_WITH_VISIBLE_UNEXECUTED_DRAFT_GAP',
        'records':result,'unexecuted_draft_gaps':missing,
        'note':'Superseded planning proposal only; actual B1 authorization/plan/build/dependencies and raw CPU bindings are checked strictly. No claim of complete historical snapshot retention.',
        'audit_tool':m.ref(Path(__file__)),'resources':budget()})
    print('AUDITED',len(result),'VISIBLE_UNEXECUTED_DRAFT_GAPS',len(missing))
def package():
    assert (BASE/'reports/FINAL_BINDINGS.json').exists()
    files=[];excluded=[]
    for p in sorted(BASE.rglob('*')):
        if not p.is_file() or 'artifacts' in p.relative_to(BASE).parts:continue
        with p.open('rb') as f:magic=f.read(4)
        if magic==b'\x7fELF':excluded.append(m.ref(p));continue
        files.append(p)
    # Conservative uncompressed reservation, then verify every archived byte.
    size=sum(p.stat().st_size for p in files)
    budget(size/1048576+1)
    manifest=BASE/'reports/LOCAL_EXPORT_CONTENTS.json'
    m.put(manifest,{'files':[m.ref(p) for p in files],'excluded_ELF_objects_and_binaries_preserved_in_place':excluded,
        'note':'Archive does not embed large existing/new ELF producers; exact paths/SHA remain here. No original dataset/PDK upload.'})
    files.append(manifest)
    directory=BASE/'artifacts';directory.mkdir(exist_ok=True)
    target=directory/'BP_SEU_V14_FINITE_O3_RESULTS.zip'
    with zipfile.ZipFile(target,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in files:z.write(p,'o3_finite_v14/'+str(p.relative_to(BASE)))
    with zipfile.ZipFile(target) as z:
        assert z.testzip() is None
        for item in load(manifest)['files']:
            entry='o3_finite_v14/'+str(Path(item['path']).relative_to(BASE))
            assert hashlib.sha256(z.read(entry)).hexdigest()==item['sha256']
    m.put(BASE/'reports/POST_EXPORT_VERIFICATION.json',{'status':'PASS_ZIP_BYTES_AND_RESOURCE_GUARDS_NOT_HARDWARE_QUALIFICATION',
        'archive':m.ref(target),'included_files':len(files),'ELF_excluded':len(excluded),'resources':budget()})
    print('EXPORTED',m.ref(target))
def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['audit','package']);a=p.parse_args()
    (audit if a.action=='audit' else package)()
if __name__=='__main__':main()
