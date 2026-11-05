"""Parse actual first worst-slack path per reported class. No missing=>zero."""
from pathlib import Path
import re,json,csv
from budget import BASE
cases=[('p0','protection_words_p0'),('parity_frequent','protection_words_parity_frequent'),('parity_incremental','protection_words_parity_incremental'),('secded','protection_words_secded'),('tmr','protection_words_tmr'),('history_recurrent','history_state_recurrent'),('history_direct','history_state_direct')]
rows=[]
for short,top in cases:
 runs=[x for x in (BASE/'runtime').glob('map_'+short+'_A*') if (x/'mapped.v').exists() and ('\nV10_COMPONENT_MAP_PASS '+top+' STATE ') in (x/'console.log').read_text()]
 if not runs:continue
 assert len(runs)==1,(top,runs)
 r=runs[0]
 if not (r/'mapped.v').exists():continue
 log=(r/'console.log').read_text();assert '\nV10_COMPONENT_MAP_PASS '+top+' STATE ' in log and 'Error   :' not in log
 s=(r/'area_mapped.rpt').read_text();a=re.search(r'^'+re.escape(top)+r'\s+NA\s+(\d+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)',s,re.M);assert a,top
 states=int(re.search(r'\nV10_FINAL_STATE_COUNT '+re.escape(top)+r' (\d+) EXPECTED',log)[1])
 row=dict(top=top,accepted_run=r.name,storage_bits=states,cell_count=int(a[1]),mapped_cell_area_um2=float(a[2]),estimated_net_area_tool_units=float(a[3]),routed=False,energy=None)
 row['timing_classes']={}
 for c in ['mapped','in2out','in2reg','reg2reg','reg2out']:
  p=r/('timing_'+c+'.rpt')
  if not p.exists():row['timing_classes'][c]={'status':'NO_REGISTERS_NOT_APPLICABLE'};continue
  t=p.read_text();first=t.split('\nPath 2:')[0]
  start=re.search(r'Startpoint:\s*(.*?)\n',first);end=re.search(r'Endpoint:\s*(.*?)\n',first)
  data=re.search(r'Data Path:-\s*(-?\d+)',first);slack=re.search(r'Slack:=\s*(-?\d+)',first)
  row['timing_classes'][c]=dict(status='KNOWN_FIRST_WORST_SLACK_PATH',data_path_ps=int(data[1]),slack_ps=int(slack[1]),startpoint=start[1],endpoint=end[1]) if all([start,end,data,slack]) else dict(status='NO_CONSTRAINED_PATH_REPORTED',report=str(p))
 rows.append(row)
report=dict(status='ALL7_ACTUAL_COMPONENT_MAPS' if len(rows)==7 else 'PARTIAL_COMPONENT_MAPS',rows=rows,limits=['Mapped pre-placementglobalinterconnect estimate; not routedarea/timing','Firstworstslackpath withinclass, not a matchedsource/endpoint contrast','Protectionprimitives omit23wordfullrecovery/refill/drain/epoch/ports/source-delta generation','Externalretainedsource/read/align/ownership remainsUNKNOWN; no fullstage or totalcost ranking','Energynotmeasured'])
(BASE/'reports/COMPONENT_RESULTS.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
