# 마지막 B4 코드 복구 후보

이 폴더는 과거 B4 스냅샷에 도달한 텍스트 후보를 따로 모은 것입니다. 알고리즘을 새로 구현하거나 바꾸지 않았고 코드 bytes와 원래 경로의 연결을 SOURCE_RECOVERY_MANIFEST.json에 보존했습니다. 빌드/실험을 다시 실행하지 않았습니다.

`src/`에는 유한 source service/controller/lookup/early receiver와 parity/ECC/TMR 보호 구현이 있습니다. `gem5_overlay/`에는 회수한 predictor/O3 연동이 있습니다. 테스트/runner도 원문 후보로 보관하되 실행하지 않았습니다.

당시 실제로 출력된 SHA와 일치한 B4 cpu.cc가 있지만, 전체 source lock이 되살아난 것은 아닙니다. 절대 include 경로를 임의로 바꾸지 않았으며, 아래 누락 연구 헤더와 upstream/generated dependency 때문에 현재 실행 가능한 완성본으로 판정하지 않습니다.

누락된 연구 include:
- `../predictor/tage_adapter.hpp`

전체 과거 코드 후보는 상위 recovered_static/와 recovered/에 있습니다. 원시 실험 로그·ELF·원본 완료 ZIP은 복구되지 않았습니다. 예전에 다운로드한 2026-10-18 전체 인계 ZIP이 추가로 확보되면 실제 source snapshot과 대조해 복구를 보완할 수 있습니다.

추가 검증: O3 cpu.cc, o3_protection_v18.py와 observer_v18.py의3개 bytes가 기록된 최종B4 SHA와 일치했습니다(VERIFIED_COMPONENTS.json). support_reference/는 누락 v9 adapter에 대한 이전 모델의 참조 후보이며 최종동일성을 증명하지 않습니다.
