"""Whole augmented storage mapping gate. No simulator execution."""
import sys,pathlib
sys.dont_write_bytecode=True
import campaign as p
r=p.r;B=p.B
init=r.load(B/'reports/INITIALIZATION_B1.json');maps={z['method']:p.semantic_map(r.load(z['manifest']['path'])) for z in init['rows']};union=set().union(*[set(x) for x in maps.values()])
assert maps['P_ED_FREQUENT']==maps['P_ED_PERIODIC_N1']
for k in ('raw_ring:b0','raw_ring:b1129','path:b15','original_logical_tables_in_pinned_Site_order:b65023'):assert all(k in x for x in maps.values())
assert all('fold:b199' in mp for method,mp in maps.items() if method!='EXACT_DIRECT') and 'fold:b199' not in maps['EXACT_DIRECT']
assert 'protect_stage_payload:w0:b0' not in maps['EXACT_DIRECT'] and 'protect_stage_payload:w21:b129' in maps['EXACT_DIRECT'] and 'protect_stage_payload:w22:b15' in maps['EXACT_DIRECT']
assert not any(':SECDED:' in k for k in maps['P_ED_FREQUENT']) and not any(':parity:' in k for k in maps['P_ECC'])
assert all(any(k.startswith('protect_replica1:') for k in maps[z])==(z=='P_TMR') for z in maps)
r.put(B/'reports/SEMANTIC_MAPPING_GATE_B1.json',{'status':'PASS_ACTUAL_AUGMENTED_LOGICAL_BIT_BIJECTION_NOT_FAULT_OUTCOMES','populations':{k:len(v) for k,v in maps.items()},'union':len(union),'Direct_absent_fold':True,'parity_ECC_code_bit_semantics_separate':True,'actual_native_input_payloads_checked':True,'new_CPU':0});print('MAP_GATE_PASS',len(union))
