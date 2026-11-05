"""Standalone scientific figure of actually completed independent CPU results."""
from v5_common import ROOT
import csv,json,numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
F=ROOT/'rate_state_v5/results';rs=list(csv.DictReader((F/'CPU_PAIRED_SUMMARY.csv').open()))
rows=[r for r in rs if r['cohort']=='EVALUATION_V3_FAULT'];assert rows
names=['qsort_small','dijkstra_small','sha1','bitcount_det','basicmath_sseio']
labels=['qsort','dijkstra','SHA-1','bitcount','basicmath\n(binary64, integer I/O)']
policies=['PARITY64','BATCH_DIRECT','BATCH_STRAT16'];colors=['#ae7d2c','#147a88','#795ba5'];aliases=['Periodic parity k64','Exact direct fold','Stratum16 direct']
fig,axes=plt.subplots(1,3,figsize=(14.5,4.6))
for panel,scenario in enumerate([None,'CHARM_RHO1_RAW130','WHOLE_SBU_SCALE1E15']):
 ax=axes[panel]
 for pi,policy in enumerate(policies):
  selected=[next(r for r in rows if r['program']==n and r['policy']==policy and r['scenario']==(scenario or 'CHARM_RHO1_RAW130')) for n in names]
  values=[float(r['normal_overhead_pct'] if scenario is None else r['mean_gain_pp']) for r in selected]
  x=np.arange(5)+(pi-1)*.24
  if scenario is None:ax.bar(x,values,.23,color=colors[pi],label=aliases[pi])
  else:
   lo=[v-float(r['gain_CI_low']) for r,v in zip(selected,values)];hi=[float(r['gain_CI_high'])-v for r,v in zip(selected,values)]
   ax.errorbar(x,values,yerr=[lo,hi],fmt='o',capsize=3,color=colors[pi],label=aliases[pi],markersize=4)
   for xx,v,r in zip(x,values,selected):
    if int(r['n_valid_pairs'])!=20:ax.annotate(r['n_valid_pairs']+'/20',(xx,v),xytext=(1,6),textcoords='offset points',fontsize=7,color=colors[pi])
 ax.set_xticks(np.arange(5),labels,rotation=27,ha='right',fontsize=8)
 ax.axhline(0,color='#333333',linewidth=.7);ax.grid(axis='y',alpha=.2)
 if scenario is None:
  ax.axhline(2,color='#b94040',linestyle='--',linewidth=.8,label='2% engineering budget');ax.set_title('Clean overhead vs native TAGE');ax.set_ylabel('% (lower is better)')
 else:
  ax.set_title('Raw-targeted CHARM, rho=1' if panel==1 else 'Enumerated-population SBU stress');ax.set_ylabel('Paired net gain (B-D)/A, pp')
handles,text=axes[0].get_legend_handles_labels();fig.legend(handles,text,loc='upper center',ncol=4,frameon=False,fontsize=9)
fig.text(.5,.015,'20 independent owners/program/condition; nominal 95% paired bootstrap. Failed pairs omitted from cycle estimates and explicitly labeled.\nStress rates are assumptions; storage exclusions and adverse metadata failures prevent hardware qualification.',ha='center',fontsize=8)
fig.subplots_adjust(top=.83,bottom=.26,wspace=.32);fig.savefig(F/'INDEPENDENT_CPU_RESULTS.png',dpi=180);plt.close(fig)
print('Saved actual independent CPU figure')
