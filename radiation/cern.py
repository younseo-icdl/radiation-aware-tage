#!/usr/bin/env python3
"""Strict parser for the published cluster grammar. Counts are coordinate counts, NOT event rates.
Parse an entire file before using its clusters. Suspected origin records are flagged, never silently deleted.
"""
import re
from pathlib import Path
HEADER=re.compile(r'cluster\s+(\d+)\s+with xmin\s+(-?\d+)\s+xmax\s+(-?\d+)\s+ymin\s+(-?\d+)\s+ymax\s+(-?\d+)\s*')
ANCHOR=re.compile(r'xadd\s+(-?\d+)\s+yadd\s+(-?\d+)(?:\s+(\d{1,2}:\d{1,2}:\d{1,2}))?\s*')
COUNT=re.compile(r'NUMBER OF EVENTS\s*=\s*(\d+)\s*')
XY=re.compile(r'(-?\d+)\s+(-?\d+)\s*')
INDEXED_XY=re.compile(r'(\d+)\s+(-?\d+)\s+(-?\d+)\s*')
def parse(text):
    out=[];current=None
    for ln,line in enumerate(text.splitlines(),1):
        s=line.strip()
        if not s:continue
        h=HEADER.fullmatch(s)
        if h:
            if current is not None:raise ValueError(f'Unclosed cluster before line {ln}')
            i,x0,x1,y0,y1=map(int,h.groups());current={'cluster_id':i,'header_line':ln,'bbox':[x0,x1,y0,y1],'coordinates':[]};continue
        if current is None:raise ValueError(f'Unexpected line {ln}: {s[:100]}')
        m=ANCHOR.fullmatch(s)
        if m:
            if 'anchor' in current:raise ValueError(f'Duplicate anchor at {ln}')
            current['anchor']=list(map(int,m.groups()[:2]))
            if m[3]:
                hh,mm,ss=map(int,m[3].split(':'))
                if not(0<=hh<24 and 0<=mm<60 and 0<=ss<60):raise ValueError(f'Invalid clock label at {ln}')
                current['source_clock_label']=m[3]
                current['coordinate_record_ids']=[]
            continue
        m=COUNT.fullmatch(s)
        if m:
            n=int(m[1]);xy=current['coordinates']; x0,x1,y0,y1=current['bbox']
            if n!=len(xy) or n<1:raise ValueError(f'Count mismatch at {ln}')
            if len(set(map(tuple,xy)))!=n:raise ValueError(f'Duplicate coordinates at {ln}')
            if any(not(x0<=x<=x1 and y0<=y<=y1) for x,y in xy):raise ValueError(f'Coordinate outside bbox at {ln}')
            if 'anchor' not in current or current['anchor'] not in xy:raise ValueError(f'Missing/invalid anchor at {ln}')
            current['raw_number_of_events_field']=n;current['multiplicity_from_unique_coordinates']=n
            current['suspected_origin_sentinel']=current['cluster_id']==0 and xy==[[0,0]]
            ax,ay=current['anchor'];current['offsets_from_anchor']=[[x-ax,y-ay] for x,y in xy]
            current['semantics']='one published cluster record; coordinate count is NOT independent particle count'
            out.append(current);current=None;continue
        m=INDEXED_XY.fullmatch(s)
        if m:
            if 'source_clock_label' not in current:raise ValueError(f'Indexed coordinate without clock-label anchor at {ln}')
            current['coordinate_record_ids'].append(int(m[1]))
            current['coordinates'].append(list(map(int,m.groups()[1:])));continue
        m=XY.fullmatch(s)
        if m:current['coordinates'].append(list(map(int,m.groups())));continue
        raise ValueError(f'Unsupported syntax line {ln}: {s[:120]}')
    if current is not None:raise ValueError('Truncated final cluster')
    if not out:raise ValueError('No clusters')
    ids=[r['cluster_id'] for r in out]
    if len(set(ids))!=len(ids):raise ValueError('Duplicate cluster IDs')
    return out
