#!/usr/bin/env python3
"""Closure bindings for this pilot; preserve the immutable completed baseline."""
import json
from pathlib import Path
from summarize_e3_cpu import sha
ROOT=Path(__file__).resolve().parents[1]
def read(p):return json.loads((ROOT/p).read_text())
def main():
    c=read('configs/periodic_extension.lock.json');cpp=read('reports/PERIODIC_CPP_DESIGN.json')
    cpu=read('reports/PERIODIC_CPU_EVAL.json');gate=read('reports/PERIODIC_CPU_GATE.json')
    summary=read('reports/PERIODIC_EXTENSION_SUMMARY.json');model=read('reports/PERIODIC_MODEL_SUMMARY.json')
    selection=read('sources/periodic_policy_selection.lock.json');old=read('sources/gem5_e3_source.lock.json')
    assert cpp['completed_runs']==cpp['planned_runs']==84 and cpu['completed_runs']==cpu['planned_runs']==42
    assert gate['status']=='PASS_ISOLATED_PERIODIC_REAL_O3_GATE' and gate['trials']==13
    assert summary['status']=='PASS_AUDITED_PERIODIC_EXTENSION_PILOT' and not summary['failures']
    assert summary['campaign_sha256']==sha(ROOT/'reports/PERIODIC_CPU_EVAL.json')
    assert summary['analysis_source_sha256']==sha(ROOT/'scripts/summarize_periodic_extension.py')
    assert model['status']=='PASS_AUDITED_CONDITIONAL_MODEL_HOLDOUT_PILOT' and model['campaign_sha256']==sha(ROOT/'reports/PERIODIC_MODEL_HOLDOUT.json')
    assert model['analysis_source_sha256']==sha(ROOT/'scripts/summarize_periodic_models.py')
    assert selection['CPP_design_sha256']==sha(ROOT/'reports/PERIODIC_CPP_DESIGN.json') and selection['config_sha256']==sha(ROOT/'configs/periodic_extension.lock.json')
    assert sha(ROOT/'sources/protection_scope.lock.json')==c['scope_sha256']=='dec5020e5a504d0cdf49589e0acc4d2f7e8aa6c61798f61685b468d6dfdefe7b'
    assert gate['baseline_binary_preserved_sha256']==sha(ROOT/'third_party/gem5-e3/build/X86_STAGE0/gem5.opt')
    for p,h in old['shared_code'].items():assert sha(ROOT/p)==h
    for p,h in old['modified_files'].items():assert sha(ROOT/'third_party/gem5-e3'/p)==h
    design={t['seed'] for t in cpp['tasks']};assert not design.intersection(t['seed'] for t in cpu['tasks'])
    renderer=read('reports/PERIODIC_EXTENSION_REPORT.json')
    assert renderer['report_sha256']==sha(ROOT/'reports/PERIODIC_EXTENSION_REPORT.ko.md')
    for p,h in renderer['source_hashes'].items():assert sha(ROOT/p)==h
    assert renderer['generator_sha256']==sha(ROOT/'scripts/render_periodic_report.py')
    assert 'Ran 39 tests' in (ROOT/'reports/periodic_extension/python_tests.log').read_text()
    assert (ROOT/'reports/periodic_extension/cpp_correctness.log').read_text().startswith('PASS')
    paths=['reports/PERIODIC_CPP_DESIGN.json','reports/PERIODIC_CPU_GATE.json','reports/PERIODIC_CPU_EVAL.json','reports/PERIODIC_EXTENSION_SUMMARY.json','reports/PERIODIC_MODEL_HOLDOUT.json','reports/PERIODIC_MODEL_SUMMARY.json','sources/periodic_policy_selection.lock.json','sources/gem5_periodic_source.lock.json','sources/periodic_literature.lock.json','sources/periodic_e4_functional_handoff.json','reports/PERIODIC_EXTENSION_REPORT.json','reports/PERIODIC_EXTENSION_REPORT.ko.md','reports/periodic_extension/figures/periodic_cpu_comparison.png','reports/periodic_extension/figures/periodic_cpu_comparison.pdf']
    record={'status':'PASS_REVIEWED_OPTIONAL_PERIODIC_SOFTWARE_PILOT','evidence_hashes':{p:sha(ROOT/p) for p in paths},'scope_preserved':True,'old_producer_preserved':True,'design_eval_seed_split':True,'selection_interval':selection['selected_interval'],'actual_RTL_PPA_measured':False,'remaining_pilot_required':[],'limitations':['assumed C1/R4 and added update lane0 cycles','fixed2programs and targeted payload only','one CPU rate; no general lambda threshold','five-seed single-event quantiles not certified populationp95','two-seed/source-pattern means exploratory','adaptive/rebuild schemes unimplemented'],'review':'actual completed statistics and scientific PNG visually inspected; metadata/raw counters/config/event pairing audited by summaries','audit_source_sha256':sha(Path(__file__))}
    (ROOT/'reports/PERIODIC_EXTENSION_AUDIT.json').write_text(json.dumps(record,indent=2)+'\n')
    print(record['status'])
if __name__=='__main__':main()
