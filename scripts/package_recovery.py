#!/usr/bin/env python3
"""Create a private download bundle and offline Git backup; no experiments."""
import argparse
import hashlib
import json
import pathlib
import subprocess
import zipfile


def digest(data):return hashlib.sha256(data).hexdigest()


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--private',type=pathlib.Path,required=True);ap.add_argument('--zip',type=pathlib.Path,required=True);a=ap.parse_args()
    root=pathlib.Path(__file__).resolve().parents[1]
    def git(*args):return subprocess.check_output(['git',*args],cwd=str(root),universal_newlines=True).strip()
    assert not git('status','--porcelain'),'Commit and push the recovery snapshot first.'
    head=git('rev-parse','HEAD');remote=git('ls-remote','origin','refs/heads/main').split()[0];assert head==remote
    archive=a.private/'repository_source';archive.mkdir(exist_ok=False)
    names=subprocess.check_output(['git','ls-files','-z'],cwd=str(root)).split(b'\0')
    for raw in names:
        if not raw:continue
        name=raw.decode();target=archive/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((root/name).read_bytes())
    saved=a.private/'repository_backup';saved.mkdir(exist_ok=False)
    bundle=saved/'radiation-aware-tage_recovery.bundle'
    subprocess.check_call(['git','bundle','create',str(bundle),'--all'],cwd=str(root))
    subprocess.check_call(['git','bundle','verify',str(bundle)],cwd=str(root),stdout=subprocess.DEVNULL)
    receipt={'repository':'https://github.com/younseo-icdl/radiation-aware-tage','main_commit':head,'remote_main_verified_equal':True,'offline_bundle':bundle.relative_to(a.private).as_posix(),'bundle_sha256':digest(bundle.read_bytes()),'tag':'recovery-20261105','original_deleted_Git_history_recovered':False,'old_experiments_executed':0}
    (a.private/'GITHUB_BACKUP_RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n')
    status=json.loads((root/'recovery/CURRENT_STATUS.json').read_text())
    (a.private/'CURRENT_RECOVERY_STATUS.json').write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n')
    (a.private/'README_FIRST.ko.md').write_text('''# ELE548 복구 A2 — 2026-11-05

원래 첨부자료37개, 기록된 patch 요청506개, 회수한 소스 후보, 최신 B4용 source 모음, GitHub에 push한 코드·중요 문서와 그 새 Git history bundle을 보존합니다.

repository_source/final_b4/부터 확인하세요. 정확한 상태는 CURRENT_RECOVERY_STATUS.json과 repository_source/recovery/에 있습니다. 원본 전체실험 ZIP/ELF/510owner 원시행/기존Git history를 되찾은 것은 아닙니다. 기존 실험을 재실행하지 않았습니다. 코드 후보를 자동으로 실행하지 않습니다.

B4 O3 cpu.cc, 실행 config, observer의3개 파일은 과거 기록된 최종 SHA와 일치합니다. 나머지는 회수한 source text 후보이며 전체빌드 또는 전체source lock의 재검증이 아닙니다. v9 predictor/tage_adapter.hpp 동일성은 아직 확인되지 않았고 이전모델 reference를 별도로 보존했습니다.

원래논문/수업자료/HW1이 들어 있는 original_attachments/는 private 인계 자료입니다. 이 전체ZIP을 공개GitHub에 그대로 올리지 마세요. 공개저장소에는 research code 후보와작성문서/집계만 별도로보존했습니다.

repository_backup/*.bundle은 새 복구저장소의 Git history입니다. 네트워크가 없어도 git clone <bundle경로> radiation-aware-tage로 풀 수 있습니다. 원래 삭제된 저장소의 history를 복구한 것은 아닙니다. GITHUB_BACKUP_RECEIPT.json은 실제 원격commit 확인 결과입니다.
''')
    paths=[p for p in a.private.rglob('*') if p.is_file()]
    manifest={p.relative_to(a.private).as_posix():{'sha256':digest(p.read_bytes()),'bytes':p.stat().st_size} for p in paths}
    assert not a.zip.exists()
    with zipfile.ZipFile(a.zip,'x',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(paths):z.write(p,p.relative_to(a.private).as_posix())
        z.writestr('SHA256_MANIFEST.json',json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    with zipfile.ZipFile(a.zip) as z:
        assert z.testzip() is None
        assert len(z.namelist())==len(set(z.namelist()))==len(manifest)+1
        for name,ref in manifest.items():
            data=z.read(name);assert len(data)==ref['bytes'] and digest(data)==ref['sha256']
    verification={'status':'PASS_ZIP_CRC_ALL_MEMBER_SHA_AND_GIT_BUNDLE','zip':str(a.zip),'bytes':a.zip.stat().st_size,'sha256':digest(a.zip.read_bytes()),'members':len(manifest)+1,'verified_remote_commit':head,'old_experiments_executed':0}
    a.zip.with_suffix('.verification.json').write_text(json.dumps(verification,indent=2)+'\n')
    print(json.dumps(verification,indent=2))


if __name__=='__main__':main()
