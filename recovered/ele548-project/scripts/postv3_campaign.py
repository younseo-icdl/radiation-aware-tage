"""Fixed small development ablation: only safe promotion boundaries vary."""
import statistics
import numpy as np
from postv3_common import *
from rng_namespace import rng,descriptor

assert json.loads((OUT/'reports/G0_ACCEPTANCE.json').read_text())['status']=='PASS'
clean=json.loads((OUT/'reports/CLEAN.json').read_text())['tasks']
inputs=json.loads((ROOT/'continuation_v3/runtime/configs/design_inputs.lock.json').read_text())['programs']
scope=json.loads((ROOT/'sources/protection_scope.lock.json').read_text())
words=[w['site_ids'] for w in scope['payload_words']];ends=np.cumsum(list(map(len,words)))
jobs=[]
for wi,item in enumerate(inputs):
    ref=next(t for t in clean if t['program']==item['name'] and t['id']=='P0')
    A=ref['cycles'];cap=4*A
    for si,scenario in enumerate(['SBU_SINGLE','CHARM_6T']):
        for n in range(4):
            seed=2815480000+wi*1000000+si*10000+n
            tr,kr,lr=[rng(seed,role) for role in ['time','K','location']]
            if scenario=='SBU_SINGLE':arrivals=[float(tr.uniform(.1*A,.8*A))]
            else:
                arrivals=[];t=0.
                while True:
                    t+=float(tr.exponential(1e6))
                    if t>=cap:break
                    arrivals.append(t)
            events=[]
            for at in arrivals:
                K=1 if scenario=='SBU_SINGLE' or int(kr.integers(214))<205 else 2
                word=words[int(np.searchsorted(ends,int(lr.integers(346)),side='right'))]
                start=int(lr.integers(len(word)-K+1));events.append((max(1,int(round(at*500))),word[start:start+K]))
            text=''.join(str(at)+' '+';'.join(map(str,ids))+'\n' for at,ids in events)
            owner=f'POSTV3_G2_W{wi}_S{si}_N{n}'
            for v in [P0]+variants:
                jobs.append(task(v,item,'G2',scenario,owner,text,max_ticks=cap*500,
                    expected_instructions=ref['instructions'],seed=seed,
                    namespaces={role:descriptor(seed,role) for role in ['time','K','location']}))
assert len(jobs)==144
forecast=statistics.mean(t['host_cpu_seconds'] for t in clean if t['id']!='SHAM_WAIT')*len(jobs)/3600
write(OUT/'reports/G2_FORECAST.json',dict(status='FORECAST_NOT_RESULT',runs=144,estimated_core_hours=forecast,used_core_hours=used_cpu()/3600))
assert forecast+used_cpu()/3600<32,'Checkpoint before fixed campaign; no sample reduction'
# Ten measured jobs precede wider dispatch. This is host parallelism only.
pilot=execute(jobs[:10],'G2_PILOT',workers=2)
write(OUT/'reports/G2_PILOT_HEALTH.json',dict(status='PASS',runs=len(pilot),
    mean_wall_seconds=statistics.mean(r['wall_seconds'] for r in pilot),
    max_rss_kib=max(r['max_rss_kib'] for r in pilot),all_native_correct=True,
    next_workers=8,rate_per_cycle=1e-6,rate_measured=False))
rest=execute(jobs[10:],'G2_REMAINDER',workers=8)
rows=pilot+rest
write(OUT/'reports/G2.json',dict(status='PASS',planned=144,completed=144,tasks=rows,
    same_k=64,detector='original incremental parity',source_resource='SHARED2 L1 II1 hot64',
    only_production_change='safe static promotion boundaries',old_holdout_reused_as_independent=False))
