"""Generate a local-only mapped history TB; no production saboteur/ports.
Q_buf force is a simulation Q-boundary perturbation through the sampling edge. This checks the
actual mapped cone/edge behavior with zero annotations, not physical SEU physics.
"""
from pathlib import Path
import re,json,hashlib
from budget import ROOT,BASE
r=BASE/'runtime/map_history_recurrent_A1/mapped.v';d=BASE/'runtime/map_history_direct_A1/mapped.v'
assert r.exists() and d.exists()
s=r.read_text();matches=re.findall(r'(\w+BWP30P140)\s+(\\fold_q_reg\[(\d+)\])\s*\(',s)
assert len(matches)==200 and {int(i) for _,_,i in matches}==set(range(200))
model=Path('/export/PDK/TSMC/28nm/Library/tcbn28hpcplusbwp30p140_190a/TSMCHOME/digital/Front_End/verilog/tcbn28hpcplusbwp30p140_110a/tcbn28hpcplusbwp30p140.v')
lib=model.read_text();paths={}
for cell,inst,i in matches:
 m=re.search(r'module\s+'+cell+r'\s*\(.*?endmodule',lib,re.S);assert m and 'tsmc_dff (Q_buf' in m[0]
 paths[int(i)]='dut_r.'+inst+' .Q_buf'
q='wire [199:0] observed_fold;\n'+'\n'.join('assign observed_fold[%d]=%s;'%(i,paths[i]) for i in range(200))
q+='\ntask automatic seed_mapped(input reg [199:0] v);begin\n'+'\n'.join('if(v[%d]) force %s=1\'b1; else force %s=1\'b0;'%(i,paths[i],paths[i]) for i in range(200))+'\nend endtask\ntask automatic release_seed;begin\n'+'\n'.join('release %s;'%paths[i] for i in range(200))+'\nend endtask\n'
# A separate namespace avoids loading two differently mapped helper definitions.
original_direct=d.read_text()
module_names=re.findall(r'^module\s+(\w+)',original_direct,re.M)
renamed=original_direct
for name in module_names:renamed=re.sub(r'\b'+re.escape(name)+r'\b','gls_direct_'+name,renamed)
reverse=renamed
for name in module_names:reverse=re.sub(r'\bgls_direct_'+re.escape(name)+r'\b',name,reverse)
assert reverse==original_direct
renamed_path=BASE/'tests/history_direct_mapped_namespaced.v';renamed_path.write_text(renamed)
s=(BASE/'tests/history_state_tb.sv').read_text().replace('module history_state_tb;','module history_mapped_tb;')
s=s.replace('history_state_direct dut_d','gls_direct_history_state_direct dut_d')
s=s.replace('dut_r.fold_q=seed_fold','seed_mapped(seed_fold)').replace('dut_r.fold_q','observed_fold')
s=s.replace('clk_i=1;#1;', 'clk_i=1;#1;if(seed_enable!=0)release_seed();#1;')
s=s.replace(' integer fd,n,rc',q+' integer fd,n,rc').replace('PASS_HISTORY_STATE_RTL_','PASS_HISTORY_MAPPED_QBOUNDARY_')
p=BASE/'tests/history_state_mapped_tb.sv';p.write_text(s)
(BASE/'tests/history_state_mapped_inputs.json').write_text(json.dumps(dict(model_path=str(model),model_sha256=hashlib.sha256(model.read_bytes()).hexdigest(),testbench_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),namespacing='Bijective module-identifiers-only rename for directGLS helper collisions; reverse transformation byteidentical',renamed_direct_sha256=hashlib.sha256(renamed_path.read_bytes()).hexdigest(),netlists={str(x.relative_to(ROOT)):hashlib.sha256(x.read_bytes()).hexdigest() for x in [r,d]},scope='Zero-annotation mapped function/edge/Q-boundary force-through-edge and release; not internalUDPstate SEU; no postrouteSDF/no physical crosssection qualification'),indent=2)+'\n')
print(str(p))
