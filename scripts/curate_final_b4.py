#!/usr/bin/env python3
"""Collect B4 source candidates without editing their bytes or running them."""
import hashlib
import json
import pathlib
import posixpath
import re
import shutil

root=pathlib.Path(__file__).resolve().parents[1]
prefix='ele548-project-v15/query_controls_v15/runtime/protection-v18-worktree/finite_protection_v18'
primary=root/'recovered_static'/prefix
snapshot=primary/'producer_source/B4'
out=root/'final_b4'
assert not out.exists()
out.mkdir()
records=[]


def add(source,dest,kind):
    dest.parent.mkdir(parents=True,exist_ok=True)
    data=source.read_bytes();dest.write_bytes(data)
    records.append({'path':dest.relative_to(root).as_posix(),'source_candidate':source.relative_to(root).as_posix(),'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),'kind':kind,'rebuilt_or_tested':False})


for p in sorted(snapshot.rglob('*')):
    if p.is_file():add(p,out/p.relative_to(snapshot),'LATEST_B4_SNAPSHOT_TEXT_CANDIDATE')
for name in ('tools','continuation_b4/tools','continuation_4199/tools'):
    directory=primary/name
    if directory.is_dir():
        for p in sorted(directory.rglob('*.py')):add(p,out/name/p.relative_to(directory),'RECOVERED_BUILD_RUN_ANALYSIS_TOOL_NOT_EXECUTED')
for name in ('gem5_overlay/o3_protection_v18.py','gem5_overlay/observer_v18.py'):
    p=primary/name
    if p.is_file() and not(out/name).exists():add(p,out/name,'LIVE_OVERLAY_REFERENCE_FROZEN_CONFIG_NOT_PROVEN')

registry={}
for variant in ('recovered','recovered_static'):
    for p in (root/variant).rglob('*'):
        if p.is_file():registry['/home/youns/workspace/'+p.relative_to(root/variant).as_posix()]=p
available=[];missing=[]
search=['/home/youns/workspace/'+prefix+'/producer_source/B4/src','/home/youns/workspace/'+prefix+'/producer_source/B4/gem5_overlay/src','/home/youns/workspace/ele548-project-v9/src','/home/youns/workspace/ele548-project-v9/src/standalone']
queue=[p for p in sorted(snapshot.rglob('*')) if p.is_file() and p.suffix in ('.hpp','.h','.hh','.cpp','.cc')];seen=set()
while queue:
    p=queue.pop(0)
    if str(p) in seen:continue
    seen.add(str(p))
    variant='recovered_static' if str(p).startswith(str(root/'recovered_static')+'/') else 'recovered'
    original='/home/youns/workspace/'+p.relative_to(root/variant).as_posix()
    for include in re.findall(r'^\s*#include\s+"([^"]+)"',p.read_text(),re.M):
        candidates=[include] if include.startswith('/') else [posixpath.normpath(posixpath.dirname(original)+'/'+include)]+[s+'/'+include for s in search]
        found=next((k for k in candidates if k in registry),None)
        item={'requiring_source':p.relative_to(root).as_posix(),'include':include}
        if found:
            available.append({**item,'source_candidate':registry[found].relative_to(root).as_posix()})
            dependency=registry[found]
            if not str(dependency).startswith(str(snapshot)+'/'):
                rel=found.split('/workspace/',1)[1];dest=out/'support'/rel
                if not dest.exists():add(dependency,dest,'RECOVERED_TRANSITIVE_RESEARCH_DEPENDENCY_CANDIDATE')
                queue.append(dependency)
        else:
            category='UPSTREAM_OR_GENERATED_HEADER' if include.startswith(('cpu/','base/','sim/','params/','debug/','arch/','enums/')) else 'MISSING_RESEARCH_SOURCE'
            missing.append({**item,'status':category})

status={'status':'PARTIAL_FINAL_B4_SOURCE_RECOVERY_NOT_A_QUALIFIED_REBUILD','files':records,'resolved_quote_includes':available,'unresolved_quote_includes':missing,'simulations_executed':0,'original_completed_archive_recovered':False,'absolute_includes_preserved':True}
(out/'SOURCE_RECOVERY_MANIFEST.json').write_text(json.dumps(status,indent=2,ensure_ascii=False)+'\n')
research_missing=sorted(set(x['include'] for x in missing if x['status']=='MISSING_RESEARCH_SOURCE'))
text='''# 마지막 B4 코드 복구 후보

이 폴더는 과거 B4 스냅샷에 도달한 텍스트 후보를 따로 모은 것입니다. 알고리즘을 새로 구현하거나 바꾸지 않았고 코드 bytes와 원래 경로의 연결을 SOURCE_RECOVERY_MANIFEST.json에 보존했습니다. 빌드/실험을 다시 실행하지 않았습니다.

`src/`에는 유한 source service/controller/lookup/early receiver와 parity/ECC/TMR 보호 구현이 있습니다. `gem5_overlay/`에는 회수한 predictor/O3 연동이 있습니다. 테스트/runner도 원문 후보로 보관하되 실행하지 않았습니다.

당시 실제로 출력된 SHA와 일치한 B4 cpu.cc가 있지만, 전체 source lock이 되살아난 것은 아닙니다. 절대 include 경로를 임의로 바꾸지 않았으며, 아래 누락 연구 헤더와 upstream/generated dependency 때문에 현재 실행 가능한 완성본으로 판정하지 않습니다.

누락된 연구 include:
'''+''.join('- `'+s+'`\n' for s in research_missing)+'''
전체 과거 코드 후보는 상위 recovered_static/와 recovered/에 있습니다. 원시 실험 로그·ELF·원본 완료 ZIP은 복구되지 않았습니다. 예전에 다운로드한 2026-10-18 전체 인계 ZIP이 추가로 확보되면 실제 source snapshot과 대조해 복구를 보완할 수 있습니다.
'''
(out/'README.ko.md').write_text(text)
print(json.dumps({'curated_files':len(records),'missing_research_includes':research_missing,'resolved_include_refs':len(available),'unresolved_refs':len(missing)},ensure_ascii=False,indent=2))
