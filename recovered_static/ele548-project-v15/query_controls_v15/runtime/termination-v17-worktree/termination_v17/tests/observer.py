from pathlib import Path
import copy,json,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'config'))
from terminal_observer import observe,valid,quiescent
V15=Path('/home/youns/workspace/ele548-project-v15/query_controls_v15')
tested=0
for mode in ('REC','DIRECT'):
 label='dijkstra_small.R1.EARLY_'+mode+'_Q1U1'
 s=json.loads((V15/'runtime/cpu_trials'/label/'seu.json').read_text())
 valid(s);assert not quiescent(s);tested+=1
 # An explicit synthetic future is a unit-test fixture, NOT a claim about
 # the real O3 post-exit event queue. The CPU regressions must prove that.
 complete=copy.deepcopy(s);complete['tick']+=500;complete['source_cycles']+=1
 n=complete['early_pending'];complete['early_delivered']+=n;complete['early_pending']=0
 complete['lookup_consumed']+=n;complete['lookup_pending']-=n
 complete['source_completed']+=complete['source_pending'];complete['source_pending']=0
 complete['ingress_issued']=complete['ingress_enqueued'];valid(complete)
 assert len(observe(s,lambda:None,lambda:complete))==2;tested+=1
 assert len(observe(complete,lambda:(_ for _ in ()).throw(AssertionError('unexpected advance')),lambda:None))==1;tested+=1
 bad=copy.deepcopy(s);bad['conserved']=False
 try:observe(bad,lambda:None,lambda:complete)
 except AssertionError:tested+=1
 else:raise AssertionError('integrity failure became censored')
 bad=copy.deepcopy(s);bad['lookups']+=1
 try:valid(bad)
 except AssertionError:tested+=1
 else:raise AssertionError('orphan prediction accepted')
 slow=copy.deepcopy(s)
 def step():slow['tick']+=500;slow['source_cycles']+=1
 try:observe(s,step,lambda:copy.deepcopy(slow),2)
 except AssertionError as e:assert 'UNRESOLVED_TERMINAL' in str(e);tested+=1
 else:raise AssertionError('unresolved request masked')
 try:observe(s,lambda:None,lambda:s,2)
 except AssertionError as e:assert 'BAD_ACTUAL_CLOCK' in str(e);tested+=1
 else:raise AssertionError('non-progressing clock accepted')
print(json.dumps({'status':'PASS_OBSERVER_UNIT_ONLY_NOT_O3_TERMINATION','checks':tested,'real_failed_snapshots':2,'synthetic_completion_fixtures':2,'CPU_trials':0}))
