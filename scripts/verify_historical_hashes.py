#!/usr/bin/env python3
"""Compare recovered source bytes with SHA references actually printed in logs."""
import argparse
import csv
import hashlib
import json
import pathlib
import re

from recover_from_local_records import output_text, write_json


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--session',type=pathlib.Path,required=True);ap.add_argument('--repo',type=pathlib.Path,required=True);ap.add_argument('--max-line',type=int,required=True);a=ap.parse_args()
    refs={}
    pattern=re.compile(r'''["']path["']\s*:\s*["'](/home/youns/workspace/ele548-project[^"'\n]+)["']\s*,\s*["']sha256["']\s*:\s*["']([0-9a-f]{64})["']''')
    def inspect(value,line,depth=0):
        if depth>6:return
        if isinstance(value,dict):
            p=value.get('path');s=value.get('sha256')
            if isinstance(p,str) and p.startswith('/home/youns/workspace/ele548-project') and isinstance(s,str) and re.match(r'^[0-9a-f]{64}$',s):refs[p]=(s,line)
            for v in value.values():inspect(v,line,depth+1)
        elif isinstance(value,list):
            for v in value:inspect(v,line,depth+1)
        elif isinstance(value,str):
            for p,s in pattern.findall(value):refs[p]=(s,line)
            try:parsed=json.loads(value)
            except (ValueError,TypeError):return
            inspect(parsed,line,depth+1)
    with a.session.open() as stream:
        for line_no,raw in enumerate(stream,1):
            if line_no>a.max_line:break
            x=json.loads(raw)
            if x.get('type')=='response_item' and x.get('payload',{}).get('type') in ('custom_tool_call_output','function_call_output'):
                inspect(x['payload'].get('output'),line_no)
    rows=[]
    for original,(expected,line) in sorted(refs.items()):
        rel=original.split('/workspace/',1)[1]
        for variant in ('recovered_static','recovered'):
            p=a.repo/variant/rel
            if p.is_file():
                actual=hashlib.sha256(p.read_bytes()).hexdigest()
                rows.append({'path':p.relative_to(a.repo).as_posix(),'historical_path':original,'expected_SHA256':expected,'observed_source_record':line,'recovered_SHA256':actual,'status':'MATCH_PRINTED_HISTORICAL_SHA' if actual==expected else 'DIFFERENT_BYTES_NOT_QUALIFIED_AS_FINAL'})
    out=a.repo/'recovery/HISTORICAL_HASH_COMPARISON.csv'
    with out.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['path','historical_path','expected_SHA256','observed_source_record','recovered_SHA256','status']);w.writeheader();w.writerows(rows)
    summary={'historical_path_refs_found':len(refs),'candidate_comparisons':len(rows),'matches':sum(x['status'].startswith('MATCH') for x in rows),'mismatches':sum(not x['status'].startswith('MATCH') for x in rows),'source_refs':{p:{'sha256':s,'record_line':n} for p,(s,n) in refs.items() if '/producer_source/B4/' in p},'not_full_source_lock_recovery':True,'no_simulations':True}
    write_json(a.repo/'recovery/PRINTED_FILE_HASH_REFERENCES.json',{p:{'sha256':s,'record_line':n} for p,(s,n) in sorted(refs.items())})
    write_json(a.repo/'recovery/HISTORICAL_HASH_STATUS.json',summary)
    print(json.dumps({k:summary[k] for k in ('historical_path_refs_found','candidate_comparisons','matches','mismatches')},indent=2))
    for row in rows:
        if '/producer_source/B4/' in row['path']:print(row['status'],row['path'])


if __name__=='__main__':main()
