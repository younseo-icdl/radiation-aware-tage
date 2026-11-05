"""Corrected V8 replication and owner holdout; no simulator or inferred success."""
from pathlib import Path
import collections,hashlib,json,statistics
import pipeline_v6_analyze as stats
from pipeline_v8_common import ROOT,OUT,PHASE_COUNTS,FAILURE_RETENTION_POLICY,sha,write
from pipeline_v8_campaign import semantic_map
RESULTS=ROOT/'rate_state_v5_pipeline_v8/results';V6=ROOT/'rate_state_v5_pipeline/runtime';V7=ROOT/'rate_state_v5_pipeline_v7/runtime'
TERMINAL={'PASS','COMPLETED_WITH_FAILED_RUNS'}
def require(ok,message):
 if not ok:raise RuntimeError('V8_ANALYSIS: '+str(message))
def load(path):
 d=json.loads(path.read_text());require(isinstance(d,dict),('NON_OBJECT',str(path)));return d
def ref(path):return dict(path=str(path.relative_to(ROOT)),sha256=sha(path))
def key(r):return tuple(r.get(k) for k in ['program','scenario','owner','id'])
def resolve(phase):
 original=OUT/'reports'/(phase+'.json');lock=OUT/'configs'/(phase+'.lock.json');merged=OUT/'reports'/(phase+'_COMPLETE.json')
 if not merged.exists():return original,load(original),None
 d=load(merged);c=d.get('continuation',{});require(d.get('status')=='COMPLETED_WITH_FAILED_RUNS','NONTERMINAL_MERGED_VIEW')
 expected={'prefix_report':original,'full_task_lock':lock,'remainder_report':OUT/'reports'/(phase+'_REMAINDER.json'),'remainder_task_lock':OUT/'configs'/(phase+'_REMAINDER.lock.json'),'producer_lock':OUT/'configs/PRODUCER.lock.json','continuation_lock':OUT/'configs'/(phase+'_CONTINUATION.lock.json')};docs={}
 for k,p in expected.items():require(c.get(k)==ref(p),('CONTINUATION_REF_CHANGED',k));docs[k]=load(p)
 prefix,suffix,frozen,tail,decl=map(docs.get,['prefix_report','remainder_report','full_task_lock','remainder_task_lock','continuation_lock']);n=len(prefix['tasks'])
 require(prefix['status']=='FAIL_RETAINED' and suffix['status'] in TERMINAL and 0<n<len(frozen['tasks']),'INVALID_CONTINUATION_PREFIX_SUFFIX')
 require(c['prefix_count']==n and c['remainder_count']==len(suffix['tasks']) and tail['tasks']==decl['tasks']==frozen['tasks'][n:],'CHANGED_CONTINUATION_TASKS')
 require(d['tasks']==prefix['tasks']+suffix['tasks'] and [key(r) for r in d['tasks']]==[key(t) for t in frozen['tasks']],'MERGED_TASKS_CHANGED')
 for k in ['prefix_report','full_task_lock','producer_lock']:require(decl[k]==c[k],('CONTINUATION_DECLARATION_CHANGED',k))
 for k in ['binary_sha256','config_sha256']:require(frozen[k]==tail[k]==docs['producer_lock'][k],'CONTINUATION_PRODUCER_CHANGED')
 return merged,d,c

