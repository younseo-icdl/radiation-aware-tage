"""Explicit units and paired, signed performance estimands for v5."""
import math
import numpy as np

def metrics(A,B,C,D):
    assert min(A,B,C,D)>0
    return dict(normal_overhead_pct=100*(C/A-1),residual_pct=100*(D/C-1),residual_pp=100*(D-C)/A,
                total_slowdown_pct=100*(D/A-1),reference_slowdown_pct=100*(B/A-1),
                net_cycles=B-D,net_gain_pp=100*(B-D)/A,
                additional_damage_reduction_pp=100*((B-A)-(D-C))/A,
                repair_only_gain_pp=100*((B-A)-(D-C))/A) # Legacy field: DID, not isolated repair causality.

def paired_interval(values,seed=3515480000,draws=10000):
    x=np.asarray(values,dtype=float)
    if not len(x):return (None,None,None)
    means=np.mean(np.random.default_rng(seed).choice(x,size=(draws,len(x)),replace=True),axis=1)
    return float(x.mean()),float(np.quantile(means,.025)),float(np.quantile(means,.975))

def poisson_window(mu):
    assert mu>=0 and math.isfinite(mu)
    p0=math.exp(-mu);p1=mu*p0
    # Stable small-mu tail; 1-p0-p1 loses all significant digits for rare rates.
    if mu<.1:
        term=mu*mu/2;tail=term;n=2
        while n<100:
            n+=1;term*=mu/n;tail+=term
            if abs(term)<abs(tail)*1e-16:break
        tail*=p0
    else:tail=max(0.,-math.expm1(-mu)-p1)
    return p0,p1,tail
