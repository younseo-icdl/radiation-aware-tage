# Repository backup workflow

The user designated `younseo-icdl/radiation-aware-tage` for code and important-document backup on 2026-11-05.

- Preserve recovered-source provenance and distinguish candidate text, historically hash-matched bytes, and newly tested code.
- The current task is source recovery. Do not rerun old fault-injection or gem5 campaigns as part of recovery or backup.
- Commit meaningful code, configuration, authored reports and small result summaries; push them to the configured remote and verify the remote commit SHA when work is complete.
- Preserve prior commits. Do not force-push or rewrite shared history.
- Keep original private handoff bundles, papers/course/HW1 distributions, raw session logs, credentials, license files and PDK/library data outside the public repository. Record external archive locations and hashes instead.
- Use `scripts/check_backup_scope.py` before pushing. Keep large execution artifacts in a separately copied, hashed archive.
