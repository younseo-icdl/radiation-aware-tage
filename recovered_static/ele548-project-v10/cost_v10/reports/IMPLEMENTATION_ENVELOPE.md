# 측정 범위와 구현 조건

IMPLEMENTED/TESTED RESULT: `COMPONENT_RESULTS.json`의 일곱 mapped top은 같은28HPC+ NVT TT0.9V25°C library/LEF, 4threads, medium generic/map/opt, 입력arrival50ps/slew20ps, 출력load5fF/reserve100ps, period500ps/setupU50ps를 사용했다. 실제 sequential 회로는 clk_i를 clock으로 제약했다. Direct에는 인공 launch/capture FF를 넣지 않았다. 모든 설계의 실제 state는 같은 merge/delete 보존 원칙을 적용했다.

|Primitive|실제 state bits|Mapped cell area µm²|최악 slack ps|범위|
|---|---:|---:|---:|---|
|무보호 word bank|346|1320.858|78|23word legitimate-XOR RMW|
|빈번 parity word bank|369|1994.706|6|read/selected-update 검사·full reencode|
|증분 parity word bank|369|2028.474|2|외부 주기의read검사·legitimate-delta parity 유지|
|SECDED word bank|467|6438.600|−12|실제23word codec, decode-before-RMW, correction feedback/DUE word hold|
|TMR word bank|1038|4699.044|0|3copy vote/feedback, correlated-copy 한계 유지|
|순환 fold 저장·갱신·hash|200|962.640|5|실제persistentFF, forward/inverseundo,135outputs|
|원본에서 직접 fold·hash|0|641.466|25|현재alignedraw130→같은135outputs|

이는 배치 전 global-interconnect estimate의 mapped cell area/timing이다. `Net-Area`를 실제 routed area로 합산하지 않는다. 최악 slack은 output·reg setup·reset fanout 등 서로 다른 path class를 포함한다. Direct의275ps와 recurrent의 reset378ps를 동일lookup경로 차이로 빼지 않는다. 구분한 in2out/in2reg/reg2reg/reg2out의 실제 first-worst-slack 경로는 JSON과 raw reports에 남겼다. 예컨대 recurrent reg2out122ps는clk-to-Q 포함이며 lookup source 경계가 direct raw input과 다르다.

NEW DERIVATION: 이 local boundary에서 fold200과 forward/inverseundo까지 포함하면 direct mapped area가 recurrent보다321.174µm² 작다(recurrent를 분모로 약33.36%). 기존 stored-hash-only275.184µm²와 direct645.498µm²의 routed비교는 다른 경계다. 두 결과를 같은 면적표로 섞거나 whole-predictor 우위로 확대하지 않는다. 이 차이보다 direct 전용 source read/align/ownership 구현 부담이 크면 현재 이득은 소진될 수 있다. 공통부분이 실제 공통인지도 후속 구현으로 확인해야 한다.

## 저장·포트·service·안전 불변식

- History 경계: pc32/path16/currentalignedraw130/transitionraw131/cmd2/reset/clock 입력, index63/tag72 출력. bit0가최신. FORWARD의step은삽입후, UNDO의step은제거전이다. L130의h[130] tail은실제retention operand이며 없다고0으로채우지 않는다.
- 한 edge에 FORWARD 또는 UNDO 한 건. CORRECT는UNDO→FORWARD 두 edge. update operand와 source ownership은외부다. 원래algorithm을 saved-fold snapshot restore로 바꾸지 않았다.
- Word-bank 경계: 외부legitimate delta346/word mask23/check/update/reset/clock 입력과 current346/payload346/check121/6flags×23의 공통진단출력. 모든word를병렬로접근하는primitive다. 실제 predictor의arrayports/II/finitequeue/service를 구현했다고 하지 않는다.
- ECC121과 parity23, TMR추가692는실제FF에포함. 실제state비트→FF/Q manifest로독립성확인. 별도controller/transport/epoch/queue가무료라는뜻은아니며 이primitive외부다.
- ECCselectedUPDATE는correction후RMW, DUE는그wordhold. 이것이livefullpolicy의전체23wordreset/refill130/epoch/drain을구현한것은아니다. refill130은updates이며130cycles로대체하지 않는다.
- Incremental parity는검사시점외부, oldparity XOR정상delta의parity. check_en0에도combinational망이toggle가능하므로1/kenergy절약미측정. wide-delta발생기·특화historytap의비용도외부다.
- Recurrentfold200을historyblock에넣은뒤S*=346word-bankarea를그대로더하면fold200을이중계상한다. direct에는사라진foldbit를no-op공격으로넣지않는다. fullcost정합composition은미구현이다.

## routed endpoint와 source arrival의 조건

별도 `STA_REPORT.ko.md`는 기존routedDB를읽은2160개보고서다. TT direct285ps/stored201ps; SS0.81V125°C cell+동일typRC25°C direct379ps/stored266ps. directSS32/135endpoint가300pslocalbudget을초과했다. 새route는0이다.

NEW DERIVATION: virtualperiod500−outputreserve100−setupU50=350ps에서 입력허용도착은350−localdata다. 기존routeddirect최악TT는65ps, SS는−29ps다. 따라서 **이매핑을유지한SS에서sourcearrival만개선해도2GHz가된다는결론은불가**다. 가정된50psarrival를유지하면79ps의local논리/부하/PVT개선또는period조건변경이필요하다. 이는CPU허용clock측정이아니다. 실제rawstorage/read/align/provider/SRAM/CTS가추가된다. SS는RCworst/온도125°C배선signoff가아니다.

## 정확성 증거와 남은 UNKNOWN

C++/RTL64,155protectionrows와3,804historyrows가일치했다. Mapped64,155word-bankrows와3,804historyrows도zero-annotation정상/edge/Q-boundary-clamp검증PASS다. 출력Q를samplingedge까지clamp후release한fixture이며UDP내부memory SEU·metastability·실리콘physics검증이아니다. 최초Q_bufnetdeposit실패를보존했다.

FULL_STAGE, 실제source/read/align/retention/rollback ownership, 실제finiteports/II, 전체보호controller, switching energy, RCworst/OCV/SI/CTS/signoff는UNKNOWN. mappedECC−12ps와TMR0ps는숨길toolfailure가아니라이경계의설계관측이다. conventional에도적합한parallelism/codeword/port/implementation개선기회를주어야하며, 이단일구현으로불가피한추가cycle을부과하지않는다.
