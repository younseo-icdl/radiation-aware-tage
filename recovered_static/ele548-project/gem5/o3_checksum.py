"""Stage0 only: coupled X86 O3, plain TAGE, no radiation injection."""
import argparse
from pathlib import Path
import m5
from m5.objects import (System,SrcClockDomain,VoltageDomain,AddrRange,X86O3CPU,
    Cache,SystemXBar,MemCtrl,SEWorkload,Process,Root,BranchPredictor,TAGE,TAGEBase)
from gem5.components.memory.dram_interfaces.ddr3 import DDR3_1600_8x8
p=argparse.ArgumentParser();p.add_argument('--binary',required=True);p.add_argument('--n',default='20000');a=p.parse_args()
system=System();system.clk_domain=SrcClockDomain(clock='2GHz',voltage_domain=VoltageDomain());system.mem_mode='timing';system.mem_ranges=[AddrRange('256MiB')]
system.cpu=X86O3CPU(numThreads=1,decoupledFrontEnd=False)
# Table geometry comes from this locked release. CPU history is speculative;
# offline trace replay is explicitly non-speculative. Both use direction history.
system.cpu.branchPred=BranchPredictor(instShiftAmt=0,conditionalBranchPred=TAGE(tage=TAGEBase(takenOnlyHistory=False)),takenOnlyHistory=False,speculativeHistUpdate=True)
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
process=Process(cmd=[binary,a.n]);system.cpu.workload=process;system.cpu.createThreads()
root=Root(full_system=False,system=system);m5.core.seedRandom(548);m5.instantiate();event=m5.simulate(1000000000000)
print('Exit cause:',event.getCause(),'code:',event.getCode(),'tick:',m5.curTick())
if event.getCause()!='exiting with last active thread context' or event.getCode()!=0:raise RuntimeError('unexpected termination')
