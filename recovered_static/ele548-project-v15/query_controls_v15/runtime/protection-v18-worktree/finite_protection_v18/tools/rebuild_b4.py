from pathlib import Path
import concurrent.futures,json,sys
sys.dont_write_bytecode=True
import common as m
r=m.r;B=m.BASE;S=B/'producer_source/B4'
def freeze(label):
 files=[];dest=B/'runtime/frozen';dest.mkdir(exist_ok=True)
 for p in sorted(S.rglob('*')):
  if p.is_file():
   z=r.ref(p);q=dest/(z['sha256']+p.suffix)
   if not q.exists():q.write_bytes(p.read_bytes())
   z['verified_bytes']=str(q);files.append(z)
 lock=B/'reports'/(label+'.source.lock.json');r.put(lock,{'files':files});return r.ref(lock)
def gate(name,original=False):
 label=name+('_REPRO_B1' if original else '_B4');src=B/'producer_source/B1/src' if original else S/'src';binary=B/'runtime'/label
 cc=[m.CC,'-std=c++17','-O2','-g0','-static-libstdc++','-static-libgcc','-I'+str(src),'-I'+str(m.V9/'src'),'-I'+str(m.V9/'src/standalone'),'-I'+str(m.V9/'third_party/gem5-native-v9r2/src'),S/'tests'/(name+'.cpp'),m.V15/'runtime/tage_base.cc','-o',binary]
 build=m.invoke(label+'_build',cc)
 if original:
  try:m.invoke(label+'_run',[binary]);raise RuntimeError('ORIGINAL_FAILURE_NOT_REPRODUCED')
  except AssertionError:print('EXPECTED_ORIGINAL_MIXED_TRANSACTION_FAILURE_RETAINED',flush=True);return
 run=m.invoke(label+'_run',[binary]);result=json.loads(Path(run['stdout']['path']).read_text());r.put(B/'reports'/(label+'.json'),{'result':result,'build':build,'run':run,'binary':r.ref(binary)});print(name,result['status'],flush=True)
def main():
 freeze('B4_BEFORE_GATES')
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(gate,['scope_gate','vector_gate','source_guard_gate','source_transport_gate','transaction_gate','zero_undo_gate','rmw_phase_gate','commit_ingress_gate']))
 old=r.load('/home/youns/workspace/ele548-project-v14/o3_finite_v14/reports/MEASURED_BUILD_PLAN_B1.lock.json');gem=m.V9/'third_party/gem5-native-v9r2';old['consumers'].append({'source':str(gem/'src/cpu/o3/commit.cc'),'object':str(gem/'build/X86_PIPELINE/cpu/o3/commit.o')});overlay=S/'gem5_overlay/src';flags=['-I'+str(overlay),*old['flags']];out=B/'runtime/gem5_build_B4';out.mkdir(exist_ok=False);lock=freeze('CPU_BUILD_B4');plan=B/'reports/CPU_BUILD_PLAN_B4.lock.json';r.put(plan,{'source_lock':lock,'flags':flags,'old_objects':old['old_link_objects'],'runtime_config':str(S/'gem5_overlay')})
 def compile(pair):
  i,item=pair;src=Path(item['source']);relative=src.relative_to(gem/'src') if src.is_relative_to(gem/'src') else None
  if relative is not None and (overlay/relative).exists():src=overlay/relative
  obj=out/(str(i)+'_'+Path(item['object']).name);dep=out/(str(i)+'.d');run=m.invoke('cpu_compile_B4_'+str(i),[m.CC,*flags,'-MMD','-MF',dep,'-c',src,'-o',obj],600,15);return {'replace':item['object'],'object':r.ref(obj),'dependency':r.ref(dep),'execution':run}
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:objects=list(pool.map(compile,enumerate(old['consumers'])))
 replacements={x['replace']:x['object']['path'] for x in objects};inputs=[replacements.get(x['path'],x['path']) for x in old['old_link_objects']];assert len(inputs)==1516
 for z in old['old_link_objects']+old['old_static_libraries']:assert r.sha(z['path'])==z['sha256']
 binary=out/'gem5.protection_v18.opt';link=m.invoke('cpu_link_B4',[m.CC,'-o',binary,'-rdynamic','-O3','-Wl,--as-needed','-Wl,--no-keep-memory',*inputs,'-Wl,--start-group',*[z['path'] for z in old['old_static_libraries']],'-Wl,--end-group','-L/opt/miniconda3/lib','-lpython3.13','-lpthread','-lz','-lrt','-ldl'],600,50)
 deps={}
 for f in out.glob('*.d'):
  for n in f.read_text().replace('\\\n',' ').split(':',1)[1].split():deps[n]=r.ref(n)
 r.put(B/'reports/CPU_BUILD_B4.json',{'status':'PASS_NEW_B4_BUILD_NOT_CPU_QUALIFICATION','binary':r.ref(binary),'plan':r.ref(plan),'runtime_config':str(S/'gem5_overlay'),'objects':objects,'actual_dependencies':list(deps.values()),'link':link,'resources':r.snapshot()});print('BUILD_B4_PASS',flush=True)
if __name__=='__main__':main()
