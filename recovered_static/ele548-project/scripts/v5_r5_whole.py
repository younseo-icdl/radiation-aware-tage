"""Coupled Poisson latent marks with architecture-specific site acceptance.

Missing sites are rejected latent marks, never no-op fault events. Per-second
per-bit hazard is the same ASSUMPTION across architectures, not target calibration.
"""
from v5_r5_common import *
from rng_namespace import rng,descriptor
import math
inputs=json.loads((ROOT/'continuation_v3/runtime/configs/design_inputs.lock.json').read_text())['programs']
ids=['NATIVE','PARITY64','ECC64_RMW','BATCH_DIRECT','BATCH_STRAT16']
base=[json.loads(s) for s in (ROOT/'reports/predictor_logical_state_manifest.jsonl').read_text().splitlines()]
maps={};pop=[]
for ident in ids:
 r=clean_row(inputs[0]['name'],ident);m=json.loads((ROOT/r['output']/'logical_manifest.json').read_text())
 entries={'base:'+str(s['site_id']):s['site_id'] for s in base if not (m['direct'] and s['field']=='folded')}
 for s in m['additional_sites']:
  key='extra:'+':'.join(str(s[k]) for k in ['structure','word','bit','replica']);assert key not in entries;entries[key]=s['id']
 assert len(entries)==m['total_bits'] and len(set(entries.values()))==len(entries),ident
 maps[ident]=entries;pop.append(dict(id=ident,bits=len(entries),manifest_sha256=sha(ROOT/r['output']/'logical_manifest.json'),source_manifest=r['output']+'/logical_manifest.json',
    exclusion='Whole enumerated logical population only. Existing BranchInfo/CPU ownership/RNG/BTB/RAS and combinational SET exclusions retained; no physical whole-CPU reliability claim.'))
universe=sorted(set().union(*(set(x) for x in maps.values())))
jobs=[];owners=[]
for wi,item in enumerate(inputs):
 H=max(clean_row(item['name'],ident)['cycles'] for ident in ids)
 for si,scale in enumerate([1e13,1e15]):
  flip_per_bit_s=1.05e-14*20/3600*scale # spectrum/FF-transfer assumptions declared below
  union_event_cycle=flip_per_bit_s*len(universe)/2e9
  for n in range(8):
   master=3195480000+wi*1000000+si*10000+n;tt=rng(master,'time');ll=rng(master,'location');cycle=0.;latent=[];accepted={x:[] for x in ids};rejected={x:0 for x in ids}
   while True:
    cycle+=float(tt.exponential(1/union_event_cycle))
    if cycle>4*H:break
    key=universe[int(ll.integers(len(universe)))];tick=max(1,int(round(cycle*500)));mark=len(latent);latent.append(dict(mark=mark,tick=tick,site_key=key))
    for ident in ids:
     if key in maps[ident]:accepted[ident].append(dict(mark=mark,tick=tick,site=maps[ident][key]))
     else:rejected[ident]+=1
   owner=f'WHOLE.{si}.{n}';owners.append(dict(program=item['name'],owner=owner,master=master,acceleration=scale,flip_per_bit_second=flip_per_bit_s,
       classification='ACCELERATED_HYPOTHETICAL_PER_BIT_SBU; NOT AN OPERATING RATE',latent=latent,accepted=accepted,absent_site_rejections=rejected,
       lambda_union_per_cycle=union_event_cycle,clock_Hz=2e9,time=descriptor(master,'time'),location=descriptor(master,'location')))
   for ident in ids:
    events=''.join(f"{e['tick']} {e['site']}\n" for e in accepted[ident]);jobs.append(make(item,ident,'WHOLE',f'scale{scale:g}',owner,events,expected=clean_row(item['name'],ident)['instructions']))
write(OUT/'configs/WHOLE_owners.lock.json',dict(status='FROZEN_BEFORE_DISPATCH',owners=owners,populations=pop,universe_sites=len(universe),
 class_transfer='SRAM/table and FF/history/control sensitivity ratio=1 ASSUMPTION for this direct simulation; 0.1/1/10 analytic sensitivity separate. R28 spectrum compatibility still provisional.',
 no_MCU_mapping='SBU only; no physical layout inferred; stationary equal bit hazards allow relative-age sampling of ring cells.',
 event_contract='Exponential continuous time then round to1ps tick; all variant-accepted events XOR exactly once; absent latent marks are not injected/count-as-zero faults.',
 horizon='4 times largest clean duration; future-after-program events and schedule-window censoring kept'))
execute(jobs,'WHOLE',workers=8,allowed_fault_failures=(
 'FAIL_PROTOCOL invalid bounded history pointer',
 'Pending response PC/type changed without cancellation',
 'gem5 has encountered a segmentation fault',
 'queue SECDED DUE',
 'illegal queue control encoding'))
note('WHOLE.POPULATION','IMPLEMENTED_CPU','Coupled whole-enumerated SBU exposure with deleted and added sites','Keep physical calibration and inherited ownership exclusions separate','Freeze new input/owner evaluation and analyze failure frequencies')