def load_phase(phase):
 path,d,continuation=resolve(phase);lock_path=OUT/'configs'/(phase+'.lock.json');frozen=load(lock_path);tasks=frozen['tasks'];rows=d['tasks'];count=PHASE_COUNTS[phase]
 require(d['status'] in TERMINAL and d.get('planned')==len(rows)==len(tasks)==count,('PHASE_INCOMPLETE',phase))
 actual={key(r):r for r in rows};expected={key(t):t for t in tasks}
 require(len(actual)==len(expected)==count and actual.keys()==expected.keys(),('FROZEN_TASK_SET_CHANGED',phase))
 for k,r in actual.items():
  t=expected[k]
  for f,v in t.items():
   if f not in ['input','events_text']:require(r.get(f)==v,('TASK_FIELD_CHANGED',phase,f))
  require(r['producer_binary_sha256']==frozen['binary_sha256'] and r['config_sha256']==frozen['config_sha256'],'PRODUCER_CHANGED')
  require(r['input_sha256']==t['input']['input_sha256'] and r['program_binary_sha256']==t['input']['binary_sha256'],'INPUT_CHANGED')
  require(r['schedule_sha256']==hashlib.sha256(t.get('events_text','').encode()).hexdigest(),'TAPE_CHANGED')
  require(r['status']=='PASS' or r['status'].startswith('FAIL'),'NONTERMINAL_TASK')
  if r['status']=='PASS':require(r.get('cycles',0)>0 and r.get('instructions',0)>0 and r.get('failure') is None,'INVALID_PASS')
 return rows,dict(phase=phase,report=ref(path),task_lock=ref(lock_path),actual_runs=count,continuation=continuation)

def check_pairs(rows,policies,owners):
 programs=sorted({r['program'] for r in rows});require(set(programs)=={'qsort_small','dijkstra_small','sha1'},'PROGRAM_SET_CHANGED')
 for scenario in sorted({r['scenario'] for r in rows}):
  for p in programs:
   selected=[r for r in rows if r['program']==p and r['scenario']==scenario];sets=[{r['owner'] for r in selected if r['id']==i} for i in policies]
   require(len(selected)==len(policies)*owners and all(len(s)==owners and s==sets[0] for s in sets),'PAIRED_OWNERS_INCOMPLETE')
 return programs

def validate_holdout(phases):
 frozen_path=OUT/'configs/CANDIDATE_FROZEN.lock.json';frozen=load(frozen_path);maps_path=OUT/'configs/OWNER_HOLDOUT_maps.lock.json';maps=load(maps_path)['maps'];owner_path=OUT/'configs/OWNER_HOLDOUT_owners.lock.json';owner_lock=load(owner_path)
 require(frozen['producer_sha256']==sha(OUT/'configs/PRODUCER.lock.json') and frozen['holdout_master_base']==7215480000 and frozen['primary_L']==frozen['II']==1,'CANDIDATE_CHANGED')
 require(owner_lock['candidate_sha256']==sha(frozen_path) and owner_lock['maps_sha256']==sha(maps_path),'HOLDOUT_PROVENANCE_CHANGED')
 cleans={(r['program'],r['id']):r for r in phases['EVALUATION_CLEAN']};raw=next(w['site_ids'] for w in load(ROOT/'sources/protection_scope.lock.json')['payload_words'] if len(w['site_ids'])==130)
 for ident in ['P_REC_L1','P_DIR_L1']:
  for p in ['qsort_small','dijkstra_small','sha1']:
   r=cleans[p,ident];path=ROOT/r['output']/'logical_manifest.json';require(sha(path)==r['hashes']['logical_manifest.json'],'MANIFEST_CHANGED');require(maps[ident]==semantic_map(load(path)),'HOLDOUT_MAP_NOT_ACTUAL_MANIFEST')
 union=set().union(*(set(v) for v in maps.values()));witnesses=owner_lock['owners'];owners={(w['program'],w['scenario'],w['owner']):w for w in witnesses};rows=phases['OWNER_HOLDOUT']
 require(len(owners)==len(witnesses)==48 and set(owners)=={key(r)[:3] for r in rows},'HOLDOUT_OWNER_COVERAGE')
 old_masters={w['master'] for doc in [V6/'configs/EVALUATION_owners.lock.json',V7/'configs/OWNER_HOLDOUT_owners.lock.json'] for w in load(doc)['owners']};seen=set()
 for k,w in owners.items():
  require(w['master'] not in old_masters|seen,'OWNER_SEED_REUSED');seen.add(w['master']);p,scenario,_=k
  selected=[r for r in rows if key(r)[:3]==k];H=max(cleans[p,i]['cycles'] for i in ['NATIVE','P_REC_L1','P_DIR_L1']);rate=1/cleans[p,'NATIVE']['cycles'] if scenario=='SOURCE' else 1.05e-14*20/3600*1e15*len(union)/2e9
  require(w['cap_cycles']==4*H and w['clock_Hz']==2000000000 and w['cycle_ticks']==500,'HOLDOUT_TIME_CHANGED')
  require(__import__('math').isclose(w['lambda_union_or_target_per_cycle'],rate,rel_tol=1e-12),'HOLDOUT_RATE_CHANGED')
  for r in selected:
   events=[dict(tick=e['tick'],sites=e['sites']) for e in w['latent']] if scenario=='SOURCE' else [dict(tick=e['tick'],sites=[maps[r['id']][e['site_key']]]) for e in w['latent'] if e['site_key'] in maps[r['id']]]
   if scenario=='SOURCE':require(all(e['K'] in [1,2] and len(e['sites'])==e['K'] and any(e['sites']==raw[j:j+e['K']] for j in range(131-e['K'])) for e in w['latent']),'SOURCE_K_SPAN_CHANGED')
   require(events==w['accepted'][r['id']],'LATENT_THINNING_CHANGED');text=''.join(str(e['tick'])+' '+';'.join(map(str,e['sites']))+'\n' for e in events);require(hashlib.sha256(text.encode()).hexdigest()==r['schedule_sha256'],'ACCEPTED_TAPE_CHANGED')
 return [ref(p) for p in [frozen_path,maps_path,owner_path]]

