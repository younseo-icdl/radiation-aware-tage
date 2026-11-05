import argparse,sys,pathlib
sys.dont_write_bytecode=True
import common as m,initialize as i
r=m.r;B=m.BASE
p=argparse.ArgumentParser();p.add_argument('--build',required=True);a=p.parse_args();build=r.load(B/'reports'/('CPU_BUILD_'+a.build+'.json'));binary=pathlib.Path(build['binary']['path']);config=pathlib.Path(build['runtime_config'])/'o3_protection_v18.py';old=r.load(m.V15/'reports/CPU18_PROPOSAL.lock.json');program=old['tasks'][0]['program_binary']['path'];rows=[]
for method in i.METHODS:
 out=B/'runtime'/('initialization_'+a.build)/method;out.mkdir(parents=True,exist_ok=False)
 run=m.invoke('initialize_'+a.build+'_'+method,['/usr/bin/env','LD_LIBRARY_PATH=/opt/miniconda3/lib',binary,'--outdir='+str(out),config,*i.args(method,program),'--initialize-only'],120)
 manifest=r.load(out/'logical_manifest.json');summary=r.load(out/'seu.json');assert summary['tick']==0 and not summary['applied_events'];rows.append({'method':method,'execution':run,'manifest':r.ref(out/'logical_manifest.json'),'summary':r.ref(out/'seu.json'),'logical_bits':manifest['total_logical_bits']})
r.put(B/'reports'/('INITIALIZATION_'+a.build+'.json'),{'status':'PASS_ALL6_TICK0_ONLY_NOT_CPU','rows':rows,'binary':r.ref(binary),'config':r.ref(config),'resources':r.snapshot()})
