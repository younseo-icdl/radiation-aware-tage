"""Published contract of the actually frozen prototype, including failure bounds."""
from v5_common import ROOT,write,sha
import json
F=ROOT/'rate_state_v5/results';F.mkdir(exist_ok=True)
R4=ROOT/'rate_state_v5/runtime';R5=ROOT/'rate_state_v5/runtime_r5'
for name in ['RATE_ANCHORS_AUDIT.json','NOVELTY_EVIDENCE_MATRIX.md']:
    (F/name).write_bytes((R4/name).read_bytes())
old=(R4/'STATE_CONTRACT.md').read_text()
(F/'STATE_CONTRACT.md').write_text(old+'''

## Frozen R5 transport change and observed limits

IMPLEMENTED/TESTED RESULT: R5 source-only and clean comparisons use a shared producer after19 checksum/queue gates and18 exact full-program baseline compatibility checks. Within one BPU squash callback, up to1000 undone source insertions are reduced into one count10/path16 packet. Nested squash boundaries are handled; the aggregate flushes before any corrected append. The helper accumulator has no state between non-yielding callbacks and is excluded as combinational SET, not presented as protected persistent storage.

The dedicated64-token queue now has30 payload+7 SECDED bits per entry,42 control+7 code bits:2417 bits. Append takes1 cycle, aggregated undo2 cycles. The configured minimum launch gap is1, but this is a single non-pipelined RMW server: effective append II1 and effective undo II2, with no second job in flight. Mixed A append/U undo packets require at least A+2U service cycles, excluding arrival gaps/stalls. The optimistic undo1 sensitivity is not primary. All source writes and head/path changes publish at service completion, not enqueue. PHT learning remains on the pinned schedule, not globally serialized. Pending source demand and the actual BPU occupancy block new reads as necessary.

The declared direct population is65024 table/bimodal +130 active raw +16 path +1000 rollback cells +11 head +68 pending lookup +2417 queue =68666 bits. Removed200 folded bits have no physical target in direct variants. Whole-population schedules reject absent latent sites rather than insert pseudo-events. Recurrent NATIVE has65370 bits; the legacy finite-policy endpoint has separate manifest populations.

Population comparability LIMIT: the legacy NATIVE manifest counts active raw130 and excludes upstream backing-history pointer/retention and BranchInfo snapshots as inherited common CPU ownership. The new direct journal's1000 retention cells and head are explicitly owned and counted. Thus the enumerated-population stress is not a complete, physically symmetric SRAM/FF inventory across implementations. Native rollback/checkpoint implementation and all common CPU-owned copies must be mapped consistently before any whole-chip reliability or storage/PPA comparison. Deleting200 folds while adding3496 modeled bits is not a demonstrated total physical storage reduction.

IMPLEMENTED/TESTED FAILURE: both direct families fail on the directed high head-bit cases and FIFO control two-bit DUE. Twelve directed cases include six failed executions; this is an adverse-case count, not an estimated radiation failure probability. Pending active/read flips at tick1 were overwritten/no impact in those particular tests, not evidence of universal safety. A queue payload pair can hit an inactive cell and remain zero-effect; its presence is retained.

The11-bit pointer includes unimplemented encodings1130..2047. Its C++ error path is not a silicon safety response. The frozen direct FIFO has no graceful DUE cancellation protocol. Pending record fields are enumerated, while existing common BranchInfo/ownership and simulator absolute timing are excluded. These scope boundaries and missing total state transitions prevent calling the new prototype a hardware-qualified winner. Conditional source performance is still measured under its explicitly stated valid-metadata condition. No injector or golden data informs the production decisions.

Correctness repair history: the initial direct rollback transport qualified Base::restoreHistState and bypassed the new ring hook. Those initial CPU outputs are superseded, not pooled. R4 corrected and R5 producers passed exact gates. CPU equivalence means identical clean prediction function where timing/interface are held fixed; finite timing changes may change speculative streams, training and committed-branch prediction outcomes/performance without changing table algorithms. Architectural program results and stdout must still remain identical.
''')
write(F/'RESOURCE_CONTRACT.json',dict(status='IMPLEMENTED_CPU_MODEL_NOT_PHYSICAL_SIGNOFF',
 base_scope_bits=346,mandatory_legacy_methods=['P0','P_ED','P_ECC','P_TMR'],
 frozen_candidates=['BATCH_DIRECT','BATCH_STRAT16'],native_reference='NATIVE',
 storage=dict(table_and_bimodal=65024,active_raw=130,path=16,retention_raw=1000,head=11,pending_lookup=68,
              queue_depth=64,queue_payload=30,queue_code=7,queue_control=49,queue_total=2417,direct_total=68666),
 packet=dict(undo_bit=0,insertion_or_undo_count_bits=[1,10],direction_bits=[11,12],path_bits=[13,28],valid_bit=29),
 service=dict(append_latency=1,aggregated_undo_latency=2,configured_minimum_launch_gap=1,
              non_pipelined=True,max_source_jobs_in_service=1,effective_append_II=1,effective_undo_II=2,
              mixed_service_lower_bound='A+2U source cycles for A append/U aggregated undo packets; dependent jobs never overlap.',queue_slots=64,lookup_II=1,
              primary_extra_lookup_latency=0,sensitivity_extra_lookup_latency=[1,2],optimistic_undo_latency=1,
              operand_availability='BPU produces insertion/direction/PCbit or actual decoded undo count and oldest saved path at enqueue; current ring/head sampled at service completion.',
              publication='Raw/head/path visible only after clocked job completion; lookup waits for queued source operations. No function-first debt.',
              capacity='Actual BPU in-flight occupancy + queued demand<62 at lookup admission;2 slots reserved; retention<=1000. Capacity overflow is a protocol failure, not dropped work.',
              end='accepted=completed+cancelled+pending; pending at program exit is right-censored, not free completed work.',
              priorities='source service48, injector49, CPU50; same-tick events see completion before CPU use'),
 physical_interface=dict(source_bank='1130 independently selectable bits or equivalent parallel window with130-wide functional visibility; one insertion write/head-path transition per source service completion.',
              lookup='21 direct fold reductions (index+2tag per7 banks) from one consistent source version; shared raw read fanout and width-specific XOR networks; sparse16 selects fixed positions.',
              squash='BPU supplies up to1000 insertion undo span and final saved16-bit path as one packet. Need available decoded span/oldest-path ports and bounded reduction timing; no free serial scan claim.',
              same_cycle='Primary L0 assumes lookup read/XOR/table index fits the existing prediction stage. This is an explicit unverified clock/port condition, not zero physical delay.',
              queue='one enqueue port per serialized callback admission, one encoded read/service path, control/code update ports; queue codec timing and back-to-back callback port feasibility unmeasured.',
              stage_sensitivities='READ1/READ2 are measured CPU sensitivity, not synthesized pipeline realizations.'),
 protection_comparison=dict(k=64,parity='periodic detector+exclude/reset/relearn; even same-word bit pairs can escape',
              cadence_unit='role_history.hpp finish(bool committed) increments history_writes and saturating progress; next prediction boundary inspects when progress>=64. Includes actual modeled history transitions, not64CPUcycles or64retired conditional branches.',
              ECC='matched periodic prediction cadence but every source RMW must decode before re-encoding; extra decoder work is charged, not falsely equal total check activity',
              TMR='legacy same S* regression/main single-event comparison retained; correlated copies and voter/control scope remain limitations'),
 safety_gaps=['Invalid head encodings have host-model failure, no hardware fallback.','Journal SECDED DUE has no total graceful transition.','Common BranchInfo/CPU ownership/BTB/RAS are excluded, so this is not whole-CPU resilience.','Pending absolute latency/control deadlines are simulator scheduling objects, excluded from logical storage.'],
 no_claims=['No actual clock/ports/area/energy validated','No fabricated FIT or target cross section','No HDL/PDK/Cadence/SPICE/TCAD execution']))
nov=(F/'NOVELTY_EVIDENCE_MATRIX.md').read_text()+'''

TESTED RESULT (v5): exact direct folding and two sparse tap families were compared with recurrent/short32 controls, independent event RNGs, finite source service, and retained-task runs. The grouped pointer rewind is an implementation refinement over a measured serialization cost, not a claim that circular-buffer recovery is new. BADGR PDFpp1–3/§II and Fig2/3 already discuss circular-buffer/checkpoint alternatives. The potential contribution is the joint conditional damage-lifetime/rate/CPU service evidence and its explicit failure/latency bounds. No firstness or physical advantage has been established.

NEW DERIVATION: the rare-rate fixed-window expression keeps P(N>=2) as missing mass. It is not a demonstrated target-device expected completion time. R28 source coverage remains partial as recorded in RATE_ANCHORS_AUDIT.json. Source facts, implementation evidence and transfer assumptions remain separate.
'''
(F/'NOVELTY_EVIDENCE_MATRIX.md').write_text(nov)
print('Actual R5 state/resource contracts and bounded novelty evidence written')
