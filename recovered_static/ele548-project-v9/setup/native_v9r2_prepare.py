"""Install R2 into a private copied cache and lock sources before building."""
import json, shutil, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import native_v9_common as c

ROOT=c.ROOT;OUT=ROOT/'rate_state_v9/r2/runtime';CACHE=ROOT/'third_party/gem5-native-v9r2'

def main():
    for name in ['configs','reports','gates']:(OUT/name).mkdir(parents=True,exist_ok=True)
    source=OUT/'configs/source.lock.json';assert not source.exists(),'R2_SOURCE_ALREADY_FROZEN'
    assert CACHE.is_dir()
    assert c.load(ROOT/'rate_state_v9/source_continuation/runtime/reports/SOURCE_CONTINUATION.json')['status']=='PASS'
    cpp=c.load(OUT/'gates/CPP_GATE.json');assert cpp['status'].startswith('PASS')
    binding=c.load(OUT/'gates/CPP_GATE_BINDING.json')
    for name,digest in binding['source'].items():assert c.sha(ROOT/name)==digest,('CPP_TEST_SOURCE_CHANGED',name)
    c.verify_sources();old=c.load(c.OUT/'configs/PRODUCER.lock.json');assert c.sha(c.BINARY)==old['binary_sha256']
    protected={}
    for folder in [c.OUT,ROOT/'rate_state_v9/source_continuation/runtime']:
        for p in folder.rglob('*'):
            if p.is_file() and '__pycache__' not in p.parts:protected[str(p.relative_to(ROOT))]=c.sha(p)
    for name,digest in c.load(c.OUT/'configs/source.lock.json')['sources'].items():assert c.sha(ROOT/name)==digest;protected[name]=digest
    protected[str(c.BINARY.relative_to(ROOT))]=c.sha(c.BINARY);protected[str(c.CONFIG.relative_to(ROOT))]=c.sha(c.CONFIG)
    preservation=OUT/'configs/PRESERVED_R1.lock.json';assert not preservation.exists()
    c.write(preservation,dict(status='R1_COMPILED_SOURCE_PRODUCER_RAW_AND_PARTIAL_FAILURE_IMMUTABLE',hashes=protected,original_v8_lock=c.ref(c.OUT/'configs/PRESERVED_V8.lock.json'),failed_original_row='dijkstra_small.WHOLE_K1_REF_SCALE10000000000000000.V9_CONFIRMATION.1.0.A_DIR',no_failed_row_replacement=True))
    extensions={}
    for p in (ROOT/'gem5_rate_native_v9r2_ext').iterdir():
        if p.is_file():
            dst=CACHE/'src/cpu/pred'/p.name;shutil.copy2(p,dst);extensions[str(p.relative_to(ROOT))]=c.sha(p);assert c.sha(dst)==c.sha(p)
    scon=CACHE/'src/cpu/pred/SConscript'
    text=scon.read_text();assert "SimObject('BPPipelineV9.py'" in text and "Source('research_pipeline_v9_tage.cc')" in text
    text=text.replace("SimObject('BPPipelineV9.py', sim_objects=['PipelineV9TAGEBase', 'PipelineV9TAGE'])","SimObject('BPPipelineV9R2.py', sim_objects=['PipelineV9R2TAGEBase', 'PipelineV9R2TAGE'])")
    text=text.replace("Source('research_pipeline_v9_tage.cc')","Source('research_native_v9r2_tage.cc')");scon.write_text(text)
    files=dict(c.load(c.OUT/'configs/source.lock.json')['sources']);files.update(extensions)
    for p in (ROOT/'src/rate_native_v9r2').rglob('*'):
        if p.is_file() and p.suffix in ['.hpp','.cpp','.py','.md']:files[str(p.relative_to(ROOT))]=c.sha(p)
    transport={name:c.sha(CACHE/'src'/name) for name in c.load(c.OUT/'configs/source.lock.json')['transport']}
    config=ROOT/'gem5/o3_native_v9r2.py';assert config.exists()
    c.write(source,dict(status='PREBUILD_R2_SOURCE_FROZEN_NOT_CPU_QUALIFIED',pin=c.load(c.OUT/'configs/source.lock.json')['pin'],files=files,transport=transport,config=c.ref(config),cpp_gate=c.ref(OUT/'gates/CPP_GATE.json'),cpp_gate_binding=c.ref(OUT/'gates/CPP_GATE_BINDING.json'),r1_producer=c.ref(c.OUT/'configs/PRODUCER.lock.json'),r1_preservation=c.ref(preservation),copied_old_binary_sha256=c.sha(CACHE/'build/X86_PIPELINE/gem5.opt'),binary_must_not_run_before_new_build=True,scope='Native L0 LEGACY only, mirrored common pending68 endpoint152bits, ≥1 actual cycle correction/DUE hold, old algorithm/protection S*346 unchanged. New WHOLE populations require new comparison; old failure remains.',installed_extensions=extensions,source_commit=__import__('subprocess').check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()))
    print('PASS R2 installed and source-frozen; copied old binary is not qualified')

if __name__=='__main__':main()
