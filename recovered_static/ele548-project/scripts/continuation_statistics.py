"""Matched owner inference; failures and oracle diagnostics are never performance rows."""
import math
import numpy as np

def abcd(A,B,C,D):
 if any(not math.isfinite(x) or x<=0 for x in [A,B,C,D]):raise ValueError('actual positive finite CPU cycles required')
 return dict(A=A,B=B,C=C,D=D,net_cycles=B-D,net_pp=100*(B-D)/A,clean_overhead_pct=100*(C-A)/A,residual_loss_pp=100*(D-C)/A,total_slowdown_pct=100*(D-A)/A,fault_unprotected_pct=100*(B-A)/A)

def fixed_program_bootstrap(groups,iterations=2000,seed=731026):
 if not groups or any(len(v)<2 for v in groups.values()):return dict(mean=None,CI95=None,status='INSUFFICIENT_INDEPENDENT_OWNERS')
 gen=np.random.Generator(np.random.PCG64(np.random.SeedSequence([0x42504349,2,seed])))
 arrays=[np.asarray(v,dtype=float) for _,v in sorted(groups.items())]
 if any(not np.all(np.isfinite(a)) for a in arrays):raise ValueError('missing/failed metrics cannot become0')
 means=[]
 for _ in range(iterations):means.append(float(np.mean([np.mean(a[gen.integers(len(a),size=len(a))]) for a in arrays])))
 return dict(mean=float(np.mean([np.mean(a) for a in arrays])),CI95=np.percentile(means,[2.5,97.5]).tolist(),status='PAIRED_OWNER_BOOTSTRAP_FIXED_PROGRAMS',programs=len(arrays),owners_per_program={k:len(v) for k,v in groups.items()},resampling='within each fixed input/program; equal program weights; not program population CI')

def audit_pair(B,D):
 for key in ['owner','program','scenario','input_sha256','schedule_sha256']:
  if B[key]!=D[key]:raise ValueError(f'matched pair differs: {key}')
 if any(r.get('oracle') or 'ORACLE' in r.get('owner','') for r in [B,D]):raise ValueError('oracle diagnostics cannot enter final performance')
 return B['status']=='PASS' and D['status']=='PASS'

def zero_failure_upper(n):
 return 1-.05**(1/n) if n>0 else None
