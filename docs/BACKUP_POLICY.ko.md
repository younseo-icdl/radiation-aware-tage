# 코드와 핵심 문서 백업

원격 저장소: https://github.com/younseo-icdl/radiation-aware-tage

작업을 마칠 때 코드·설정·중요 문서·작은 집계 결과를 commit하고 원격에 push합니다. 로컬 commit만으로는 서버 폴더 삭제에 대비한 백업이 되지 않습니다. GitHub에서 같은 commit SHA를 확인해야 합니다.

일반적인 순서:

```sh
git status --short
git add <변경한 코드·설정·문서 경로>
python3 scripts/check_backup_scope.py
git diff --cached --stat
git commit -m "변경 내용과 근거"
git push origin HEAD
git rev-parse HEAD
git ls-remote origin refs/heads/main
```

`.gitignore`는 실행 ELF/object, 대형 archive, 논문, PDK/library 등을 제외합니다. 원래 업로드 자료와 수업/HW1 reference는 private 복구 bundle로 보관합니다. source/manifest/config/seed·schedule의 작은 고정 파일, 보고서·통계 CSV는 버전 관리 대상으로 유지합니다. 회수한 과거 코드의 `runtime/` 경로 아래에도 중요한 source가 있어 `runtime/` 전체를 일괄 제외하지 않습니다.

큰 원시 결과는 별도의 저장 위치와 archive SHA256를 문서화하고 서버 밖에도 사본을 보관합니다. 이번 복구 ZIP은 로컬 다운로드용이며 공개 저장소에 논문/수업자료를 그대로 업로드하지 않습니다. 원본을 삭제하거나 새 실험이 기존 결과를 덮어쓰도록 만들지 않습니다.

새 실험은 현재 복구 작업의 범위가 아닙니다. 향후 재빌드나 정확성 검증이 필요하면 복구 상태와 missing dependency를 먼저 확인합니다.
