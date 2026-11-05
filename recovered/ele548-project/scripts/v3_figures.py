"""Scientific figure from actual completed matched-owner confidence intervals."""
import json
from v3_common import *
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
d=json.loads((OUT/'reports/NEW_VS_N1.json').read_text())['P_minus_N1_net_pp']
rows=[(k,v) for k,v in d.items() if v['mean'] is not None]
fig,ax=plt.subplots(figsize=(7.5,3.4),layout='constrained')
for n,(name,s) in enumerate(rows):
 ax.errorbar(s['mean'],n,xerr=[[s['mean']-s['CI95'][0]],[s['CI95'][1]-s['mean']]],fmt='o',color='#2166ac',capsize=4)
ax.axvline(0,color='#777777',linestyle='--',linewidth=1)
ax.set_yticks(range(len(rows)),[k for k,v in rows]);ax.invert_yaxis()
ax.set_xlabel('Additional CPU net gain over N1 (percentage points)')
ax.set_title('Staged recovery vs N1: fixed inputs, matched-owner 95% CI')
ax.grid(axis='x',alpha=.2)
p=OUT/'figures';p.mkdir(exist_ok=True)
for suffix in ['png','svg']:fig.savefig(p/('P_vs_N1.'+suffix),dpi=180)
print('Actual confidence interval figure written')
