"""V10 component experiments share the prior time/disk ceiling; zero CPU trials."""
from pathlib import Path
import json,re,shutil,subprocess
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'cost_v10'
OLD=Path('/home/youns/workspace/ele548-project-v9')
def seconds(path):
    s=path.read_text(errors='replace')
    a=re.search(r'User time \(seconds\):\s*([0-9.]+)',s)
    b=re.search(r'System time \(seconds\):\s*([0-9.]+)',s)
    if a and b:return float(a[1])+float(b[1])
    if not s.strip():return 0.
    parts=s.strip().splitlines()[-1].split()
    try:return float(parts[0])+float(parts[1])
    except (ValueError,IndexError):raise RuntimeError(('UNPARSEABLE_TIME',str(path)))
def actual():
    # PREPARE_NATIVE's outer time includes native children; keep children raw but
    # count the outer process tree exactly once.
    native_outer=BASE/'next_lifetime_prepare/PREPARE_NATIVE.time'
    time_files=[p for p in BASE.rglob('*.time') if not (native_outer.exists() and p.name=='native.time' and 'next_lifetime_prepare/cases/' in str(p))]
    new_seconds=sum(seconds(p) for p in time_files)
    def size(path):return int(subprocess.check_output(['du','-sk',str(path)],text=True).split()[0])/2**20
    new_gib=size(ROOT);old_gib=size(OLD)
    return dict(new_recorded_coreh=new_seconds/3600,old_plus_new_recorded_coreh=5.286669444444445+new_seconds/3600,
       global_recorded_coreh=70.685125+new_seconds/3600,new_gib=new_gib,old_v9_plus_new_gib=old_gib+new_gib,
       combined_gib=20.54370880126953+old_gib+new_gib,free_gib=shutil.disk_usage(ROOT).free/2**30,
       old_cpu_markers=len(list((OLD/'rate_state_v9').glob('**/reports/run_starts/*.json'))))
def check():
    d=actual()
    assert d['old_cpu_markers']==352,'PREVIOUS_CPU_EVIDENCE_CHANGED'
    assert d['new_recorded_coreh']<2 and d['old_plus_new_recorded_coreh']<12 and d['global_recorded_coreh']<108,'TIME_CAP'
    assert d['new_gib']<.5 and d['old_v9_plus_new_gib']<8 and d['combined_gib']<34 and d['free_gib']>=10,'DISK_CAP'
    return d
if __name__=='__main__':print(json.dumps(check(),indent=2))