def validate_journal(phases):
 frozen_path=OUT/'configs/CANDIDATE_FROZEN.lock.json';frozen=load(frozen_path);mp=OUT/'configs/JOURNAL_HOLDOUT_maps.lock.json';op=OUT/'configs/JOURNAL_HOLDOUT_owners.lock.json';maps=load(mp)['maps'];decl=load(op)
 require(frozen['journal_holdout_master_base']==7315480000 and frozen['journal_policies']==['P_DIR_L1','JOURNAL_PIPE_L1'],'JOURNAL_CANDIDATE_CHANGED')
 require(decl['candidate_sha256']==sha(frozen_path) and decl['maps_sha256']==sha(mp),'JOURNAL_PROVENANCE_CHANGED')
 clean={(r['program'],r['id']):r for r in phases['JOURNAL_CLEAN']};native={(r['program'],r['id']):r for r in phases['EVALUATION_CLEAN']};policies=frozen['journal_policies']
 for p in ['qsort_small','dijkstra_small','sha1']:
  for i in policies:require(maps[i]==semantic_map(load(ROOT/clean[p,i]['output']/'logical_manifest.json')),'JOURNAL_ACTUAL_MANIFEST_CHANGED')
 union=set().union(*(set(v) for v in maps.values()));owners={(w['program'],w['scenario'],w['owner']):w for w in decl['owners']};require(len(owners)==24,'JOURNAL_OWNERS_CHANGED')
 old={w['master'] for doc in [V6/'configs/EVALUATION_owners.lock.json',V7/'configs/OWNER_HOLDOUT_owners.lock.json',OUT/'configs/OWNER_HOLDOUT_owners.lock.json'] for w in load(doc)['owners']};seen=set()
 for row in phases['JOURNAL_HOLDOUT']:
  w=owners[key(row)[:3]];p=row['program'];require(w['master'] not in old,'JOURNAL_OWNER_REUSE')
  H=max(native[p,'NATIVE']['cycles'],*[clean[p,i]['cycles'] for i in policies]);rate=1.05e-14*20/3600*1e15*len(union)/2e9
  require(w['cap_cycles']==4*H and w['clock_Hz']==2000000000 and w['cycle_ticks']==500 and __import__('math').isclose(rate,w['lambda_union_or_target_per_cycle'],rel_tol=1e-12),'JOURNAL_RATE_TIME_CHANGED')
  events=[dict(tick=e['tick'],sites=[maps[row['id']][e['site_key']]]) for e in w['latent'] if e['site_key'] in maps[row['id']]]
  require(events==w['accepted'][row['id']],'JOURNAL_THINNING_CHANGED');text=''.join(str(e['tick'])+' '+';'.join(map(str,e['sites']))+'\n' for e in events)
  require(hashlib.sha256(text.encode()).hexdigest()==row['schedule_sha256'],'JOURNAL_TAPE_CHANGED')
 return [ref(mp),ref(op)]
