"""Freeze V9 inputs/source while preserving the completed original workspace."""
from pathlib import Path
import argparse,datetime,hashlib,json,shutil,subprocess

ROOT=Path(__file__).resolve().parents[1]
OLD=Path('/home/youns/workspace/ele548-project')
OUT=ROOT/'rate_state_v9/runtime'
TARGET=ROOT/'third_party/gem5-native-v9'
PIN='c8222cc67a399bfc01e8658dd14b30d5bfd634f9'

def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as stream:
  for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
 return h.hexdigest()
def put(path,data):
 path.parent.mkdir(parents=True,exist_ok=True)
 assert not path.exists(),('IMMUTABLE_FILE_EXISTS',str(path))
 path.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')
def preserve():
 dest=OUT/'configs/PRESERVED_V8.lock.json'
 if dest.exists():return verify_preserved()
 parent=OLD/'rate_state_v5_pipeline_v8/runtime/configs/PRESERVED_V7.lock.json'
 hashes=dict(json.loads(parent.read_text())['hashes'])
 folders=['rate_state_v5_pipeline_v8','src/rate_pipeline_v8','src/rate_state_v8','src/rate_state_v8_support','gem5_rate_pipeline_v8_ext']
 for name in folders:
  for path in (OLD/name).rglob('*'):
   if path.is_file() and '__pycache__' not in path.parts and path.suffix not in ['.pyc','.tmp']:
    hashes[str(path.relative_to(OLD))]=sha(path)
 for path in list((OLD/'scripts').glob('pipeline_v8_*.py'))+[OLD/'gem5/o3_pipeline_v8.py',OLD/'setup/build_pipeline_v8.sh',OLD/'docs/00_LATEST_DECISIONS.ko.md',OLD/'AGENTS.md',OLD/'reports/BP_SEU_Pipeline_v8_Completed_20261016.zip',OLD/'third_party/gem5-rate-pipeline-v8/build/X86_PIPELINE/gem5.opt']:
  hashes[str(path.relative_to(OLD))]=sha(path)
 put(dest,dict(status='ORIGINAL_V8_AND_ANCESTORS_IMMUTABLE',at=datetime.datetime.now(datetime.timezone.utc).isoformat(),original_root=str(OLD),parent_sha256=sha(parent),hashes=hashes))
 return verify_preserved()
def verify_preserved():
 d=json.loads((OUT/'configs/PRESERVED_V8.lock.json').read_text())
 for name,digest in d['hashes'].items():assert sha(OLD/name)==digest,('ORIGINAL_CHANGED',name)
 print('PASS original preservation',len(d['hashes']))
 return d
def inputs():
 dest=OUT/'configs/development_inputs.lock.json'
 if dest.exists():return json.loads(dest.read_text())
 original=OLD/'rate_state_v5_pipeline_v8/runtime/configs/CANDIDATE_FROZEN.lock.json'
 source=json.loads(original.read_text());items=[]
 for item in source['inputs']:
  result=dict(item)
  for key in ['binary','input','native_stdout']:
   old=OLD/item[key];new=OUT/'inputs/development'/item['name']/old.name;new.parent.mkdir(parents=True,exist_ok=True);assert not new.exists();shutil.copy2(old,new)
   result[key]=str(new.relative_to(ROOT));assert sha(new)==sha(old)
  result['scope']='Previously seen V8 input; development only, not independent input holdout'
  items.append(result)
 checksum=dict(name='checksum')
 for key,name in [('binary','build/checksum_freestanding'),('input','continuation_v3/runtime/inputs/checksum/ignored.dat'),('native_stdout','continuation_v3/runtime/inputs/checksum/native.stdout')]:
  old=OLD/name;new=OUT/'inputs/checksum'/old.name;new.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(old,new);checksum[key]=str(new.relative_to(ROOT));checksum[key+'_sha256']=sha(new)
 result=dict(status='FROZEN_BEFORE_V9_CPU',original_root=str(OLD),source=dict(path=str(original),sha256=sha(original)),programs=items,checksum=checksum)
 put(dest,result);return result
def freeze():
 verify_preserved();inputs()
 assert subprocess.check_output(['git','-C',TARGET,'rev-parse','HEAD'],text=True).strip()==PIN
 assert not (OUT/'configs/PRODUCER.lock.json').exists(),'Frozen producer requires a new namespace'
 config=ROOT/'gem5/o3_native_v9.py';ext=ROOT/'gem5_rate_pipeline_v9_ext'
 for path in ext.iterdir():
  if path.is_file():assert sha(path)==sha(TARGET/'src/cpu/pred'/path.name),('EXTENSION_NOT_COPIED',path.name)
 parent=OLD/'rate_state_v5_pipeline_v8/runtime/configs/source.lock.json';old=json.loads(parent.read_text())
 paths=[]
 for folder in ['src/rate_pipeline_v9','gem5_rate_pipeline_v9_ext','src/rate_state_v9','src/rate_state_v9_support']:
  paths.extend(p for p in (ROOT/folder).rglob('*') if p.is_file() and p.suffix in ['.hpp','.h','.hh','.cc','.cpp','.inc','.py'])
 paths.extend(p for p in (ROOT/'src').rglob('*') if p.is_file() and p.suffix in ['.hpp','.h','.hh','.cc','.cpp','.inc'] and not any(part.startswith('rate_') for part in p.parts))
 transport={name:sha(TARGET/'src'/name) for name in old['transport']}
 for name,digest in transport.items():
  p=OUT/'sources/TRANSPORT'/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(TARGET/'src'/name,p);assert sha(p)==digest
 data=dict(status='PREPARED_V9_NOT_GATED',pin=PIN,sources={str(p.relative_to(ROOT)):sha(p) for p in sorted(set(paths))},transport=transport,config=str(config.relative_to(ROOT)),config_sha256=sha(config),upstream_opt_sconscript_sha256=sha(TARGET/'src/SConscript'),preservation_lock_sha256=sha(OUT/'configs/PRESERVED_V8.lock.json'),parent_source_lock=dict(path=str(parent),sha256=sha(parent)),bootstrap_sha256=sha(OUT/'configs/BOOTSTRAP.json'),final_extension_copy_sha256=sha(OUT/'configs/FINAL_EXTENSION_COPY.json'),source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),private_backend=['src/rate_state_v9','src/rate_state_v9_support'],native_semantics='Synchronous actual L0 callback; native L/II0, no journal; transport L1 object unused. Observation changes do not change predictor algorithm.')
 put(OUT/'configs/source.lock.json',data)
 print('V9 source/config/transport/bootstrap frozen before build',len(data['sources']))
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--phase',choices=['preserve','inputs','freeze'],default='freeze');args=parser.parse_args()
 {'preserve':preserve,'inputs':inputs,'freeze':freeze}[args.phase]()
