"""V15 query/update split + optional early unconditional checkpoint model.
--initialize-only performs NO simulate call, CPU instructions or clock events.
--execute consumes a CPU trial and may only be launched by the approved runner.
The existing pipeline_latency parameter now declares SOURCE QUERY L; manifest
records the separate provider extra1cycle. It is not the old total latency.
"""
import argparse,json
from pathlib import Path
import m5
from m5.objects import (System,SrcClockDomain,VoltageDomain,AddrRange,X86O3CPU,
    Cache,SystemXBar,MemCtrl,SEWorkload,Process,Root,BranchPredictor,PipelineV9R2TAGE,PipelineV9R2TAGEBase)
from gem5.components.memory.dram_interfaces.ddr3 import DDR3_1600_8x8
p=argparse.ArgumentParser();p.add_argument('--binary',required=True);p.add_argument('--input')
p.add_argument('--representation',choices=['recurrent','direct'],required=True)
p.add_argument('--scheme',choices=['P0','P_ED','P_ECC','P_TMR'],default='P0')
p.add_argument('--inspection-interval',type=int,choices=[0,64],default=0)
p.add_argument('--schedule',default='')
p.add_argument('--query-latency',type=int,choices=[1,2],required=True)
p.add_argument('--update-latency',type=int,choices=[1,2],required=True)
p.add_argument('--early-unconditional',action='store_true')
p.add_argument('--max-ticks',type=int,default=2000000000000)
mode=p.add_mutually_exclusive_group(required=True);mode.add_argument('--initialize-only',action='store_true');mode.add_argument('--execute',action='store_true')
a=p.parse_args();out=Path(m5.options.outdir).resolve()
system=System();system.clk_domain=SrcClockDomain(clock='2GHz',voltage_domain=VoltageDomain());system.mem_mode='timing';system.mem_ranges=[AddrRange('256MiB')]
system.cpu=X86O3CPU(numThreads=1,decoupledFrontEnd=False)
base=PipelineV9R2TAGEBase(representation=a.representation,pipeline_mode='pipeline',pipeline_latency=a.query_latency,pipeline_ii=1,rmw_latency=a.update_latency,rmw_ii=1,lookup_latency=0,lookup_ii=0,
    minHist=5,maxHist=130,takenOnlyHistory=False,speculativeHistUpdate=True,
    role_policy=('V18_EARLY_UNCONDITIONAL' if a.early_unconditional else 'LEGACY'),resource_mode='LEGACY',scheme=a.scheme,inspection_interval=a.inspection_interval,cycle_ticks=500,
    schedule_file=a.schedule,event_log=str(out/'events.csv'),summary_file=str(out/'seu.json'),manifest_file=str(out/'logical_manifest.json'))
system.cpu.branchPred=BranchPredictor(instShiftAmt=0,conditionalBranchPred=PipelineV9R2TAGE(tage=base),takenOnlyHistory=False,speculativeHistUpdate=True)
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
root=Root(full_system=False,system=system);m5.core.seedRandom(548);m5.instantiate()
if a.initialize_only:
    assert m5.curTick()==0
    base.dumpSeu()
    (out/'INITIALIZATION_ONLY.json').write_text(json.dumps({'status':'PASS_TICK0_NO_CPU','tick':0,'simulate_called':False,'CPU_trial':False},indent=2)+'\n')
    print('PASS_TICK0_NO_CPU')
else:
    import atexit,sys
    sys.path.insert(0,str(Path(__file__).resolve().parent))
    from observer_v18 import observe
    event=m5.simulate(a.max_ticks)
    base.dumpSeu();m5.stats.dump()
    print('Exit cause:',event.getCause(),'code:',event.getCode(),'tick:',m5.curTick())
    if event.getCause()!='exiting with last active thread context' or event.getCode()!=0:raise RuntimeError('unexpected termination')
    initial=json.loads((out/'seu.json').read_text())
    (out/'seu.program_exit.json').write_text(json.dumps(initial,indent=2)+'\n')
    atexit.unregister(m5.stats.dump)
    def advance():
        result=m5.simulate(500)
        if result.getCause()!='simulate() limit reached':raise RuntimeError('unexpected post-exit helper event: '+result.getCause())
    def sample():
        base.dumpSeu();return json.loads((out/'seu.json').read_text())
    trace=observe(initial,advance,sample)
    (out/'termination_trace.json').write_text(json.dumps({'status':'PASS_ACTUAL_HELPER_COMPLETION_FROZEN_FAULT_CENSOR','program_exit_tick':initial['tick'],'observation_end_tick':trace[-1]['tick'],'source_cycles_observed':len(trace)-1,'first_exit_stats_preserved':True,'trace':trace},indent=2)+'\n')
