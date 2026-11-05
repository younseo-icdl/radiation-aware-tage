#!/usr/bin/env python3
"""Compile upstream algorithm unchanged; substitute only simulator statistics constructor.
Generated file retains original copyright. Never edit the pinned gem5 checkout.
"""
from pathlib import Path
import hashlib,json,subprocess
root=Path(__file__).resolve().parents[1]
p=root/'third_party/gem5/src/cpu/pred/tage_base.cc'
s=p.read_text();start=s.index('TAGEBase::TAGEBaseStats::TAGEBaseStats(')
brace=s.index('{',start);end=s.index('\n}',brace)+2
replacement='''TAGEBase::TAGEBaseStats::TAGEBaseStats(statistics::Group *parent, unsigned nHistoryTables)
    : statistics::Group(parent) {
    longestMatchProvider.init(nHistoryTables + 1);
    altMatchProvider.init(nHistoryTables + 1);
}'''
out=s[:start]+replacement+s[end:]
d=root/'build/standalone';d.mkdir(parents=True,exist_ok=True)
(d/'tage_base.cc').write_text(out)
record={'upstream_commit':subprocess.check_output(['git','-C',str(root/'third_party/gem5'),'rev-parse','HEAD'],text=True).strip(),'upstream_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'generated_sha256':hashlib.sha256(out.encode()).hexdigest(),'only_substitution':'TAGEBaseStats constructor; statistics/logging/SimObject/params are standalone shims; no predictor algorithm changes'}
(root/'reports/tage_source_binding.json').write_text(json.dumps(record,indent=2)+'\n')