def journal_aggregate(phases,programs):
 # Alias IDs only for the unchanged paired-statistics implementation; restore actual policy labels afterwards.
 aliases={'P_DIR_L1':'P_REC_L1','JOURNAL_PIPE_L1':'P_DIR_L1'}
 def remap(rows):
  return [dict(r,id=aliases[r['id']]) for r in rows]
 jc=remap(phases['JOURNAL_CLEAN']);jf=remap(phases['JOURNAL_HOLDOUT'])
 abcd,summary=stats.aggregate(dict(PILOT=[],CLEAN_SCREEN=jc,EVALUATION_CLEAN=jc,EVALUATION_FAULT=jf),programs)
 reverse={v:k for k,v in aliases.items()}
 for collection in [abcd,summary]:
  for r in collection:
   r['phase']='JOURNAL_HOLDOUT';r['cohort_scope']='independent journal owners; atomic versus finite source backend, exact same direct algorithm/L1/II1; not pure protection cause'
   for field in ['policy','reference','baseline','left','right']:
    if r.get(field) in reverse:r[field]=reverse[r[field]]
   if r.get('policy')=='MATCHED_REPRESENTATION':r['policy']='FINITE_JOURNAL_BACKEND_COST'
   if 'contrast' in r:r['contrast']=r['contrast'].replace('P_REC_L1','ATOMIC_DIRECT_L1').replace('P_DIR_L1','FINITE_JOURNAL_DIRECT_L1')
 return abcd,summary

def replication_table(phases):
 old_path=V7/'reports/V6_REPLICATION.json';old=load(old_path)['tasks'];old_by={key(r):r for r in old};witness=load(OUT/'configs/V7_REPLICATION_replication.lock.json')['rows'];table=[]
 for r,w in zip(phases['V7_REPLICATION'],witness):
  require(key(r)==(w['program'],w['scenario'],w['owner'],w['id']),'REPLICATION_WITNESS_CHANGED');before=old_by[(r['program'],r['scenario'],w['original_owner'],r['id'])]
  require(r['schedule_sha256']==w['mapping']['new_schedule_sha256'] and before['schedule_sha256']==w['mapping']['old_schedule_sha256'],'REPLICATION_TAPE_BINDING_CHANGED')
  if r['scenario']=='SOURCE':require(w['mapping']['numeric_tape_identical'],'SOURCE_TAPE_CHANGED')
  table.append(dict(program=r['program'],scenario=r['scenario'],owner=r['owner'],policy=r['id'],v7_status=before['status'],v8_status=r['status'],v7_cycles=before.get('cycles') if before['status']=='PASS' else None,v8_cycles=r.get('cycles') if r['status']=='PASS' else None,delta_cycles=r['cycles']-before['cycles'] if stats.successful(r,before) else None,numeric_tape_identical=w['mapping']['numeric_tape_identical'],scope='known-case replication; no added-ECC exposure inference',v7_output=before['output'],v8_output=r['output']))
 return table

