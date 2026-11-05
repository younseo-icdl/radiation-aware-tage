import json,csv,concurrent.futures,os
from continuation_common import *
from run_o3_public_baseline import stats
binary=ROOT/'third_party/gem5-continuation/build/X86_STAGE0/gem5.opt'
selection=json.loads((OUT/'configs/policy_selection.lock.json').read_text())['selection']
kN=int(selection['N1'].split('k')[-1]);kH=int(selection['H1'].split('k')[-1])
old=json.loads((ROOT/'reports/E3_INTEGRATION_GATE.json').read_text());baseline=next(r for r in old['cases'] if r['case']=='clean_P0')
reads=list(csv.DictReader((ROOT/'reports/e3_integration/gate/clean_P0/prediction_reads.csv').open()));tick=int(reads[90]['tick'])
manifestH=json.loads((OUT/f'configs/manifest_H1_k{kH}.json').read_text())
def site(structure,word=None):return next(s['id'] for s in manifestH['additional_sites'] if s['structure']==structure and (word is None or s['word']==word))
specs=[(f'legacy_{s}',s,'LEGACY',0,0,0,[]) for s in ['P0','P_ED','P_ECC','P_TMR']]
specs += [('N1_clean_C0','P_ED','N1',kN,0,0,[]),('N1_clean_C1','P_ED','N1',kN,1,0,[]),('N1_maintenance','P_ED','N1',kN,1,1,[]),('H1_clean_C0','P_ED','H1',kH,0,0,[]),('H1_maintenance','P_ED','H1',kH,1,1,[])]
for label,ids in [('raw',[65054]),('fold',[65170]),('parity',[65370]),('progress',[65434]),('even',[65170,65171])]:specs.append(('N1_'+label,'P_ED','N1',kN,1,0,[(tick,ids)]))
specs += [('N1_cancel','P_ED','N1',kN,0,0,[(tick,[65170]),(tick,[65170])])]
for label,ids in [('raw',[65054]),('fold',[65170]),('DUE',[65024,65025]),('shadow',[site('committed_source',0)]),('shadow_DUE',[site('committed_source',0),site('committed_source',0)+1]),('source_fold',[65054,65170]),('phase',[site('rebuild_phase')+7])]:specs.append(('H1_'+label,'P_ED','H1',kH,1,1,[(tick,ids)]))
out=OUT/'reports/cpu_gate';out.mkdir(parents=True,exist_ok=True);env=os.environ.copy();env['LD_LIBRARY_PATH']='/opt/miniconda3/lib'+(':'+env['LD_LIBRARY_PATH'] if env.get('LD_LIBRARY_PATH') else '')
results=[]
def run(spec):
 label,scheme,policy,k,C,U,events=spec;d=out/label;d.mkdir(exist_ok=True);schedule=d/'schedule.ticks';schedule.write_text(''.join(str(t)+' '+ ';'.join(map(str,ids))+'\n' for t,ids in events))
 cmd=[binary,'--outdir='+str(d),ROOT/'gem5/o3_continuation.py','--binary',ROOT/'build/checksum_freestanding','--scheme',scheme,'--role-policy',policy,'--inspection-interval',str(k),'--check-cycles',str(C),'--maintenance-cycles',str(U),'--repair-cycles','0' if scheme=='P0' else '4','--schedule',schedule,'--read-log']
 r=timed(cmd,d/'gem5.log',timeout=240,env=env);r.update(case=label,scheme=scheme,policy=policy,k=k,check=C,maintenance=U,output=str(d.relative_to(ROOT)),status='FAIL_EXECUTION')
 if r['exit_code']:return r
 try:
  assert (d/'program.stdout').read_text().strip()=='checksum=1321703870693' and not (d/'program.stderr').read_bytes()
  assert 'Exit cause: exiting with last active thread context code: 0' in (d/'gem5.log').read_text()
  st=stats(d/'stats.txt');seu=json.loads((d/'seu.json').read_text());m=json.loads((d/'logical_manifest.json').read_text());expected=json.loads((OUT/f"configs/manifest_{policy+'_k'+str(k) if policy in ['N1','H1'] else scheme}.json").read_text())['CPU_total_bits']
  assert m['total_bits']==expected
  assert seu['applied_events']==len(events)
  actual=list(csv.DictReader((d/'events.csv').open()));assert len(actual)==len(events)
  for a,(t,ids) in zip(actual,events):assert int(a['tick'])==t and list(map(int,a['site_ids'].split(';')))==ids and a['XOR_verified']=='1'
  if label.startswith('legacy_') or label in ['N1_clean_C0','H1_clean_C0','N1_cancel']:
   assert int(st['system.cpu.numCycles'])==baseline['cycles']
   for key in ['canonical_base_state_hash','predictor_rng_draws','predictor_rng_hash']:assert seu[key]==baseline['seu'][key],key
  if 'clean' in label or 'maintenance' in label:assert seu['detected']==0,'false alarm'
  if label in ['N1_raw','N1_fold','N1_parity']:assert seu['reset_refill']>0 and seu['detected']>0
  if label in ['N1_even','N1_cancel']:assert seu['detected']==0
  if label in ['H1_raw','H1_fold','H1_source_fold']:assert seu['rebuild_requests']>0 and seu['rebuild_source_bits']>0 and seu['rebuild_writes']>0
  if label in ['H1_DUE','H1_shadow_DUE']:assert seu['DUE']>0 and seu['reset_refill']>0
  if U:assert seu['maintenance_hold_cycles']>0 and 0<seu['max_update_queue']<=16
  rebuild=list(csv.DictReader((d/'events.csv.rebuild.csv').open()));assert len({r['tick'] for r in rebuild})==len(rebuild),'multiple scan steps per tick'
  assert all(int(x['source_bits_delta'])<=16 and int(x['rebuild_writes_delta'])<=1 for x in rebuild)
  r.update(status='PASS',cycles=int(st['system.cpu.numCycles']),seu=seu,stats_sha256=sha(d/'stats.txt'),seu_sha256=sha(d/'seu.json'),manifest_sha256=sha(d/'logical_manifest.json'),rebuild_log_sha256=sha(d/'events.csv.rebuild.csv'))
 except Exception as e:r.update(status='FAIL_VALIDATION',error=str(e))
 return r
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
 for r in pool.map(run,specs):
  results.append(r);write(OUT/'reports/G4_CPU_GATE.json',dict(status='RUNNING',cases=results,binary_sha256=sha(binary),planned=len(specs)));print(r['case'],r['status'],r.get('error',''),flush=True)
  if r['status']!='PASS':break
assert len(results)==len(specs) and all(r['status']=='PASS' for r in results)
write(OUT/'reports/G4_CPU_GATE.json',dict(status='PASS',cases=results,binary_sha256=sha(binary),source_lock_sha256=sha(OUT/'configs/gem5_source.lock.json'),planned=len(specs),host_core_hours=sum(r['host_cpu_seconds'] for r in results)/3600,scope='synthetic functional/protocol gate, not representative performance'))
print('PASS',len(specs),'real O3 gates')
