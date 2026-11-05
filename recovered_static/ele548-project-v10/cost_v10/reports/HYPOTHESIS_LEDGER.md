# V10 가설·결정 장부

상위 질문: 올바른 프로그램 실행과 필요한 성능을 유지하면서, 어느 TAGE 상태를 저장·보호·재계산해야 하는가? 이 장부는 새 charter 수신 후 작성했다. 초기 STA/P0/parity 자료를 이미 본 뒤이므로 그 부분을 새 사전등록/독립평가로 부르지 않는다. 실제 실행 전 고정 항목은 configs/ROUND.lock.json, PRODUCTION_INPUTS.lock.json, 기존135endpoint의300ps budget이다. 같은 CPU 세대를 바꾼 새 성능 campaign은0이다.

|ID|경쟁 설명/가설|가설을 가를 대조|현재 판정과 다음 행동|
|---|---|---|---|
|V10-A|R2의 빈칸 때문에 conventional 최선이 빠졌음 vs live 독립평가가 이미 완료됨|동결된 all6 clean18/fault144와 SOURCE/forcedK2/WHOLE 장부 읽기|Supported:162회 완료·정답PASS, 재실행0. n=2/program으로 동등성/보편 순위 확정 안 함.|
|V10-B|Direct의 TT15ps가 공통 stage 여유를 보장 vs source 경계/PVT에 민감한 작은 블록값|기존 routedDB 두 개를 같은135endpoint·TT/SS-cell+typRC로 읽기|전자는 Refuted-in-scope:SS direct32endpoint 위반, stored0. 전체 stage는 여전히 UNKNOWN.|
|V10-C|기존 stored-hash 면적만으로 recurrent가 싸다 vs fold200 저장·forward/inverse-undo까지 포함하면 비용 차이가 달라짐|실제 persistent200FF+update+hash와 exactdirect의 mapped 공통135output 비교|Supported-in-component-scope: recurrent962.640/direct641.466µm² mappedcellarea. source read/align/ownership 양쪽 외부라 totalcost는미확정. 신규 saved-fold restore 대체 없이 pinned inverse undo 사용.|
|V10-D|Incremental parity는 항상 더 작고 빠름 vs delta/검사 경계와 library mapping에 따라 서로 다른 비용|같은346payload/23word, 동일FF보존·clock·ports·load의 full-check/reencode 대 parity XOR legitimate-delta|개발 관측:incremental의 RMW 경로는 짧지만 area는 소폭 큼. 주기1/k 에너지 절약은 미측정·미주장.|
|V10-E|ECC/TMR의 저비용/고비용은 counterwidth만으로 결정 vs 실제 같은word codec/vote/feedback/FF가 필요|C++→RTL 정답/오류 gate, actual storage-bit map, same-boundary mapped cost|RTL64,155행 PASS. ECC A1 보고서 API 실패와 GLS Q_buf fixture 실패를 보존; export·기능·timing 판정을 분리. 일곱map actualstate 감사와전체64,155mappedfixture PASS. ECC−12ps/TMR0ps의boundarytiming을보존.|
|V10-F|짧은 task의 Poisson P0/P1 가중만으로 저율 장기 runtime 추정 가능 vs 잔류 피해·수명·반복 상호작용이 필요|별도 rate×state-window 노출 산술과 실제 retained-state 증거 구분|전자는 Refuted-as-inference. 실제 native 장기 damage kernel이 없어 장기 손익분기 UNKNOWN. DESIGN_SELECTION_MAP 참고.|

다음 구조 가설은 결과를 보고 고른 development 가설이다. 원본에서 갱신 시 fold를 통째로 다시 써서 lookup은 작은 stored hash로 유지하면 recurrence의 잔류 오염을 끊을 수 있다. 반대 설명은 full-fold update/rollback 경로, 추가200FF 노출과 source 공급 비용이 절약을 상쇄한다는 것이다. 이 변형의 소형primitive를 구현했고 C++/RTL3,650행과 RTL mid-cycle400fixtures가PASS했다. HOLD에서는오류가남고정상source를사용하는다음update에서전체F가덮어써졌다. 손상source는그대로재계산했다. gem5통합·성능·물리비용은미측정이다. 동시 새 주요 후보를 두 개 넘게 활성화하지 않는다.

## 실패 취급

- protection_rtl_A1: helper/public module 이름 충돌, 수정 후A2 RTL PASS. 원본 로그 보존.
- genus_preserve_probe_A1: unmapped leaf에 .preserve true 적용 거절(TUI210); exit0도 gateFAIL. 설치 공식 문서의 merge/delete 제어를 A2에서 실제24FF로 검증.
- map_secded_A1: actual467FF map 뒤 unusedQN을 timing startpoint로 준 TIM303. A2는 sequential instance query만 수정. A1을 성공으로 덮지 않음.
- gls_p0_A1: Q_buf UDP 출력 net deposit의 post-edge mismatch2573. 실제 내부 UDP state 변경과 같다고 보지 않음. A2는 sampling edge까지 static Q clamp 후release하여 별도 boundary 기능 gate PASS. 물리 SEU/internal UDP qualification 아님.

새 구현/평가는 이 장부의 과거 결과를 development로 사용하며, 후보를 바꾸고 같은 평가 seed를 독립 검증이라고 다시 부르지 않는다. CPU cap3361/3361 유지.

- overwrite_rtl_A1: root launcher가TB의recurrent/direct의존파일2개를누락해CUVMUR. 실제filelist의두파일을추가한A2에서source변경없이PASS. 원시실패와명령보존.
