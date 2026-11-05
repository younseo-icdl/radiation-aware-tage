"""Verified continuation lock and readable entry point; preserve historical root locks."""
import json,subprocess,sys
from continuation_common import *
assert json.loads((OUT/'reports/G6_FINAL_AUDIT.json').read_text())['status'].startswith('PASS_G0_TO_G6')
required=['G4_CPU_DESIGN_V2.json','G5_CPU_HOLDOUT_V2.json','G5_SOURCE_ROBUSTNESS.json','G5_CPU_EXPOSURE_ROBUSTNESS.json']
for name in required:
 assert json.loads((OUT/'reports'/name).read_text())['status']=='PASS',name
producer=ROOT/'third_party/gem5-continuation/build/X86_STAGE0/gem5.opt'
compiler=subprocess.check_output(['bash','-c','source /opt/rh/gcc-toolset-11/enable\ng++ --version'],text=True).splitlines()[0]
source=json.loads((OUT/'configs/gem5_source.lock.json').read_text())
record=dict(status='VALIDATED_CONTINUATION_SOFTWARE_G0_TO_G5',
 source_preparation_lock_sha256=sha(OUT/'configs/gem5_source.lock.json'),
 source_preparation_status_note='PREPARED_GATE_PENDING describes preparation time; completed gates are referenced separately.',
 research_code_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
 gem5_pin=source['pin'],gem5_version='v25.1.0.1',source_hashes=source['sources'],
 gem5_opt=dict(path=str(producer.relative_to(ROOT)),sha256=sha(producer)),
 python=dict(version=sys.version,executable=sys.executable),compiler=compiler,
 rng_namespace_version=2,predictor_rng_seed=548,
 scope_sha256=sha(ROOT/'sources/protection_scope.lock.json'),
 gate_hashes={name:sha(OUT/'reports'/name) for name in required},
 executable_hashes={str(p.relative_to(ROOT)):sha(p) for p in (ROOT/'build').glob('continuation*') if p.is_file()},
 baseline_software_lock_sha256=sha(ROOT/'reports/software.lock.json'),
 build_CPU_timing_note='First build CPU timing lost; retained compiler log and conservative 3x wall charge. Subsequent timing files retained.',
 RTL_PPA_measured=False,TCAD='UNAVAILABLE_EXCLUDED_BY_USER',license_checkout='NOT_TESTED_NO_LICENSE_REQUIRED_FOR_THIS_STAGE')
write(OUT/'configs/software.lock.json',record)
(OUT/'reports/USER_ACTIONS_REQUIRED.md').write_text('# User actions\n\n현재 소프트웨어 continuation 완료에 필요한 외부 조치는 없습니다. 새 입력·제공 논문·검증한 source dataset으로 실험했습니다. 추가 SPEC 설치, PDF 업로드, Cadence license 변경을 요청하지 않습니다.\n\nG6에서 멈춥니다. 후보의 유효 오류 조건과 정상 경로 비용 가정을 먼저 논의할 자료를 제공했습니다. 실제 RTL/PDK/PPA 단계는 후속 범위 결정이 있을 때 진행하며 TCAD는 사용하지 않습니다.\n')
entry=ROOT/'reports/CONTINUATION_G6_REPORT.ko.md'
entry.write_text('# 최신 continuation 결과\n\nG0→G6 소프트웨어 평가를 완료했습니다. 이전 보고서와 root software.lock은 역사적 증거로 보존했습니다. 이번 continuation의 최신 자료는 아래 파일입니다.\n\n'+
 '- [결과와 후보](../continuation/runtime/reports/G6_HARDWARE_CANDIDATE_SHORTLIST.ko.md)\n'+
 '- [CERN·Flying Laptop 패턴 민감도](../continuation/runtime/reports/G5_MODEL_SENSITIVITY.ko.md)\n'+
 '- [하드웨어 측정 계약](../continuation/runtime/reports/G6_HARDWARE_CONTRACT.json)\n'+
 '- [최종 감사](../continuation/runtime/reports/G6_FINAL_AUDIT.json)\n'+
 '- [검증된 software lock](../continuation/runtime/configs/software.lock.json)\n'+
 '- [논의용 ZIP](BP_SEU_Continuation_G6_20261013.zip)\n\n실제 PPA와 물리적 SEU rate는 미측정입니다. N1의 성능 이득은 U0 유지 비용 가정 및 주입 조건에 의존합니다.\n')
print(record['status'])
