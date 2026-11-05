#!/usr/bin/env python3
"""Verify this continuation ZIP CRC and every included file SHA; no simulation."""
import argparse,hashlib,json,zipfile
from pathlib import PurePosixPath
def main():
 p=argparse.ArgumentParser();p.add_argument('zip');a=p.parse_args()
 with zipfile.ZipFile(a.zip) as z:
  assert z.testzip() is None,'CRC_FAILURE'
  names=z.namelist();assert len(names)==len(set(names))
  assert all(not PurePosixPath(s).is_absolute() and '..' not in PurePosixPath(s).parts for s in names)
  manifest=json.loads(z.read('PACKAGE_CONTENTS.json'))
  assert manifest['status']=='PLAN_AND_PRIOR_EVIDENCE_NOT_NEW_V18_RESULTS'
  expected={x['member'] for x in manifest['files']}|{'PACKAGE_CONTENTS.json'};assert set(names)==expected
  for x in manifest['files']:
   data=z.read(x['member']);assert len(data)==x['bytes'] and hashlib.sha256(data).hexdigest()==x['sha256'],x['member']
  print(json.dumps({'status':'PASS_ZIP_CRC_AND_ALL_FILE_SHA','files_verified':len(manifest['files']),'new_v18_simulations':0,'portable_full_toolchain':False},indent=2))
if __name__=='__main__':main()
