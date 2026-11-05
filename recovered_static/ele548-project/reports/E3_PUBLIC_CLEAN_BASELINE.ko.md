# E3 무오류 CPU 기준 실행 — 2026-10-12

공식 MiBench source/input의 실제 static ELF 3개를 native와 pinned gem5 O3에서 실행했다. 모두 exit 0, stdout hash 일치, stderr 비어 있음. Native 정답은 독립 Python sorting/shortest-path/hashlib로 검증했다. Source는 [MiBench 공식 배포](https://vhosts.eecs.umich.edu/mibench/source.html), library는 user-local musl 1.2.6이며 source archive/hash/license/port 내용은 `sources/public_workload_sources.lock.json`과 `E3_PUBLIC_WORKLOADS.json`에 있다.

| Program / input | Committed instructions | CPU cycles | IPC | Conditional committed MPKI |
|---|---:|---:|---:|---:|
| qsort_small / 공식 10000 words | 25377476 | 33796610 | 0.750888 | 6.948642 |
| dijkstra_small / 공식 100-node matrix, 20 paths | 47146344 | 40997454 | 1.149982 | 1.243299 |
| SHA-1 / 공식 input_small.asc | 11608102 | 5895370 | 1.969020 | 0.032305 |

표의 instruction 값은 raw `commitStats0.numInsts`에서 확인하며 `simInsts`와 일치한다. IPC는 committed instructions/cycles이고, MPKI numerator는 committed `mispredicted_0::DirectCond + IndirectCond`다. Speculative corrected/condIncorrect counter를 committed MPKI로 사용하지 않는다. 정확한 원 수치·hash·commands와 fetch stall counters는 `E3_PUBLIC_CLEAN_BASELINE.json`, `gem5_o3_public/{program}/stats.txt`에 있다.

ROI는 **cold whole process startup→exit**다. Libc/input parsing/output을 포함하며 compute-only/SPEC score 또는 stationarily warmed predictor 결과로 표시하지 않는다. Qsort/Dijkstra는 원래 algorithm/source를 유지했다(Dijkstra는 missing stdlib declarations를 compilation에서 공급). SHA는 LP64에서 32-bit word/format을 명시한 derived copy와 원래 documented SHA-1/endian option을 사용했다. Original public source는 보존했다.

CPU는 X86O3 single core/thread, coupled frontend, plain TAGE, direction history와 speculative history, 2GHz, classic L1 I/D 32KiB/2-way, DDR3_1600_8x8/256MiB range다. Actual config를 pinned predictor geometry와 검증했다. Source pin v25.1.0.1 / `c8222cc67a399bfc01e8658dd14b30d5bfd634f9`, source checkout dirty=false. Optimized binary/hash는 software lock에 있다.

Debug에서 Qsort/Dijkstra는 900s budget timeout이었다. SHA는 debug에서도 정답/exit 0이고 optimized와 cycles/instructions/MPKI가 일치했다. Timeout 결과를 success/masked로 세지 않았다. Debug pilot 원 logs/stats/report는 `e3_setup/debug_runtime_pilot`에 보존했다. 최초 port-role configuration failure는 `e3_setup/attempt1_port_role`에 보존하고 checksum config와 동일 wiring으로 수정했다. Optimized/debug checksum의 정답과 six simulated counters도 동일하다(`E3_OPT_DEBUG_EQUIVALENCE.json`). Optimized three-program baseline wall 197.06s이며 host time은 CPU cycles와 구분한다.

Warnings는 optional pydot, DRAM device capacity/range, OSABI Linux assumption, legacy stats, disabled GDB listeners, redirected stdout의 terminal ioctl ENOTTY다. Native 정답/exit를 각각 확인했으며 unsupported terminal ioctl의 ENOTTY는 stdout이 terminal이 아닌 native 조건과 맞는다. 그 외 unsupported syscall/assertion/timeout은 성공 처리하지 않는다.

## 다음 비교

**이번 결과는 P0 clean baseline이며 CPU fault injection/보호 성능 결과가 아니다.** 다음에 logical-bit SimTick events, same-tick ordering, speculation/squash/rollback, 동일 S*의 세 controller를 gem5에 연결해 검증한다. 그 뒤 P0/ED/ECC/TMR 각각 clean/faulty를 비교한다. Δcycles, IPC loss, committed MPKI, frontend hold/repair stalls와 failure를 기록한다. HW1 C++ ΔMPKI를 cycles/IPC로 임의 환산하지 않는다.

Cadence 없이도 가정한 check/repair latency sensitivity는 software에서 수행할 수 있다. 실제 predictor response/hold/repair 경로에 연결하며 실제 RTL latency/PPA로 표시하지 않는다. 실제 latency/PPA와 최종 ranking은 E4 이후다. CERN footprint와 Flying Laptop detection-time sensitivity도 남아 있으며 source/model gate를 통과해야 한다.
