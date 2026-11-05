"""Same frozen v15 ledger with the one actual user-authorized disk change."""
from pathlib import Path
import hashlib,json,sys
sys.dont_write_bytecode=True
B=Path(__file__).resolve().parents[1]
V15=Path('/home/youns/workspace/ele548-project-v15/query_controls_v15')
sys.path.insert(0,str(V15/'tools'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
auth=B/'reports/DISK_AUTHORIZATION_328.lock.json'
a=json.loads(auth.read_text());assert a['authorized_by']=='user' and a['status']=='USER_AUTHORIZED_RECENT_DISK328_ONLY' and a['recent_disk_MiB_cap']==328
assert (a['CPU_cap'],a['CPU_phase_coreh_cap'],a['recent_coreh_cap'],a['v9_onward_coreh_cap'],a['global_coreh_cap'],a['all7_roots_GiB_cap'])==(3531,4,8,19,108,8)
p=V15/'tools/resources_cpu.py';proposal=json.loads((V15/'reports/CPU18_PROPOSAL.lock.json').read_text());assert sha(p)==proposal['resource_guard']['sha256']
source=p.read_text();old="assert old['recent_MiB']+size+additional_MiB+active<320 and";new=old.replace('<320','<328');assert source.count(old)==1
derived=source.replace(old,new)
scope={'__name__':'v17_guard_with_user_disk_amendment','__file__':str(p)}
exec(compile(derived,str(p)+' [one authorized disk bound changed]','exec'),scope)
def snapshot(additional_seconds=0,additional_MiB=0):
 result=scope['snapshot'](additional_seconds,additional_MiB)
 result['caps']=dict(result['caps'],recent_disk_MiB=328)
 result['disk_amendment']={'path':str(auth),'sha256':sha(auth)}
 return result
def transformation():return {'original_guard':{'path':str(p),'sha256':sha(p)},'derived_source_sha256':hashlib.sha256(derived.encode()).hexdigest(),'only_replacement':{'from':old,'to':new},'authority':{'path':str(auth),'sha256':sha(auth)}}
