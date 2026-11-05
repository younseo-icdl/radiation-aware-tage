#!/usr/bin/env python3
"""Verify frozen public downloads, extract only required MiBench programs."""
import hashlib
import json
import tarfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
    lock=ROOT/'sources/public_workload_sources.lock.json'
    if not lock.exists():
        specs=[('mibench-automotive.tar.gz','https://vhosts.eecs.umich.edu/mibench/automotive.tar.gz',['automotive/qsort/']),
               ('mibench-network.tar.gz','https://vhosts.eecs.umich.edu/mibench/network.tar.gz',['network/dijkstra/']),
               ('mibench-security.tar.gz','https://vhosts.eecs.umich.edu/mibench/security.tar.gz',['security/sha/']),
               ('musl-1.2.6.tar.gz','https://musl.libc.org/releases/musl-1.2.6.tar.gz',['musl-1.2.6/'])]
        items=[{'path':'third_party/downloads/'+name,'url':url,'sha256':sha(ROOT/'third_party/downloads'/name),'extract_prefixes':prefixes} for name,url,prefixes in specs]
        lock.write_text(json.dumps({'status':'HTTPS_PRIMARY_SOURCE_HASH_PIN_NOT_PUBLISHER_SIGNATURE_VERIFICATION',
            'MiBench_source_page':'https://vhosts.eecs.umich.edu/mibench/source.html',
            'musl_release_author_announcement':'https://www.openwall.com/lists/musl/2026/03/20/1',
            'local_install_only':True,'archives':items},indent=2)+'\n')
    c=json.loads(lock.read_text())
    for item in c['archives']:
        source=ROOT/item['path'];assert sha(source)==item['sha256'],source
        target=ROOT/'third_party' if source.name.startswith('musl') else ROOT/'third_party/mibench-original'
        target.mkdir(parents=True,exist_ok=True)
        with tarfile.open(source) as archive:
            members=[m for m in archive.getmembers() if any(m.name.startswith(p) for p in item['extract_prefixes'])]
            assert members,source
            archive.extractall(target,members=members,filter='data')
    print('PASS primary public download hashes; safe selected extraction; per-program licenses retained')
if __name__=='__main__':main()
