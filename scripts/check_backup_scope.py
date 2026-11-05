#!/usr/bin/env python3
"""Check staged public-backup files without executing recovered research code."""
import pathlib
import re
import subprocess
import sys

root=pathlib.Path(subprocess.check_output(['git','rev-parse','--show-toplevel'],text=True).strip())
names=subprocess.check_output(['git','diff','--cached','--name-only','-z','--diff-filter=ACMR']).split(b'\0')
bad=[];count=0
for raw in names:
    if not raw:continue
    name=raw.decode();p=pathlib.PurePosixPath(name);count+=1
    data=subprocess.check_output(['git','show',':'+name],cwd=str(root))
    if p.suffix.lower() in ('.zip','.pdf','.rar','.bundle','.o','.opt','.so','.lib','.lef','.gds','.db'):
        bad.append((name,'BULK_OR_PRIVATE_INPUT'))
    if len(data)>10*1024*1024:bad.append((name,'OVER_10_MIB'))
    if re.search(rb'-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----|gh[pousr]_[A-Za-z0-9_]{25,}|github_pat_[A-Za-z0-9_]{25,}|AKIA[0-9A-Z]{16}',data):bad.append((name,'SECRET_MARKER'))
if bad:
    for name,reason in bad:print(reason,name)
    sys.exit(1)
print('PASS_PUBLIC_BACKUP_SCOPE',count,'staged files')
