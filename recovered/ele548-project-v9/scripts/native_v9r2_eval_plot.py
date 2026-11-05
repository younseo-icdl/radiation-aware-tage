"""Standalone scientific figure from the sealed actual R2 paired analysis."""
import csv
import hashlib
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

ROOT=Path(__file__).resolve().parents[1]
RESULTS=ROOT/'rate_state_v9/r2_evaluation/results'
source=RESULTS/'PAIRED_SUMMARY.csv'
lock=json.loads((RESULTS/'ANALYSIS.lock.json').read_text())
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert digest(source)==lock['artifacts_sha256'][source.name]
rows=list(csv.DictReader(source.open()))
rows={(r['program'],r['scenario'],r['policy']):r for r in rows if r['level']=='PROGRAM_SCENARIO'}
programs=['qsort_small','dijkstra_small','sha1']
scenarios=['SOURCE_RAW130_CHARM_2000S','WHOLE_K1_REF_SCALE1000000000000000','WHOLE_K1_REF_SCALE10000000000000000','RAW130_K2_SINGLE']
titles=['Raw130: CHARM marks, 2000 events/s','WHOLE: reference x $10^{15}$','WHOLE: reference x $10^{16}$','Raw130: conditional one K2 event']
policies=['C_PAR_FREQUENT','C_PAR_PERIODIC','C_ECC','C_TMR','A_DIR']
labels=['Parity','N1 (64)','ECC','TMR','Direct']
colors=['#0072B2','#56B4E9','#009E73','#E69F00','#333333']
folder=RESULTS/'figures';assert not folder.exists(),'IMMUTABLE_FIGURE_DIR'
fig,axes=plt.subplots(3,4,figsize=(15,8.5),layout='constrained')
for pi,program in enumerate(programs):
    for si,scenario in enumerate(scenarios):
        ax=axes[pi,si];ax.axhline(0,color='0.65',lw=.7,zorder=0)
        for x,(policy,color) in enumerate(zip(policies,colors)):
            row=rows[program,scenario,policy]
            if row['n_valid_pairs']!='2' or not row.get('common_owner_mean_net_gain_pp'):
                ax.text(x,.5,'invalid',rotation=90,ha='center',va='center',transform=ax.get_xaxis_transform(),color='#D55E00');continue
            value=float(row['common_owner_mean_net_gain_pp']);low=float(row['CI_low_pp']);high=float(row['CI_high_pp'])
            assert low-1e-10<=value<=high+1e-10
            ax.errorbar(x,value,yerr=[[max(0,value-low)],[max(0,high-value)]],fmt='o',color=color,capsize=3,lw=1.2,ms=4)
        ax.set_xticks(range(5),labels,rotation=35,ha='right',fontsize=8)
        ax.yaxis.set_major_locator(MaxNLocator(4));ax.tick_params(axis='y',labelsize=8)
        ax.spines[['top','right']].set_visible(False)
        if pi==0:ax.set_title(titles[si],fontsize=10)
        if si==0:ax.set_ylabel(program+'\nNet gain [%p]',fontsize=10)
fig.suptitle('Paired CPU net gain: $100(B-D)/A$ | Native L0; normal stage-fit assumed',fontsize=14)
fig.supxlabel('Two owners per cell; exact discrete bootstrap intervals are descriptive. Panel y-scales differ. WHOLE multipliers are stress conditions.',fontsize=9)
folder.mkdir()
files=[]
for suffix in ['png','pdf']:
    path=folder/('R2_PAIRED_NET_GAIN.'+suffix);fig.savefig(path,dpi=180);files.append(path)
plt.close(fig)
(folder/'FIGURE.lock.json').write_text(json.dumps(dict(status='ACTUAL_R2_ANALYSIS_DERIVED_FIGURE',source={'path':str(source.relative_to(ROOT)),'sha256':digest(source)},analysis={'path':str((RESULTS/'ANALYSIS.lock.json').relative_to(ROOT)),'sha256':digest(RESULTS/'ANALYSIS.lock.json')},script={'path':str(Path(__file__).relative_to(ROOT)),'sha256':digest(Path(__file__))},files={p.name:digest(p) for p in files},limitations='n2 descriptive CIs; panel-specific scales; no physical full-stage or PPA inference'),indent=2)+'\n')
print('PASS_FIGURE',*[str(p) for p in files])
