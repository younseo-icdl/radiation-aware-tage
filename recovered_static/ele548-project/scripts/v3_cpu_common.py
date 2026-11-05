"""Concrete O3 execution with native answer checks; no placeholder results."""
import os,csv,json
from v3_common import *
from run_o3_public_baseline import stats
BINARY=ROOT/'third_party/gem5-costaware-v3/build/X86_STAGE0/gem5.opt'
CONFIG=ROOT/'gem5/o3_costaware_v3.py'
def select_final_endpoint():
 global BINARY,CONFIG
 lock=json.loads((OUT/'configs/FINAL_PRODUCER.lock.json').read_text());assert lock['status']=='CPU_GATE_PASS_BEFORE_EVALUATION'
 BINARY=ROOT/lock['binary'];CONFIG=ROOT/lock['config']
 assert sha(BINARY)==lock['binary_sha256'] and sha(CONFIG)==lock['config_sha256']
 return lock
def validate_cpu(t,r,d):
 item=t['input'];schedule=d/'schedule.ticks'
 assert sha(ROOT/item['binary'])==item['binary_sha256'] and sha(ROOT/item['input'])==item['input_sha256']
 assert schedule.read_text()==t.get('events_text',''),'RECOVERED_SCHEDULE_MISMATCH'
 r.update({k:v for k,v in t.items() if k not in ['input','events_text']});r.update(output=str(d.relative_to(ROOT)),input_sha256=item['input_sha256'],program_binary_sha256=item['binary_sha256'],schedule_sha256=sha(schedule),producer_binary_sha256=sha(BINARY),config_sha256=sha(CONFIG),status='FAIL_EXECUTION')
 if r['exit_code']:return r
 try:
  assert sha(d/'program.stdout')==item['native_stdout_sha256'],'CHECKSUM_WRONG'
  assert not (d/'program.stderr').read_bytes(),'PROGRAM_STDERR'
  log=(d/'gem5.log').read_text();assert 'Exit cause: exiting with last active thread context code: 0' in log,'UNEXPECTED_EXIT'
  assert not any(s in log.lower() for s in ['ignoring syscall','unimplemented syscall']),'UNSUPPORTED_SYSCALL'
  st=stats(d/'stats.txt');s=json.loads((d/'seu.json').read_text());m=json.loads((d/'logical_manifest.json').read_text())
  cycles=int(st['system.cpu.numCycles']);ni=int(st['system.cpu.commitStats0.numInsts']);assert ni==int(st['simInsts']) and cycles>0
  if t.get('expected_instructions'):assert ni==t['expected_instructions'],'INSTRUCTION_MISMATCH'
  expected=[line for line in t.get('events_text','').splitlines() if int(line.split()[0])<=s['end_tick']];ee=list(csv.DictReader((d/'events.csv').open()));assert len(expected)==len(ee)==s['applied_events']
  for line,e in zip(expected,ee):
   tick,ids=line.split();assert e['tick']==tick and e['site_ids']==ids and e['XOR_verified']=='1'
  for key in ['hot','shadow']:
   if key+'_accepted' in s:assert s[key+'_accepted']==s[key+'_completed']+s[key+'_cancelled']+s[key+'_pending'],'QUEUE_CONSERVATION'
  r.update(status='PASS',cycles=cycles,instructions=ni,IPC=ni/cycles,seu=s,total_bits=m['total_bits'],hashes={p.name:sha(p) for p in d.iterdir() if p.is_file() and p.name not in ['gem5.log.time']},oracle=t.get('cost_remove','NONE')!='NONE',failure=None)
 except Exception as e:r.update(status='FAIL_VALIDATION',failure=str(e))
 return r

def recover_cpu(t):
 """Recover finished, immutable actual evidence after runner interruption only."""
 import configparser
 d=OUT/'reports'/t['phase']/t['label'];cp=configparser.ConfigParser();cp.read(d/'config.ini')
 section='system.cpu.branchPred.conditionalBranchPred.tage';c=cp[section]
 for k,v in [('scheme',t['scheme']),('role_policy',t['policy']),('inspection_interval',str(t['k'])),('check_cycles',str(t['C'])),('maintenance_cycles',str(t['U']))]:assert c[k]==v,('RECOVERED_CONFIG_MISMATCH',k)
 assert c['resource_mode']=='SHARED2' and c['rmw_latency']=='1' and c['rmw_ii']=='1'
 assert c['decouple_shadow']==str(bool(t.get('split'))).lower()
 vals=(d/'gem5.log.time').read_text().splitlines();assert len(vals)==1,'ACTUAL_PROCESS_FAILURE_REQUIRES_RETAINED_FAILURE'
 u,s,rss=vals[0].split();log=(d/'gem5.log').read_text()
 command_line=next(x for x in log.splitlines() if x.startswith('command line: '));assert str(BINARY) in command_line and str(CONFIG) in command_line
 r=dict(exit_code=0,host_cpu_seconds=float(u)+float(s),max_rss_kib=int(rss),wall_seconds=None,wall_time_unavailable_after_runner_interrupt=True,log=str((d/'gem5.log').relative_to(ROOT)),recovered_finished_artifact=True,command_line=command_line)
 return validate_cpu(t,r,d)

def run_cpu(t):
 d=OUT/'reports'/t['phase']/t['label'];d.mkdir(parents=True,exist_ok=True);item=t['input']
 assert sha(ROOT/item['binary'])==item['binary_sha256'] and sha(ROOT/item['input'])==item['input_sha256']
 schedule=d/'schedule.ticks';assert not schedule.exists();schedule.write_text(t.get('events_text',''))
 cmd=[BINARY,'--outdir='+str(d),CONFIG,'--binary',ROOT/item['binary'],'--input',ROOT/item['input'],'--scheme',t['scheme'],'--role-policy',t['policy'],'--inspection-interval',str(t['k']),'--check-cycles',str(t['C']),'--maintenance-cycles',str(t['U']),'--repair-cycles','0' if t['scheme']=='P0' else '4','--cost-remove',t.get('cost_remove','NONE'),'--schedule',schedule,'--max-ticks',str(t.get('max_ticks',250000000000))]
 if t.get('full_delta'):cmd+=['--full-delta']
 if t.get('reset_recovery'):cmd+=['--reset-recovery']
 cmd+=t.get('additional_args',[])
 env=os.environ.copy();env['LD_LIBRARY_PATH']='/opt/miniconda3/lib'+(':'+env['LD_LIBRARY_PATH'] if env.get('LD_LIBRARY_PATH') else '')
 r=timed(cmd,d/'gem5.log',env=env);r.update({k:v for k,v in t.items() if k not in ['input','events_text']});r.update(output=str(d.relative_to(ROOT)),input_sha256=item['input_sha256'],program_binary_sha256=item['binary_sha256'],schedule_sha256=sha(schedule),producer_binary_sha256=sha(BINARY),config_sha256=sha(CONFIG),status='FAIL_EXECUTION')
 return validate_cpu(t,r,d)
