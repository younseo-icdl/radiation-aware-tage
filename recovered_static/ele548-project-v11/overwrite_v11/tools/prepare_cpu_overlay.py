#!/usr/bin/env python3
"""Create a new overlay; read-only dependency graph determines all consumers."""
from pathlib import Path
import hashlib,json,pickle,sys
import SCons.dblite
sys.dont_write_bytecode=True
BASE=Path(__file__).resolve().parents[1];ROOT=BASE.parent
OLD=Path('/home/youns/workspace/ele548-project-v9');GEM=OLD/'third_party/gem5-native-v9r2'
def sha(p,algorithm='sha256'):
    with p.open('rb') as f:return hashlib.file_digest(f,algorithm).hexdigest()
def ref(p):return {'path':str(p),'sha256':sha(p)}
def put(p,data):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x') as f:f.write(data)
def main():
    gate=json.loads((BASE/'reports/CPP_GATE.json').read_text());assert gate['status']=='PASS_FULL_PREDICTOR_CPP_FUNCTIONAL_NOT_CPU_TIMING'
    assert json.loads((BASE/'reports/PILOT_RESULT.json').read_text())['status'].startswith('PASS_')
    hh=GEM/'src/cpu/pred/research_native_v9r2_tage.hh';cc=hh.with_suffix('.cc')
    parent='v5::RepresentationAccess<RoundAccess>';new='v11::CpuSelectOverwrite<v5::RepresentationAccess<RoundAccess>>'
    text=hh.read_text();old_class='class CpuPipelineV9R2TAGEBase: public '+parent+' {'
    assert text.count(old_class)==1
    text=text.replace(old_class,'class CpuPipelineV9R2TAGEBase: public '+new+' {')
    # Bind immutable existing helpers explicitly, never recreate them in an old
    # mutable source checkout and never use symlinked output files.
    import re
    text=re.sub(r'"../../../../../src/([^\"]+)"',lambda m:'"'+str(OLD/'src'/m[1])+'"',text)
    text=text.replace('namespace bp {','#include "'+str(BASE/'src/cpu_select.hpp')+'"\nnamespace bp {',1)
    overlay=BASE/'gem5_overlay/src/cpu/pred';put(overlay/hh.name,text)
    body=cc.read_text();needle=':'+parent+'(p,p.representation,p.tap_budget)'
    assert body.count(needle)==1;body=body.replace(needle,':'+new+'(p,p.representation,p.tap_budget)')
    needle='    fatal_if(p.numThreads!=1'
    assert body.count(needle)==1
    body=body.replace(needle,'    fatal_if(overwrite_enabled&&(p.pipeline_mode!="native"||p.scheme!="P0"||p.role_policy!="LEGACY"||p.resource_mode!="LEGACY"||p.maintenance_cycles||p.check_cycles||p.repair_cycles||p.lookup_latency||p.journal_service),"Overwrite first integration is native C0/P0 only; timing/resource extensions require a new gate");\n'+needle)
    needle='out<<"{\\"journal_merge_undo\\":"'
    assert body.count(needle)==1
    body=body.replace(needle,'out<<"{\\"representation_overwrite\\":"<<int(overwrite_enabled)<<",\\"overwrite_forward_calls\\":"<<activity.forward_calls<<",\\"overwrite_undo_calls\\":"<<activity.undo_calls<<",\\"overwrite_tap_terms\\":"<<activity.fold_tap_terms<<",\\"overwrite_source_bits\\":"<<activity.source_bits_sampled<<",\\"overwrite_fold_bit_writes\\":"<<activity.fold_bit_writes<<",\\"journal_merge_undo\\":"')
    put(overlay/cc.name,body)
    config=OLD/'gem5/o3_native_v9r2.py';cfg=config.read_text();needle="choices=['recurrent','direct','geometric','stratum','short32']"
    assert cfg.count(needle)==1;cfg=cfg.replace(needle,"choices=['recurrent','direct','geometric','stratum','short32','overwrite']")
    put(BASE/'gem5_overlay/o3_overwrite_v11.py',cfg)
    compile(cfg,str(BASE/'gem5_overlay/o3_overwrite_v11.py'),'exec')
    dbpath=GEM/'build/X86_PIPELINE/gem5.build/sconsign'
    db=SCons.dblite.open(str(dbpath),'r');consumers=[]
    for directory in db.keys():
        for name,e in pickle.loads(db[directory]).items():
            if name.endswith('.o') and getattr(e,'binfo',None) and 'src/cpu/pred/research_native_v9r2_tage.hh' in e.binfo.bimplicit:
                assert len(e.binfo.bsources)==1
                consumers.append({'object':str(GEM/directory/name),'source':str(GEM/e.binfo.bsources[0]),'implicit':[str(GEM/p) if not p.startswith('/') else p for p in e.binfo.bimplicit]})
    assert len(consumers)==3,'UNEXPECTED_ABI_CONSUMER_SET_REVIEW_BEFORE_BUILD'
    entry=pickle.loads(db['build/X86_PIPELINE'])['gem5.opt'];objects=[]
    for name,sig in zip(entry.binfo.bsources,entry.binfo.bsourcesigs):
        p=GEM/name;assert p.is_file()
        assert sha(p,'md5')==sig.csig,('OLD_LINK_INPUT_CHANGED',str(p))
        objects.append(ref(p))
    assert len(objects)==1516
    assert sha(GEM/'build/X86_PIPELINE/gem5.opt')=='194c022c89cda8754d9fdafd787338b51ab81b6e4438a9fdbd7870256f962330'
    libraries=[Path(p) for p in entry.binfo.bimplicit if p.endswith('.a') and p.startswith('build/')]
    lock={'status':'PREPARED_OVERWRITE_CPU_OVERLAY_NOT_BUILT_OR_EXECUTED','gate':ref(BASE/'reports/CPP_GATE.json'),'pilot':ref(BASE/'reports/PILOT_RESULT.json'),
          'old_header':ref(hh),'old_source':ref(cc),'old_config':ref(config),'old_binary':ref(GEM/'build/X86_PIPELINE/gem5.opt'),
          'scons_database':ref(Path(str(dbpath)+'.dblite')),'abi_consumers':consumers,'immutable_link_objects':objects,
          'static_libraries':[ref(GEM/p) for p in libraries],
          'new_files':[ref(p) for p in sorted((BASE/'gem5_overlay').rglob('*')) if p.is_file()],
          'mixin_sources':[ref(BASE/'src/overwrite.hpp'),ref(BASE/'src/cpu_select.hpp')],
          'implementation_scope':'Native C0 functional regression only; no full timing/finite-service model or CPU performance winner',
          'fault_manifest':'Same active logical state as recurrent P0;200fold bits retained. Fixed build configuration and software observer counters excluded; original trusted helper exclusions retained. No claim for physical retention/control safety.',
          'build_strategy':'New objects for all3 original-header consumers, immutable remaining1513objects and existing7staticlibs, new output only. No old source/config/object/binary writes. Manual incremental link must be reported separately from original SCons build.'}
    path=BASE/'reports/CPU_OVERLAY.lock.json';put(path,json.dumps(lock,indent=2)+'\n')
    print(json.dumps({'status':lock['status'],'consumers':len(consumers),'immutable_objects':len(objects),'static_libraries':len(libraries),'overlay':str(overlay)},indent=2))
if __name__=='__main__':main()
