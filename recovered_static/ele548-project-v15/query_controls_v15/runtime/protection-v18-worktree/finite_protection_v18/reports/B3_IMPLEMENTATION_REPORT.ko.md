# B3: RMW primary SEU 재인코딩 결함 수정

DONE: `rmw_primary_boundary_A1_run`은 B2에서 raw source SBU를 실제RMW write와encoder input등록사이에넣었을때parity/ECC/TMR 모두wrong=1/detected=0임을재현했다. 이실패는보호대상S*내부이므로B2를올바른protectedbaseline으로확대해사용하지않는다. 기존G2원본·source/config/ELF·정상42CPU는보존했다. 진행중L2 CPU2는정상종료까지두었고새dispatch를bookkeepinglock으로막았다. 그뒤활성CPU0을확인하고이round의coordinator만종료했으며어떤gem5process에도signal을보내지않았다.

수정: 실제RMW가만든post-image raw130/path16을outputregister에저장하고,실제fold reduction결과와함께encoder입력으로전달한다. 이후physicalsource를검증없이다시읽지않는다. Injector/golden/미래실제branchoutcome을controller에주지않는다. Bulkundo에서이미사용하던raw130 register를모든RMW에활성화했고path16을추가했다. Direct에는post-image146bit가추가된다. 실제manifest를갱신했고L/II/ports/queue계약은그대로다.

검증: B3 scope/vector/native source guard/transport/transaction/zeroUndo회귀PASS. 별도S*346×5시점×5정책=8650 source-SBUphase사례PASS: ECC/TMR3460복원또는자연overwrite,frequentparity1730검출/제외또는overwrite,periodic1730due검출또는overwrite,P0자연overwrite547. 실제O3는새GUgate로RMW후primaryrawSBU를강제했고parity frequent/N1/ECC/TMR4개모두정답·protocol·검출gate를통과했다. GU는기전gate에만쓰며통계campaignschedule에는쓰지않는다.

새L1 manifest: P0 77625/parity각77671/ECC77867/TMR79009/Direct76609 logicalbits,semanticunion79427. 표는실제tick0manifest에서읽은모델storage다. S*346/23word/parity23/ECC121/TMRextra692는그대로다. WHOLE은새register까지노출하고기존per-bitstress계수·RNGv2·owner/input·종료censoring을유지한다.

NOT DONE: B3정상18개를새로측정중이며개발102/독립408fault결과는아직없다. B2정상값을B3새실행으로복사하지않는다. 인코더operand등추가uncodedlatch의단일SEU가ECCcheck나두TMRreplica로전파되는경계는여전히전체manifest에서평가하며모든bit완전복구를주장하지않는다.

VERIFIED ASSUMPTIONS: Sourcecheck/encode/provider stage-fit은모델가정이다. 원래native L0는정상reference이며matched-native faultB는이matrix에없다. Primary A/B/C/D는공통finiteP0기준이다. SourceL1/2와provider/tableLUT1의구분,stall단위·제외storage·retention재진입은resourcecontract를따른다.

BLOCKERS: 기존사용자CPUcap4143안에서진행한다. 완전한B3정상18재측정을더하면실제630/global4161회가필요해+18만별도로질문했다. 시간160coreh·모든disk/32slots한도는유지한다. 실제사용자답변이오기전4161승인파일을만들지않는다.

NEXT: B3 freshnormal18→원래native reference6→SOURCEpairedpilot2를포함한개발102→후보/resourcefreeze→freshinputnormal18/독립fault408. 현재code/config/binary는불변이며모든case는별도B3label/outputnamespace를쓴다. RTL/Cadence/SPICE/TCAD는실행하지않는다.
