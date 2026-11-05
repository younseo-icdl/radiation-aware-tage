#!/usr/bin/env python3
import json,subprocess,sys,hashlib,platform,sysconfig,shutil,os
from pathlib import Path
root=Path(sys.argv[1]).resolve();out={'schema_version':1,'source_commits':{},'warning':'Source checkout lock, not experiment validation.'}
for repo in ['gem5','verilator']:
 d=root/'third_party'/repo
 if (d/'.git').exists():
  out['source_commits'][repo]=subprocess.check_output(['git','-C',str(d),'rev-parse','HEAD'],text=True).strip()
  out.setdefault('sources',{})[repo]={'remote':subprocess.check_output(['git','-C',str(d),'remote','get-url','origin'],text=True).strip(),'tag':subprocess.check_output(['git','-C',str(d),'describe','--tags','--exact-match','HEAD'],text=True).strip()}
out['python']={'version':sys.version,'executable':sys.executable,'libdir':sysconfig.get_config_var('LIBDIR')}
out['compiler']={}
for name,path in [('default_gcc','/usr/bin/g++'),('selected_gcc','/opt/rh/gcc-toolset-11/root/usr/bin/g++')]:
 if Path(path).exists():out['compiler'][name]={'path':path,'version':subprocess.check_output([path,'--version'],text=True).splitlines()[0]}
out['host']=platform.platform()
lock=root/'reports/requirements.lock.txt'
if lock.exists():out['python_requirements']={'path':'reports/requirements.lock.txt','sha256':hashlib.sha256(lock.read_bytes()).hexdigest(),'packages':lock.read_text().splitlines()}
out['tools']={name:shutil.which(name) for name in ['make','git','pkg-config','m4','valgrind','genus','innovus','xrun']}
out['license_checkout']='NOT_TESTED; tool discovery is not checkout'
out['TCAD']='UNAVAILABLE_EXCLUDED_BY_USER'
conf=root/'third_party/gem5/build/X86_STAGE0/gem5.build/config'
if conf.exists():
 binary=root/'third_party/gem5/build/X86_STAGE0/gem5.debug'
 out['gem5_build']={'variant':'debug','path':str(binary.relative_to(root)),'jobs':2,'RUBY':False,'USE_SYSTEMC':False,'USE_KVM':True,'KVM_execution':False,'actual_cpu':'X86O3CPU','configuration_sha256':hashlib.sha256(conf.read_bytes()).hexdigest(),'status':'BUILT' if binary.exists() else 'NOT_BUILT'}
 if binary.exists():out['gem5_build']['binary_sha256']=hashlib.sha256(binary.read_bytes()).hexdigest()
 validated=root/'reports/gem5_o3_validation.json'
 if validated.exists():out['gem5_build']['checksum_validation']=json.loads(validated.read_text())['status']
out['research_executables']={}
for name in ['predictor_e0','pilot','checksum_freestanding','repeated','event_stream_test','e1_correctness','e1_warmup','e1_campaign','protection_e2','e2_manifest','e2_campaign']:
 p=root/'build'/name
 if p.exists():out['research_executables'][name]={'path':str(p.relative_to(root)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
for p in sorted((root/'build/public_workloads').glob('*')):
 if p.is_file():out['research_executables']['MiBench_'+p.name]={'path':str(p.relative_to(root)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
public_lock=root/'sources/public_workload_sources.lock.json';prefix=root/'.local/musl-1.2.6'
if public_lock.exists() and (prefix/'lib/libc.a').exists():
 out['user_local_musl']={'version':'1.2.6','prefix':str(prefix),'source_lock':str(public_lock.relative_to(root)),'source_lock_sha256':hashlib.sha256(public_lock.read_bytes()).hexdigest(),'build_log':'reports/e3_setup/musl_build.log','wrapper_sha256':hashlib.sha256((prefix/'bin/musl-gcc').read_bytes()).hexdigest(),'libc_static_sha256':hashlib.sha256((prefix/'lib/libc.a').read_bytes()).hexdigest(),'scope':'private prefix; no package manager/sudo/global environment changes'}
opt=root/'third_party/gem5/build/X86_STAGE0/gem5.opt'
if (root/'reports/e3_setup/gem5_opt_build.log').exists():
 out['gem5_opt_build']={'status':'BUILDING_FOR_ACTUAL_PROGRAM_E3','source_commit':out['source_commits']['gem5'],'path':str(opt.relative_to(root)),'jobs':8,'log':'reports/e3_setup/gem5_opt_build.log','binary_sha256':None}
 if opt.exists() and opt.stat().st_mode & 0o111:
  probe_env=os.environ.copy();probe_env['LD_LIBRARY_PATH']=(sysconfig.get_config_var('LIBDIR') or '/opt/miniconda3/lib')+(':'+probe_env['LD_LIBRARY_PATH'] if probe_env.get('LD_LIBRARY_PATH') else '')
  probe=subprocess.run([str(opt),'--build-info'],env=probe_env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=15)
  if probe.returncode==0:
   out['gem5_opt_build'].update(status='BUILT_BUILD_INFO_PASS_CPU_GATE_SEPARATE',binary_sha256=hashlib.sha256(opt.read_bytes()).hexdigest())
(root/'reports/software.lock.json').write_text(json.dumps(out,indent=2)+'\n')
