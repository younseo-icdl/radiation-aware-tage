"""Single-core O3 execution with native or finite source/protection TAGE."""
import argparse
import atexit
import json
from pathlib import Path
import sys
import m5
from m5.objects import (System, SrcClockDomain, VoltageDomain, AddrRange,
    X86O3CPU, Cache, SystemXBar, MemCtrl, SEWorkload, Process, Root,
    BranchPredictor, TAGE, TAGEBase, FiniteTAGE, FiniteTAGEBase)
from gem5.components.memory.dram_interfaces.ddr3 import DDR3_1600_8x8


def options():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', type=Path, required=True)
    parser.add_argument('--input', type=Path)
    parser.add_argument('--model', choices=['native', 'finite'], default='finite')
    parser.add_argument('--representation', choices=['recurrent', 'direct'], default='recurrent')
    parser.add_argument('--scheme', choices=['P0', 'P_ED', 'P_ECC', 'P_TMR'], default='P0')
    parser.add_argument('--inspection-interval', type=int, choices=[0, 64], default=0)
    parser.add_argument('--schedule', default='')
    parser.add_argument('--query-latency', type=int, choices=[1, 2], default=1)
    parser.add_argument('--update-latency', type=int, choices=[1, 2], default=1)
    parser.add_argument('--early-unconditional', action='store_true')
    parser.add_argument('--max-ticks', type=int, default=2000000000000)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--initialize-only', action='store_true')
    mode.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    if args.model == 'native' and (args.schedule or args.scheme != 'P0' or
            args.representation != 'recurrent' or args.inspection_interval or args.early_unconditional):
        parser.error('native is a clean reference; protection and injection require --model finite')
    if args.representation == 'direct' and args.scheme != 'P0':
        parser.error('exact direct is an additional unprotected representation')
    if args.representation == 'direct' and args.update_latency != 1:
        parser.error('the direct source update path is fixed at L=1; use --update-latency 1')
    if args.inspection_interval and args.scheme != 'P_ED':
        parser.error('periodic inspection requires P_ED')
    if not args.binary.is_file():
        parser.error('binary does not exist')
    if args.input and not args.input.is_file():
        parser.error('input does not exist')
    return args


def create_system(args, output):
    system = System()
    system.clk_domain = SrcClockDomain(clock='2GHz', voltage_domain=VoltageDomain())
    system.mem_mode = 'timing'
    system.mem_ranges = [AddrRange('256MiB')]
    system.cpu = X86O3CPU(numThreads=1, decoupledFrontEnd=False)
    geometry = dict(minHist=5, maxHist=130, takenOnlyHistory=False, speculativeHistUpdate=True)
    if args.model == 'finite':
        base = FiniteTAGEBase(representation=args.representation,
            pipeline_latency=args.query_latency, pipeline_ii=1,
            rmw_latency=args.update_latency, rmw_ii=1,
            early_unconditional=args.early_unconditional,
            scheme=args.scheme, inspection_interval=args.inspection_interval,
            cycle_ticks=500, schedule_file=args.schedule,
            event_log=str(output/'events.csv'), summary_file=str(output/'seu.json'),
            manifest_file=str(output/'logical_manifest.json'), **geometry)
        predictor = FiniteTAGE(tage=base)
    else:
        base = None
        predictor = TAGE(tage=TAGEBase(**geometry))
    system.cpu.branchPred = BranchPredictor(instShiftAmt=0,
        conditionalBranchPred=predictor, takenOnlyHistory=False, speculativeHistUpdate=True)
    system.membus = SystemXBar()

    class L1(Cache):
        assoc = 2
        tag_latency = data_latency = response_latency = 2
        mshrs = 4
        tgts_per_mshr = 20

    system.cpu.icache = L1(size='32KiB')
    system.cpu.dcache = L1(size='32KiB')
    system.cpu.icache_port = system.cpu.icache.cpu_side
    system.cpu.dcache_port = system.cpu.dcache.cpu_side
    system.cpu.icache.mem_side = system.membus.cpu_side_ports
    system.cpu.dcache.mem_side = system.membus.cpu_side_ports
    system.cpu.mmu.connectWalkerPorts(system.membus.cpu_side_ports, system.membus.cpu_side_ports)
    system.cpu.createInterruptController()
    system.cpu.interrupts[0].pio = system.membus.mem_side_ports
    system.cpu.interrupts[0].int_requestor = system.membus.cpu_side_ports
    system.cpu.interrupts[0].int_responder = system.membus.mem_side_ports
    system.mem_ctrl = MemCtrl(dram=DDR3_1600_8x8(range=system.mem_ranges[0]))
    system.mem_ctrl.port = system.membus.mem_side_ports
    system.system_port = system.membus.cpu_side_ports
    binary = str(args.binary.resolve())
    system.workload = SEWorkload.init_compatible(binary)
    command = [binary] + ([str(args.input.resolve())] if args.input else [])
    process = Process(cmd=command, output=str(output/'program.stdout'), errout=str(output/'program.stderr'))
    system.cpu.workload = process
    system.cpu.createThreads()
    return system, base


def main():
    args = options()
    output = Path(m5.options.outdir).resolve()
    system, base = create_system(args, output)
    root = Root(full_system=False, system=system)
    m5.core.seedRandom(548)
    m5.instantiate()
    if args.initialize_only:
        assert m5.curTick() == 0
        if base:
            base.dumpSeu()
        print('PASS_TICK0_NO_CPU')
        return root
    event = m5.simulate(args.max_ticks)
    if base:
        base.dumpSeu()  # Freeze exposure at architectural program exit.
    m5.stats.dump()
    print('Exit cause:', event.getCause(), 'code:', event.getCode(), 'tick:', m5.curTick())
    if event.getCause() != 'exiting with last active thread context' or event.getCode() != 0:
        raise RuntimeError('unexpected program termination')
    if base:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from observer import observe
        # Keep CPU performance at program exit while checking real helper drain.
        initial = json.loads((output/'seu.json').read_text())
        (output/'seu.program_exit.json').write_text(json.dumps(initial, indent=2)+'\n')
        atexit.unregister(m5.stats.dump)

        def advance():
            result = m5.simulate(500)
            if result.getCause() != 'simulate() limit reached':
                raise RuntimeError('unexpected post-exit helper event: '+result.getCause())

        def sample():
            base.dumpSeu()
            return json.loads((output/'seu.json').read_text())

        trace = observe(initial, advance, sample)
        (output/'termination.json').write_text(json.dumps({
            'status': 'PASS', 'program_exit_tick': initial['tick'],
            'observation_end_tick': trace[-1]['tick'],
            'source_cycles_observed': len(trace)-1, 'first_exit_stats_preserved': True}, indent=2)+'\n')
    return root


if __name__ == '__m5_main__':
    root = main()