def report(phases,summary,throughput,replication,safety):
 text='''# V8 corrected source-head/FIFO: replication and independent event owners\n\nIMPLEMENTED/TESTED RESULT. Original v5/v6/v7 raw/producer/locks remain preserved. The private source-head/FIFO correction is evaluated as one implementation change; this is not a new TAGE algorithm or measured physical PPA. All predeclared CPU tasks are terminal before this report. New400/global3200 CPU, new12/global108 core-hours,8shared slots,new8/combined34GiB limits are audit requirements, not measured outcomes.\n\nV7_REPLICATION uses the exact prior inputs, owners, event times and old semantic targets. SOURCE tapes are byte-identical. If added ECC storage shifts numeric IDs, existing field/bit semantics are mapped and recorded. This known-case replay is not an independent selection/evaluation cohort and does not expose newly added ECC storage. OLD_FAILURE_REPLAY repeats3 previously failed tasks twice as deterministic checks, not6 independent owners. Old failures have no imputed cycles or slowdown.\n\nOWNER_HOLDOUT uses8 disjoint event owners per3program×SOURCE/WHOLE, on the previously seen v7 inputs. It is an owner holdout, not an input or workload holdout. SOURCE retains CHARM205:9 multiplicity with independently assumed Poisson timing and lambda=1/native clean cycles. WHOLE uses the actual augmented v8 logical manifest including added check/control bits, a hypothetical per-bit reference×1e15, common union latent marks and architecture thinning. Neither is calibrated target/mission rate or a full physical CPU inventory.\n\n## Normal cost\n\n2% engineering overhead is against native L0, not the matched P_REC_L1 reference. Shared L1 delay can exceed that budget even if direct/rec matched C/A is0. Normal cycle counts do not prove physical ports/clockability.\n\n|program|native L0 cycles|P_REC_L1 overhead %|P_DIR_L1 overhead %|matched direct/rec %|\n|---|---:|---:|---:|---:|\n'''
 clean={(r['program'],r['id']):r for r in phases['EVALUATION_CLEAN']}
 for p in ['qsort_small','dijkstra_small','sha1']:
  a,b,c=(clean[p,i] for i in ['NATIVE','P_REC_L1','P_DIR_L1']);v=[100*(b['cycles']/a['cycles']-1),100*(c['cycles']/a['cycles']-1),100*(c['cycles']/b['cycles']-1)] if stats.successful(a,b,c) else [None]*3
  text+=f"|{p}|{a.get('cycles')}|"+'|'.join(stats.number(x) for x in v)+'|\n'
 text+='''\n## Paired results\n\nA/B=clean/fault P_REC_L1, C/D=clean/fault P_DIR_L1; gain=100(B−D)/A, normal=100(C−A)/A, residual=100(D−C)/A. DID is fault-attributable damage reduction including representation/exposure/timing interactions, not pure repair causality. Signed helpful/zero/future events remain. Owner bootstrap10,000 nominal95% CI; no CI-overlap significance test and no equivalence from an interval containing0. Program macro uses equal fixed-program weight. Failed owners stay in rows/failure counts; performance is survivor-conditional if any pair fails, and a whole failed program is not dropped. Pilot n1 has no CI.\n\n|cohort|program|condition|policy|valid/planned|gain pp [95% CI]|residual pp|\n|---|---|---|---|---:|---:|---:|\n'''
 for r in summary:
  if r['kind']=='ABCD_GAIN' and r['policy'] in ['P_DIR_L1','JOURNAL_PIPE_L1'] and r['phase']!='PILOT':text+=f"|{r['phase']}|{r['program']}|{r['scenario']}|{r['policy']}|{r['n_valid']}/{r['n_planned']}|{stats.number(r['mean_pp'])} [{stats.number(r['CI_low_pp'])}, {stats.number(r['CI_high_pp'])}]|{stats.number(r['mean_residual_pp'])}|\n"
 text+='\n## Old failures and corrected metadata gates\n\n|program|condition|owner/policy|v7 status|v8 status|\n|---|---|---|---|---|\n'
 for r in replication:
  if r['v7_status']!='PASS':text+=f"|{r['program']}|{r['scenario']}|{r['owner']} / {r['policy']}|{r['v7_status']}|{r['v8_status']}|\n"
 text+='\nJOURNAL_HOLDOUT uses A/B=clean/fault exact direct atomic source, C/D=clean/fault exact direct finite journal, same lookup L1/II1. This changes the source publication/resource backend and storage exposure; it is not a pure mirror-protection causal estimate or lookup-pipeline change. Journaling overhead and fault recovery stay separate from main recurrent/direct comparison.\n'
 text+='\n|program|atomic direct L1 cycles|finite journal direct L1 cycles|finite normal overhead %|\n|---|---:|---:|---:|\n'
 journal_clean={(r['program'],r['id']):r for r in phases['JOURNAL_CLEAN']}
 for p in ['qsort_small','dijkstra_small','sha1']:
  a,c=(journal_clean[p,i] for i in ['P_DIR_L1','JOURNAL_PIPE_L1']);overhead=100*(c['cycles']/a['cycles']-1) if stats.successful(a,c) else None
  text+=f"|{p}|{a.get('cycles')}|{c.get('cycles')}|{stats.number(overhead)}|\n"
 text+='\nSource head and FIFO protection use two physical SECDED codewords. The declared lossless recovery guarantee is at most two corrupt physical bits total in the paired codewords before repair, not arbitrary3+ or independent two-bit allowance per copy. Newly added check/mirror storage is exposed in WHOLE. Normal parallel decoding/repair ports and stage-fit remain model assumptions.\n'
 text+='\n## Retained execution failures\n\nWHOLE remains K1 per event; repeated physical upsets before repair can accumulate. Only the predeclared typed decoder exceptions may continue the WHOLE fault cohort. They remain failed executions with no cycles/imputation and invalidate matched performance pairs. The exception alone does not prove a3+ causal history. SOURCE K1/K2, clean/correctness and original R5 failure-replay cases still stop on any failure.\n\n|phase|program|condition|owner/policy|status|observed decoder message|\n|---|---|---|---|---|---|\n'
 failures=[r for rows in phases.values() for r in rows if r['status']!='PASS']
 for r in failures:
  text+=f"|{r['phase']}|{r['program']}|{r['scenario']}|{r['owner']} / {r['id']}|{r['status']}|{r.get('failure_retention',{}).get('what',r.get('failure','unclassified'))}|\n"
 if not failures:text+='|none|—|—|—|—|—|\n'
 text+='\n## Source-head/FIFO regression\n\n|case|policy|old status|v8 status|cycles|\n|---|---|---|---|---:|\n'
 for r in phases['SOURCE_FAILURE_REPLAY']:
  text+=f"|{r['scenario']}|{r['id']}|FAIL_EXECUTION (retained)|{r['status']}|{r.get('cycles')}|\n"
 text+=f"\nSOURCE_HEAD_FIFO_GATE: `{load(OUT/'reports/SOURCE_HEAD_FIFO_GATE.json')['status']}`; CPU_GATE_SOURCE: {sum(r['status']=='PASS' for r in phases['CPU_GATE_SOURCE'])}/{len(phases['CPU_GATE_SOURCE'])}. These are declared software safety cases, not physical qualification.\n"
 text+=f"\n[METADATA_SAFETY_GATE]({OUT/'reports/METADATA_SAFETY_GATE.json'}) status: `{safety['status']}`. Corrected CPU_GATE_FAULT tasks passed: {sum(r['status']=='PASS' for r in phases['CPU_GATE_FAULT'])}/{len(phases['CPU_GATE_FAULT'])}. Passing declared SBU/DUE/lifetime gates is scoped evidence, not universal multi-bit safety or hardware qualification. SECDED3+ and excluded CPU/control storage remain outside guaranteed correction. A no-SEU finite-lifetime failure in v6 was a common transport limitation, not intrinsic recurrent-TAGE unsafety or proof direct was safe. Prior6 R5 metadata failures,3 v6 deliberate metadata failures and3 v6 campaign failures remain immutable evidence.\n"
 clean_rows=[r for r in throughput if r['phase'] in ['CLEAN_SCREEN','EVALUATION_CLEAN'] and r.get('pipeline_mode')=='pipeline' and r['status']=='PASS'];overlap=sum(r['observed_CPU_overlap'] is True for r in clean_rows)
 text+=f'''\n## Throughput and scope\n\nClean pipeline executions with maxinflight>1: {overlap}/{len(clean_rows)}. Fault occupancy is separately labeled per row and cannot establish normal CPU utilization, especially after WHOLE control errors. Coupled next-PC/history can keep CPU outstanding at1 even when engine unit tests demonstrate multi-request capacity. THROUGHPUT records accepted/produced/consumed per CPU end cycle, actual spacing, outstanding and wait counters. Readiness-false calls aggregate issue/full/source/dependency waits; inherited source/response waits overlap and are not an additive CPI decomposition. The wrapper, not generic engine consume(), enforces issue/consume ports.\n\nCommon synchronous append and inherited rollback/training write-port assumptions are distinct from the finite-journal clean control. Same-L single/pipeline isolates capacity; same-backend L1/L2 is latency sensitivity. Journal-single/pipeline keeps the same journal. Old R5 READ1 versus new stages also changes ordering, not only capacity. Normal protection work within declared L and finite correction/recovery hold are CPU model assumptions; physical area/energy/timing are unmeasured. Source metadata and FIFO recovery gates are reported separately from transport gates.\n\nDONE: actual declared phases, old-tape mapping, disjoint-owner augmented exposure and paired analysis. NOT DONE: full physical inventory, arbitrary high-multiplicity guarantee, RTL/PDK/clockability/PPA/missionFIT. No TCAD/Cadence/SPICE/RTL run. **No fully qualified physical hardware winner is declared.** New software gate success and failure conditions are reported as observed; no new scheme is assumed better.\n'''
 return text

