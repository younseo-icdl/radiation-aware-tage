"""Frozen structure/resource definitions; extra fields are never inferred from outcomes."""
from v5_common import *
V={
 'FINITE0':dict(scheme='P0',policy='LEGACY',k=0,C=0,opts=['--resource-mode','SHARED2']),
 'PARITY64':dict(scheme='P_ED',policy='N1',k=64,C=1,opts=['--resource-mode','SHARED2']),
 'ECC64_RMW':dict(scheme='P_ECC',policy='N1',k=64,C=1,opts=['--resource-mode','SHARED2']),
 'TMR':dict(scheme='P_TMR',policy='LEGACY',k=0,C=1,opts=['--resource-mode','SHARED2']),
 'NATIVE_PORT1':dict(scheme='P0',policy='LEGACY',k=0,C=0,opts=['--lookup-ii','1']),
 'NATIVE':dict(scheme='P0',policy='LEGACY',k=0,C=0,opts=[]),
 'SHAM':dict(scheme='P0',policy='LEGACY',k=64,C=1,opts=['--resource-mode','SHARED2','--sham-wait','--schedule','']),
}
for ident,rep,taps,L,II,journal in [
 ('DIRECT_ISO','direct',8,0,0,False),('DIRECT_J0','direct',8,0,1,True),
 ('DIRECT_L1','direct',8,1,1,True),('DIRECT_L2','direct',8,2,1,True),('DIRECT_II2','direct',8,2,2,True),
 ('STRAT16','stratum',16,0,1,True),('GEOM16','geometric',16,0,1,True),('SHORT32','short32',8,0,0,False)]:
 V[ident]=dict(scheme='P0',policy='LEGACY',k=0,C=0,opts=['--representation',rep,'--tap-budget',str(taps),'--lookup-latency',str(L),'--lookup-ii',str(II)]+(['--journal-service'] if journal else []))

def make(item,ident,phase,scenario,owner,event='',extra=None,expected=None):
 v=V[ident];t=task(item,ident,phase,scenario,owner,event,scheme=v['scheme'],policy=v['policy'],k=v['k'],C=v['C'],extra=v['opts']+(extra or []))
 if expected:t['expected_instructions']=expected
 return t

def clean_rows():return json.loads((OUT/'reports/CLEAN.json').read_text())['tasks']
def clean_row(program,ident):return next(r for r in clean_rows() if r['program']==program and r['id']==ident)

if __name__=='__main__':
 assert json.loads((OUT/'reports/CPU_GATE_ACCEPTANCE.json').read_text())['status']=='PASS'
 inputs=json.loads((ROOT/'continuation_v3/runtime/configs/design_inputs.lock.json').read_text())['programs']
 write(OUT/'configs/variants.lock.json',dict(status='FROZEN_BEFORE_CLEAN_SCREEN',variants=V,diagnostic=['SHAM','DIRECT_ISO'],
     source_sha256=sha(ROOT/'src/rate_state_v5/representation.hpp'),comparison='FINITE0 protection reference; NATIVE representation reference; never mix denominator/resource contracts'))
 execute([make(item,ident,'CLEAN','zero','V5_CLEAN',extra=['--audit','--audit-limit','4000'] if ident in ['NATIVE','DIRECT_ISO'] else []) for item in inputs for ident in V], 'CLEAN',workers=8,pilot_first_batch=2)
