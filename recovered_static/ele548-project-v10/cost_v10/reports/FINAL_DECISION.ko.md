# 현재 결정

**구성요소 비용의 비교 경계를 넓히면 결론이 달라졌다.** 기존 stored-hash-only 결과로는 direct가 컸지만, 실제fold200FF·forward/inverse-undo를 포함한 새 mapped boundary에서는 recurrent962.640µm², direct641.466µm²였다. 반면 기존routedDB의directSS-cell+typRC는379ps로가정budget을79ps넘었다. 따라서 저장/정상갱신비용과lookup지연을교환하는문제이며, 전체CPU/PPA승자는아직없다.

## DONE

- 기존R2 all6의162회완료와K2층을live파일로확인해재사용했다. 수정전raw·실패·source/config/binary/archive를보존했고새CPU실행은0이다.
- 실제23word346bit의P0·빈번parity·증분parity·SECDED·TMR primitive를C++/RTL64,155행으로검증했다. 합성후실제저장346/369/369/467/1038bits와서로독립인검사·복제fan-in을감사했다. mapped Q-boundary sampling/edge/RMW fixture64,155행도PASS다. 내부UDPstateSEU나siliconqualification은아니다.
- pinned TAGE의persistentfold200·forward/inverseundo·같은135hash출력을C++/RTL/mapped3,804행으로검증했다. 실제state200/0bits를확인했다. 저장된fold를그대로복원하는shortcut으로기본rollback을바꾸지않았다.
- 기존두routedDB의135outputs전체TT/SS-cell을읽었다. rise/fall·late/early2160개실제보고서를보존했다. SS는cell125°C+기존typicalRC25°C로RCworstsignoff가아니다.
- rate×state-window선택지도와signedowner장부를완성했다. low-rate장기runtime·관측밖tail·energy는UNKNOWN으로남겼다.
- 첫비용결과뒤다음가설을실제로진행했다. **갱신때원본으로fold전체덮어쓰기**소형primitive를구현하고C++/RTL3,650행과400mid-cyclefoldfaultfixture를통과했다. 정상source다음update는oldfold잔류오염을끊지만, 손상source는그대로재계산하고HOLD는오류를유지했다. 이변형의gem5통합·성능·물리비용은아직없다.

## 비교군과 유효·불리·미확정 영역

SOURCE의현재n2/program자료에서frequent검출·재학습이direct보다qsort/dijkstra에서조금빨랐다. 사후최소값은프로그램마다달랐다. 별도강제K2에서는qsort direct와TMR동률, dijkstra SECDED가direct보다평균3609cycles빨랐다. 이K2층을자연CHARM에서관측한MCU로합치지않는다. mandatoryP0/P_ED/P_ECC/P_TMR및periodic은모두남긴다. 단일“최선conventional”을새평가결과로골라독립검증했다고하지않는다.

현재소형SS경계에서는변경없는direct를2GHz전체stage적합하다고주장할수없다. 저장fold의lookup은짧지만저장·update비용이있다. ECC는이parallel23word구현에서setup−12ps, TMR은0ps였으며이것이불가피한추가CPUcycle의증거는아니다. codeword/ports/checker의합리적최적화기회를기존보호에도준다. 실제activity없는energy우위는주장하지않는다.

**하드웨어검증완료후보0개.** 다음조사대상은①원본직접fold의source공급/lookup지연경계, ②조회시저장fold를쓰고update마다전체재계산하는primitive다. 후자는새주요구조1개로만활성화한다. 기존source/shadow재구성·단계적bank복귀와실패한group/FIFO탐색은archive에남기며근거없이재개하지않는다.

## 다음 결정과 실제 blocker

최우선CPU공백은R2native에서같은predictor를오래유지할때한사건의피해가얼마나남는가이다. 기존짧은종료창을장기runtime로외삽하지않는다. 재사용가능한persistentwrapper가있는지확인한구체적다음batch는`NEXT_NATIVE_LIFETIME_PLAN.ko.md`와config에정리한다. 새후보를평가하기전에기존여섯방식의retained피해부터공통generation에서확인한다.

추가gem5는global3361/3361한도때문에발행하지않았다. 이번물리round의7productionmappedtop과새route0도유지했다. overwrite의다음단계는실제operandavailability/rollback/freshness/ports를붙인통합gate및같은범위의비용검증이며, 소형primitivePASS로이를대체하지않는다. chartermacro/CPU/SRAM범위는자동확대하지않는다. 설치·licenseblocker는없으며실제checkout은원시로그에있다.

## novelty와 아직 못 말하는 것

BADGR PDFp3§III/Fig3에직접XOR와recurrentfolding이있다. 최초directfolding/historyconsistency/selectiveprotection을주장하지않는다. 검증할기여는오류가오래남는상태표현과정상유지·source/복구비용이,어떤event/lifetime조건에서보호선택을바꾸는지이다. 새mappedarea관측과SS실패조건은그경계를좁혔지만, conditionaltotalPareto우위는아직Inconclusive다.