def main():
 require(load(OUT/'configs/ROUND_PREDECLARED.lock.json')['failure_retention_policy']==FAILURE_RETENTION_POLICY,'FAILURE_RETENTION_POLICY_CHANGED')
 phases={};provenance=[]
 for phase in PHASE_COUNTS:
  phases[phase],p=load_phase(phase);provenance.append(p)
 require(sum(len(r) for r in phases.values())==sum(PHASE_COUNTS.values()),'PREDECLARED_ROUND_INCOMPLETE')
 require(all(r['status']=='PASS' for p in ['CPU_GATE_BASE','CPU_GATE_FAULT','CPU_GATE_SOURCE_CLEAN','CPU_GATE_SOURCE','CLEAN_SCREEN','PILOT','EVALUATION_CLEAN'] for r in phases[p]),'SOFTWARE_CORRECTNESS_GATE_NOT_PASS')
 safety=load(OUT/'reports/METADATA_SAFETY_GATE.json');require(safety['status'].startswith('PASS'),'FULL_METADATA_SAFETY_GATE_NOT_PASS')
 require(len(phases['CLEAN_SCREEN'])==36 and len({(r['program'],r['id']) for r in phases['CLEAN_SCREEN']})==36,'CLEAN_GRID_CHANGED')
 require({r['scenario'] for r in phases['OWNER_HOLDOUT']}=={'SOURCE','WHOLE'},'HOLDOUT_CONDITIONS_CHANGED')
 programs=check_pairs(phases['OWNER_HOLDOUT'],['P_REC_L1','P_DIR_L1'],8);check_pairs(phases['V7_REPLICATION'],['P_REC_L1','P_DIR_L1'],8);check_pairs(phases['PILOT'],['P_REC_L1','P_DIR_L1','S_DIR_L1'],1)
 hold_provenance=validate_holdout(phases);journal_provenance=validate_journal(phases);check_pairs(phases['JOURNAL_HOLDOUT'],['P_DIR_L1','JOURNAL_PIPE_L1'],8);replication=replication_table(phases);abcd=[];summary=[]
 for target in ['V7_REPLICATION','OWNER_HOLDOUT']:
  a,s=stats.aggregate(dict(PILOT=phases['PILOT'],CLEAN_SCREEN=phases['CLEAN_SCREEN'],EVALUATION_CLEAN=phases['EVALUATION_CLEAN'],EVALUATION_FAULT=phases[target]),programs)
  for collection in [a,s]:
   for r in collection:
    if r['phase']=='PILOT' and target!='V7_REPLICATION':continue
    if r['phase']=='EVALUATION_FAULT':r['phase']=target
    r['cohort_scope']='known-case replication, descriptive' if r['phase']=='V7_REPLICATION' else 'independent event owners; inputs previously seen' if r['phase']=='OWNER_HOLDOUT' else 'known source pilot n1 descriptive'
    (abcd if collection is a else summary).append(r)
 ja,js=journal_aggregate(phases,programs);abcd.extend(ja);summary.extend(js)
 summary.extend(stats.clean_contrasts(dict(CLEAN_SCREEN=phases['CLEAN_SCREEN'],EVALUATION_CLEAN=phases['EVALUATION_CLEAN'])))
 throughput=[]
 for phase,rows in phases.items():
  if phase.startswith('CPU_GATE'):continue
  for r in rows:
   t=stats.throughput_row(phase,r)
   for k,v in r.get('seu',{}).items():
    if (k.startswith('pipeline_') and any(x in k for x in ['metadata','correct','recover','epoch_wrap','due'])) or any(x in k for x in ['source_head','journal_head','journal_correct','journal_DUE','journal_recover']):t[k]=v
   throughput.append(t)
 failure_rows=[dict(phase=r['phase'],program=r['program'],scenario=r['scenario'],owner=r['owner'],policy=r['id'],status=r['status'],exit_code=r.get('exit_code'),output=r['output'],cycles=r.get('cycles'),classification=r.get('failure_retention',{}).get('classification'),exception_type=r.get('failure_retention',{}).get('exception_type'),what=r.get('failure_retention',{}).get('what'),failure=r.get('failure')) for rows in phases.values() for r in rows if r['status']!='PASS']
 files={'EXECUTION_FAILURES.csv':stats.csv_text(failure_rows),'CPU_ABCD.csv':stats.csv_text(abcd),'PAIRED_SUMMARY.csv':stats.csv_text(summary),'THROUGHPUT.csv':stats.csv_text(throughput),'V7_REPLICATION.csv':stats.csv_text(replication),'FINAL_REPORT.ko.md':report(phases,summary,throughput,replication,safety)}
 RESULTS.mkdir(parents=True,exist_ok=True)
 for name,text in files.items():p=RESULTS/name;temp=p.with_suffix(p.suffix+'.tmp');temp.write_text(text);temp.replace(p)
 write(RESULTS/'ANALYSIS.lock.json',dict(status='MEASURED_V8_SOFTWARE_REPLICATION_AND_OWNER_HOLDOUT',phases=provenance,actual_main_cpu=sum(PHASE_COUNTS.values()),planned_main_cpu=sum(PHASE_COUNTS.values()),new_hard_cap=400,global_cpu_cap=3200,primary_L=1,II=1,bootstrap=dict(draws=stats.DRAWS,seed=stats.BOOTSTRAP_SEED,nominal_CI=.95,multiplicity_correction=False),holdout_provenance=hold_provenance,journal_provenance=journal_provenance,metadata_safety=ref(OUT/'reports/METADATA_SAFETY_GATE.json'),reused_statistics_helper=ref(ROOT/'scripts/pipeline_v6_analyze.py'),fully_qualified_physical_candidates=0,failed_rows=sum(r['status']!='PASS' for rows in phases.values() for r in rows),outputs={n:sha(RESULTS/n) for n in files}))
 print('PASS actual corrected V8 replication + owner holdout aggregation; no physical qualification')
if __name__=='__main__':main()
