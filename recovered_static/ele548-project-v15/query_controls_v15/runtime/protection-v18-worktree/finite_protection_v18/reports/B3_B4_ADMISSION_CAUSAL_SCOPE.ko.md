# B3 실패와 B4 수정의 인과 해석 범위

SOURCE FACT: B3 반복 SOURCE qsort ECC 로그는 raw76/77의 두 bit 사건 뒤 실제 DUE/reset/fallback 시작을 기록하고 `committed history without finite ingress credit`로 종료했다. 이 실행의 실패 시점 ingress count/reserved/prepared/level은 별도 저장하지 않았다. 따라서 실제 CPU에서 정확히 8개 callback이 몰렸다거나 queue-full만이 직접 원인이었다고 단정하지 않는다. 함께 실행된 P0는 정상 종료했고 두 원본을 보존했다.

IMPLEMENTED/TESTED RESULT: 같은 B3 production SourceAccess를 쓰는 C++ fixture에서 retirement8개를 먼저 허용한 뒤 지연 callback의 다섯 번째 입력이 ingress4 overflow하는 반례를 재현했다. 이는 실제 CPU에서 관측된 것과 같은 오류 경로의 한 사례이며 CPU 내부 queue trace를 대신하지 않는다. B4의64actual-retire fixture는105 backpressure cycles를 거쳐 모두 순서대로 한 번만 발행했다. 별도 fixture는 squash 예약 중 차단, pre-reset retirement의 뒤늦은 training이 refill을 오염시키지 않음, 이미 사용한 cycle의 새 control metadata112SBU가 두 번째 입력을 열지 않음을 검증했다.

NEW DERIVATION: retirement에서 확인한 committed-ready는 그 뒤의 지연된 BPU training까지 queue 공간·squash reservation을 보존하지 않는다. 또한 nGhist=0은 기존 source-credit release의 cycle 제한을 소비하지 않아 여러 callback이 뒤늦게 모일 수 있다. B4는 실제 retirement 시점의 resolved outcome를 같은 비중단 구간에서 finite ingress에 등록하고, 새 protected commit-used 상태로 입력 II1을 강제하며, training callback의 중복 등록을 제거한다. Controller는 실제 retired outcome와 기존 저장 상태만 사용한다.

검증 범위: C++ source/admission/metadata gate와 새 O3 checksum6·overlap6·mid-DUE6은 통과했다. Mid-DUE ECC에서 reset1/committed publication133/drain1을 실제 관측했다. 이는 전체 qsort 반복 오류 schedule와 독립 A/B/C/D의 통과를 뜻하지 않는다. 수정된 소스의 fresh normal18과 원래 고정 owner/input/rate/censoring 조건의 pilot→개발→독립 평가를 진행한다. B3의 실패를 B4 성공으로 교체하지 않는다.
