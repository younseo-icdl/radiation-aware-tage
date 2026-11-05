"""Standalone research figure from the completed, frozen confirmation CSV."""
import csv, json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from native_v9_common import ROOT, sha, write, ref

def main():
    base=ROOT/'rate_state_v9/results';source=base/'source_complete_v2/SOURCE_SUMMARY.csv'
    lock=json.loads((base/'source_complete_v2/ANALYSIS.lock.json').read_text())
    assert sha(source)==lock['artifacts_sha256']['SOURCE_SUMMARY.csv']
    assert lock['source_cpu']==30
    rows=list(csv.DictReader(source.open()))
    rows=[r for r in rows if r['level']=='PROGRAM_SCENARIO']
    programs=['qsort_small','dijkstra_small','sha1']
    scenarios=[('SOURCE_RAW130_CHARM_2000S','Raw-history CHARM-law stress; actual applied K2 = 0')]
    policies=[('U','Unprotected','#666666'),('C_PAR_FREQUENT','Parity/relearn','#d27800'),('C_ECC','SECDED','#2c7f48'),('C_TMR','TMR','#844bb5'),('A_DIR','Exact direct','#206eb2')]
    fig,axis=plt.subplots(1,1,figsize=(9,4.4),layout='constrained');axes=[axis]
    for ax,(scenario,title) in zip(axes,scenarios):
        ax.axhline(0,color='#888888',linewidth=.8)
        for pi,(policy,label,color) in enumerate(policies):
            for wi,program in enumerate(programs):
                cell=[r for r in rows if r['scenario']==scenario and r['program']==program and r['policy']==policy]
                if not cell:continue  # Unmeasured policies are never zero-filled.
                assert len(cell)==1
                r=cell[0]
                if not r.get('CI_low_pp') or not r.get('common_owner_mean_net_gain_pp'):continue
                mean=float(r['common_owner_mean_net_gain_pp']);low=float(r['CI_low_pp']);high=float(r['CI_high_pp'])
                assert low-1e-10<=mean<=high+1e-10
                ax.errorbar(wi+(pi-2)*.115,mean,yerr=[[max(0,mean-low)],[max(0,high-mean)]],fmt='o',markersize=4,color=color,capsize=3,label=label if wi==0 else None)
        ax.set_xticks(range(3),['qsort','dijkstra','SHA1']);ax.set_title(title,fontsize=10)
        ax.set_ylabel('Net gain 100(B-D)/A [percentage points]');ax.grid(axis='y',alpha=.2)
    handles,labels=axes[0].get_legend_handles_labels();fig.legend(handles,labels,loc='outside lower center',ncol=5,frameon=False)
    fig.suptitle('R1 conditional raw scope: two paired owners per cell (exploratory intervals)',fontsize=12)
    dest=base/'figures_corrected';dest.mkdir(exist_ok=True)
    for ext in ['png','pdf']:
        f=dest/('NATIVE_L0_NET_GAIN.'+ext);assert not f.exists();fig.savefig(f,dpi=180)
    plt.close(fig)
    write(dest/'FIGURE.lock.json',dict(status='PLOTTED_FROZEN_MEASUREMENTS_EXPLORATORY_NOT_SUPERIORITY',source=ref(source),script=ref(Path(__file__)),artifacts={p.name:sha(p) for p in dest.glob('NATIVE_L0_NET_GAIN.*')},assumptions='C0 inline stage-fit, protectedrepair4cycles; conditional RAW130 only, R1 WHOLE metadata failure preserved separately; actual applied K2=0; no full-scheme PPA claim',errorbar='Nominal exact N2 paired bootstrap95%; no causal CPI decomposition'))
    print('PASS standalone PNG/PDF figure; no simulator executed')

if __name__=='__main__':main()
