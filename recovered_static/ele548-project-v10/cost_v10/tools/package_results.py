"""Private allowlist-style text/source/vector delta; never copy PDK/models/DB/cache."""
from pathlib import Path
import hashlib,json,zipfile
from budget import BASE,ROOT,check
exclude_parts={'artifacts','xcelium.d','__pycache__','fv','.git'}
def allowed(p):
 rel=p.relative_to(ROOT)
 if any(x in exclude_parts for x in rel.parts):return False
 if p.suffix in {'.db','.png','.o','.so','.pyc'} or '.local.' in p.name:return False
 if p.name.startswith(('BUNDLE','POST_PACKAGE')):return False
 if not p.is_file() or p.is_symlink():return False
 with p.open('rb') as f:
  magic=f.read(4)
 if magic==b'\x7fELF':return False
 return p.suffix.lower() in {'.py','.sh','.tcl','.sv','.v','.hpp','.h','.cpp','.cc','.md','.txt','.json','.csv','.tsv','.ticks','.f','.time','.rpt','.log','.sdc','.stdout','.stderr','.dat','.version','.history','.cmd'} or p.name=='.gitignore'
check();namespace_roots=[BASE,ROOT/'native_lifetime_next'];files=sorted(p for namespace in namespace_roots if namespace.exists() for p in namespace.rglob('*') if allowed(p))
manifest={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
contents=BASE/'reports/BUNDLE_CONTENTS.sha256';contents.write_text(''.join(h+'  '+n+'\n' for n,h in manifest.items()))
meta=BASE/'reports/BUNDLE.json';meta.write_text(json.dumps(dict(status='PRIVATE_LOCAL_V10_COMPONENT_RESEARCH_DELTA',payload_files=len(files),contents_sha256=hashlib.sha256(contents.read_bytes()).hexdigest(),new_gem5_trials=0,global_cpu3361_preserved=True,full_stage='UNKNOWN',hardware_qualified_candidates=0,excludes=['PDK/library/verilogmodel/LEF/QRC','mappedDB','Xceliumcache/executables','fullsourcePDFextracts/images'],resources_before_packaging=check()),indent=2)+'\n')
a=BASE/'artifacts';a.mkdir(exist_ok=True);z=a/'BP_SEU_V10_COMPONENT_RESEARCH_RESULTS.zip';assert not z.exists(),'IMMUTABLE_ARTIFACT_EXISTS'
with zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as f:
 for p in [*files,contents,meta]:f.write(p,str(p.relative_to(ROOT)))
with zipfile.ZipFile(z) as f:
 assert f.testzip() is None
 for n,h in manifest.items():assert hashlib.sha256(f.read(n)).hexdigest()==h,n
 assert hashlib.sha256(f.read(str(contents.relative_to(ROOT)))).hexdigest()==json.loads(meta.read_text())['contents_sha256']
 assert len(f.namelist())==len(files)+2
record=dict(status='PASS_CRC_ALL_PAYLOAD_SHA256',archive=str(z),archive_sha256=hashlib.sha256(z.read_bytes()).hexdigest(),archive_bytes=z.stat().st_size,payload_files=len(files),archive_entries=len(files)+2,resources_after_packaging=check())
(BASE/'reports/POST_PACKAGE_VERIFICATION.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2))
