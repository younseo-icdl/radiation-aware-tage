# Blockers

현재 사용자 조치가 필요한 외부 의존성은 없다. CPU 결과 gate는 아직 실행 전이며, 별도 gem5 build가 진행 중이다.

해결 기록: 첫 gem5 build의 `param_ContinuationTAGEBase.o` 컴파일에서 `predictor/tage_adapter.hpp` include path가 없었다. Production access와 standalone snapshot state를 분리하고 relative include로 수정했다. 원시 첫 compiler log `G4_BUILD_1.log`는 보존했다. 두 번째 build에서 새 module의 컴파일을 통과했고 전체 link 완료를 기다린다.

C++ 첫 build는 동일한 snapshot 필드를 서로 다른 type으로 정의한 compile 오류였다. Existing TageState::Snapshot alias로 수정해1,089개 unit cases와418개 replay를 통과했다. 이후 code review에서 shadow-DUE reset 후 현재 actual branch를 보존하는 순서를 수정했으며 final source 재검증을 pending으로 표시한다.

초기 build의 `/usr/bin/time` 파일을 두 번째 build가 열면서 덮어썼다. 첫 build CPU 사용량은 정확 측정으로 표현하지 않고, script 생성/첫 log 종료 timestamp에서 얻은 wall span의3배를 보수적인 budget charge로 사용한다. Compiler raw log는 그대로 유지한다. 이후 attempt별 timing을 별도 파일로 보존한다.
