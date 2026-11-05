"""Separate finite request/response pipeline producer; same O3/cache/memory settings."""
import argparse
from pathlib import Path
import m5
from m5.objects import (System,SrcClockDomain,VoltageDomain,AddrRange,X86O3CPU,
    Cache,SystemXBar,MemCtrl,SEWorkload,Process,Root,BranchPredictor,PipelineV7TAGE,PipelineV7TAGEBase)
from gem5.components.memory.dram_interfaces.ddr3 import DDR3_1600_8x8
p=argparse.ArgumentParser();p.add_argument('--binary',required=True);p.add_argument('--input')
p.add_argument('--scheme',choices=['P0','P_ED','P_ECC','P_TMR'],default='P0');p.add_argument('--schedule',default='')
p.add_argument('--check-cycles',type=int,default=0);p.add_argument('--repair-cycles',type=int,default=0)
p.add_argument('--inspection-interval',type=int,default=0)
p.add_argument('--role-policy',choices=['LEGACY','N1','H1','REV','STAGED'],default='LEGACY')
p.add_argument('--maintenance-cycles',type=int,default=0)
p.add_argument('--resource-mode',choices=['LEGACY','SHARED1','SPLIT2','SHARED2'],default='LEGACY')
p.add_argument('--decouple-shadow',action='store_true');p.add_argument('--rmw-latency',type=int,default=1);p.add_argument('--rmw-ii',type=int,default=1)
p.add_argument('--hot-queue-depth',type=int,default=64);p.add_argument('--shadow-queue-depth',type=int,default=8)
p.add_argument('--cost-remove',choices=['NONE','SPEC_SOURCE','COMMIT_SHADOW','FOLD_CHECK','RECOVERY','ALL'],default='NONE')
p.add_argument('--full-delta',action='store_true');p.add_argument('--reset-recovery',action='store_true')
p.add_argument('--promotion-group',type=int,choices=[0,1,2,3],default=3);p.add_argument('--sham-wait',action='store_true');p.add_argument('--audit',action='store_true');p.add_argument('--audit-limit',type=int,default=20000)
p.add_argument('--journal-merge-undo',action='store_true');p.add_argument('--undo-batch-latency',type=int,choices=[1,2],default=2);p.add_argument('--journal-service',action='store_true');p.add_argument('--representation',choices=['recurrent','direct','geometric','stratum','short32'],default='recurrent');p.add_argument('--tap-budget',type=int,default=8);p.add_argument('--lookup-latency',type=int,default=0);p.add_argument('--lookup-ii',type=int,default=0)
p.add_argument('--pipeline-mode',choices=['native','single','pipeline'],default='native');p.add_argument('--pipeline-latency',type=int,choices=[1,2],default=1);p.add_argument('--pipeline-ii',type=int,default=1)
p.add_argument('--read-log',action='store_true');p.add_argument('--max-ticks',type=int,default=20000000000000);a=p.parse_args()
out=Path(m5.options.outdir).resolve()
system=System();system.clk_domain=SrcClockDomain(clock='2GHz',voltage_domain=VoltageDomain());system.mem_mode='timing';system.mem_ranges=[AddrRange('256MiB')]
system.cpu=X86O3CPU(numThreads=1,decoupledFrontEnd=False)
base=PipelineV7TAGEBase(pipeline_mode=a.pipeline_mode,pipeline_latency=a.pipeline_latency,pipeline_ii=a.pipeline_ii,pipeline_log=str(out/'pipeline.csv'),journal_merge_undo=a.journal_merge_undo,undo_batch_latency=a.undo_batch_latency,journal_service=a.journal_service,representation=a.representation,tap_budget=a.tap_budget,lookup_latency=a.lookup_latency,lookup_ii=a.lookup_ii,minHist=2 if a.representation=='short32' else 5,maxHist=32 if a.representation=='short32' else 130,promotion_group=a.promotion_group,sham_wait=a.sham_wait,audit_file=str(out/'committed_audit.csv') if a.audit else '',audit_limit=a.audit_limit,resource_mode=a.resource_mode,decouple_shadow=a.decouple_shadow,rmw_latency=a.rmw_latency,rmw_ii=a.rmw_ii,hot_queue_depth=a.hot_queue_depth,shadow_queue_depth=a.shadow_queue_depth,cost_remove=a.cost_remove,full_delta=a.full_delta,reset_recovery=a.reset_recovery,role_policy=a.role_policy,maintenance_cycles=a.maintenance_cycles,inspection_interval=a.inspection_interval,takenOnlyHistory=False,scheme=a.scheme,cycle_ticks=500,check_cycles=a.check_cycles,repair_cycles=a.repair_cycles,
    schedule_file=str(Path(a.schedule).resolve()) if a.schedule else '',event_log=str(out/'events.csv'),summary_file=str(out/'seu.json'),
    manifest_file=str(out/'logical_manifest.json'),read_log=str(out/'prediction_reads.csv') if a.read_log else '')
system.cpu.branchPred=BranchPredictor(instShiftAmt=0,conditionalBranchPred=PipelineV7TAGE(tage=base),takenOnlyHistory=False,speculativeHistUpdate=True)
system.membus=SystemXBar()
class L1(Cache):
    assoc=2;tag_latency=2;data_latency=2;response_latency=2;mshrs=4;tgts_per_mshr=20
system.cpu.icache=L1(size='32KiB');system.cpu.dcache=L1(size='32KiB')
system.cpu.icache_port=system.cpu.icache.cpu_side;system.cpu.dcache_port=system.cpu.dcache.cpu_side
system.cpu.icache.mem_side=system.membus.cpu_side_ports;system.cpu.dcache.mem_side=system.membus.cpu_side_ports
system.cpu.mmu.connectWalkerPorts(system.membus.cpu_side_ports,system.membus.cpu_side_ports)
system.cpu.createInterruptController()
system.cpu.interrupts[0].pio=system.membus.mem_side_ports
system.cpu.interrupts[0].int_requestor=system.membus.cpu_side_ports
system.cpu.interrupts[0].int_responder=system.membus.mem_side_ports
system.mem_ctrl=MemCtrl(dram=DDR3_1600_8x8(range=system.mem_ranges[0]))
system.mem_ctrl.port=system.membus.mem_side_ports;system.system_port=system.membus.cpu_side_ports
binary=str(Path(a.binary).resolve());system.workload=SEWorkload.init_compatible(binary)
args=[binary]+([str(Path(a.input).resolve())] if a.input else [])
process=Process(cmd=args,output=str(out/'program.stdout'),errout=str(out/'program.stderr'))
system.cpu.workload=process;system.cpu.createThreads()
root=Root(full_system=False,system=system);m5.core.seedRandom(548);m5.instantiate();event=m5.simulate(a.max_ticks)
base.dumpSeu();m5.stats.dump()
print('Exit cause:',event.getCause(),'code:',event.getCode(),'tick:',m5.curTick())
if event.getCause()!='exiting with last active thread context' or event.getCode()!=0:raise RuntimeError('unexpected termination')
