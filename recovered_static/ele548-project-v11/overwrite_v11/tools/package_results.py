#!/usr/bin/env python3
"""Private evidence allowlist; excludes binaries, datasets and old producers."""
from pathlib import Path
import datetime,hashlib,json,shutil,subprocess,zipfile
BASE=Path(__file__).resolve().parents[1];ROOT=BASE.parent;REPORT=BASE/'reports'
OLD=Path('/home/youns/workspace/ele548-project-v9');V10=Path('/home/youns/workspace/ele548-project-v10')
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def ref(p):return {'path':str(p),'sha256':sha(p)}
def put(p,v):
    with Path(p).open('x') as f:json.dump(v,f,indent=2);f.write('\n')
def mib(p):return int(subprocess.check_output(['du','-sk',str(p)],text=True).split()[0])/1024
def disk():
    values={str(p):mib(p) for p in [OLD,V10,ROOT]};combined=sum(values.values())/1024
    free=shutil.disk_usage(ROOT).free/1024**3
    assert values[str(ROOT)]<192 and combined<8 and combined+20.54370880126953<34 and free>=10
    return {'actual_worktree_MiB':values,'combined_worktrees_GiB':combined,
            'charged_total_GiB':combined+20.54370880126953,'free_GiB':free,
            'scope':'Inherited charged legacy20.5437088013GiB plus actual3 worktrees, not full original reference workspace'}
def main():
    gate_path=REPORT/'FAULT12_FINAL_GATES.json';gate=json.loads(gate_path.read_text())
    assert gate['status']=='PASS_ACTUAL12_AUDITED_PAIRED_REPLICATION_NOT_INDEPENDENT_COST_OR_HARDWARE_QUALIFICATION'
    assert gate['actual_global_CPU']==3487 and gate['new_fault_runs']==12
    candidates=[ROOT/'AGENTS.md',ROOT/'docs/00_LATEST_DECISIONS.ko.md',BASE/'README.ko.md',BASE/'PLAN.ko.md']
    for directory in ['src','tools','gem5_overlay','reports']:
        for p in sorted((BASE/directory).rglob('*')):
            if p.is_file() and not p.is_symlink() and '__pycache__' not in p.parts and p.suffix in {'.py','.hpp','.cpp','.cc','.hh','.md','.json','.csv'}:
                if p.name not in {'BUNDLE_MANIFEST.json','PACKAGE_VERIFICATION.json'}:candidates.append(p)
    suffixes={'.json','.csv','.ticks','.time','.log','.txt','.stdout','.stderr','.ini','.bib','.py'}
    for p in sorted((BASE/'runtime').rglob('*')):
        if p.is_file() and not p.is_symlink() and '__pycache__' not in p.parts and (p.suffix in suffixes or p.name in {'stdout','stderr'}):candidates.append(p)
    candidates=sorted(set(candidates))
    before=disk();size=sum(p.stat().st_size for p in candidates)
    assert before['actual_worktree_MiB'][str(ROOT)]+size/1024**2+2<192
    assert before['combined_worktrees_GiB']+size/1024**3+0.002<8
    members=[{'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':sha(p)} for p in candidates]
    manifest=REPORT/'BUNDLE_MANIFEST.json'
    put(manifest,{'status':'ACTUAL_PRIVATE_EVIDENCE_ALLOWLIST','at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  'gate':ref(gate_path),'packager':ref(Path(__file__)),'members':members,
                  'exclusions':['ELF/object/full source clone','Full HW1 traces and application inputs','PDK/library','PDFs','Environment dumps'],
                  'reproduction_scope':'Requires preserved local referenced inputs/objects; evidence bundle, not self-contained simulator install'})
    candidates.append(manifest)
    output=BASE/'artifacts/BP_SEU_V11_OVERWRITE_RESULTS.zip';output.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(output,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in candidates:z.write(p,str(p.relative_to(ROOT)))
    with zipfile.ZipFile(output) as z:
        assert z.testzip() is None
        assert len(z.infolist())==len(candidates)
        for entry in members:
            assert hashlib.sha256(z.read(entry['path'])).hexdigest()==entry['sha256']
    for item in json.loads((REPORT/'PRESERVATION.json').read_text())['preserved']:
        assert sha(item['path'])==item['sha256']
    after=disk()
    put(REPORT/'PACKAGE_VERIFICATION.json',{
        'status':'PASS_ARCHIVE_CRC_MEMBER_SHA_OLD_PRODUCER_PRESERVATION_AND_SCOPED_BUDGET_NOT_HARDWARE_QUALIFICATION',
        'archive':ref(output),'archive_bytes':output.stat().st_size,'member_count':len(candidates),
        'manifest':ref(manifest),'actual_global_CPU':3487,'new_CPU_or_EDA_dispatched_by_packager':0,
        'disk_before':before,'disk_after':after})
    print(json.dumps({'status':'PASS_PRIVATE_EVIDENCE_PACKAGE','archive':str(output),'sha256':sha(output),
                      'bytes':output.stat().st_size,'members':len(candidates),'disk_after':after}))
if __name__=='__main__':main()
