#!/usr/bin/env python3
"""Recover text candidates from recorded patch requests; never execute them.

The private bundle retains supplied research material. The public repository gets
only research-code candidates, provenance, and explicitly recovered result rows.
Recovered candidates are not a verified replacement for the deleted workspace.
"""
import argparse
import collections
import csv
import hashlib
import io
import json
import pathlib
import re
import shutil
import zipfile


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def output_text(value):
    if isinstance(value, list):
        return '\n'.join(x.get('text', '') for x in value if isinstance(x, dict))
    return value if isinstance(value, str) else ''


def project_relative(name):
    prefix = '/home/youns/workspace/'
    if not name.startswith(prefix + 'ele548-project'):
        return None
    p = pathlib.PurePosixPath(name[len(prefix):])
    return p.as_posix() if '..' not in p.parts else None


def apply_update(before, patch_lines):
    """Only apply unambiguous, exact-context hunks; no fuzzy repair."""
    chunks, current = [], []
    for line in patch_lines:
        if line.startswith('@@'):
            if current:
                chunks.append(current)
            current = []
        elif line and line[0] in ' +-':
            current.append(line)
        elif line.startswith('*** End of File') or not line:
            continue
        else:
            raise ValueError('UNSUPPORTED_PATCH_LINE')
    if current:
        chunks.append(current)
    lines = before.splitlines()
    cursor = 0
    for chunk in chunks:
        old = [x[1:] for x in chunk if x[0] in ' -']
        new = [x[1:] for x in chunk if x[0] in ' +']
        if not old:
            raise ValueError('INSERT_WITHOUT_EXACT_CONTEXT')
        matches = [n for n in range(cursor, len(lines) - len(old) + 1) if lines[n:n + len(old)] == old]
        if len(matches) != 1:
            raise ValueError('NON_UNIQUE_OR_MISSING_CONTEXT')
        at = matches[0]
        lines[at:at + len(old)] = new
        cursor = at + len(new)
    return '\n'.join(lines) + '\n'


def public_candidate(path):
    p = pathlib.PurePosixPath(path)
    parts = set(p.parts)
    blocked = {'sources', 'prior_hw1', 'third_party', 'data', 'eda', 'rtl', 'papers', 'extracted'}
    if parts & blocked or any('hw1' in x.lower() for x in p.parts):
        return False
    if p.name.startswith('.'):
        return False
    code = {'.py', '.sh', '.cc', '.cpp', '.h', '.hh', '.hpp'}
    if p.suffix in code:
        return True
    if p.suffix == '.json' and 'configs' in parts:
        return True
    if p.suffix == '.md' and ('reports' in parts or p.name.startswith('README') or 'handoff_analysis' in parts):
        return not any(x in path.lower() for x in ('environment', 'license', 'source_access', 'course'))
    return p.name in ('Makefile', 'CMakeLists.txt')


def secret_marker(text):
    return bool(re.search(r'-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----|gh[pousr]_[A-Za-z0-9_]{25,}|github_pat_[A-Za-z0-9_]{25,}|AKIA[0-9A-Z]{16}', text))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--session', type=pathlib.Path, required=True)
    ap.add_argument('--attachments', type=pathlib.Path, required=True)
    ap.add_argument('--repo', type=pathlib.Path, required=True)
    ap.add_argument('--private', type=pathlib.Path, required=True)
    ap.add_argument('--zip', type=pathlib.Path, required=True)
    ap.add_argument('--max-line', type=int, required=True)
    a = ap.parse_args()
    assert not a.private.exists() and not a.zip.exists()
    a.private.mkdir(parents=True)
    state, metadata, events = {}, {}, []
    patch_count = 0
    outputs = []
    patch_re = re.compile(r'tools\.apply_patch\(\s*("(?:\\.|[^"\\])*")\s*\)', re.S)
    header = re.compile(r'^\*\*\* (Add|Update|Delete) File: (.+)$')
    with a.session.open() as stream:
        for line_number, raw in enumerate(stream, 1):
            if line_number > a.max_line:
                break
            entry = json.loads(raw)
            x = entry.get('payload', {})
            if entry.get('type') != 'response_item':
                continue
            if x.get('type') == 'custom_tool_call_output':
                text = output_text(x.get('output'))
                if 'mean net%A' in text and 'SOURCE_RAW130_CHARM_2000S' in text:
                    outputs.append((line_number, text))
            if x.get('type') != 'custom_tool_call' or x.get('name') != 'exec':
                continue
            for match in patch_re.finditer(x.get('input', '')):
                patch = json.loads(match.group(1))
                if 'ele548-project' not in patch:
                    continue
                patch_count += 1
                target = a.private / 'patch_requests' / ('%06d_%03d.patch' % (line_number, patch_count))
                target.parent.mkdir(exist_ok=True)
                target.write_text(patch)
                sections = []
                for pline in patch.splitlines():
                    m = header.match(pline)
                    if m:
                        sections.append((m.group(1), m.group(2), []))
                    elif sections and pline != '*** End Patch':
                        sections[-1][2].append(pline)
                for kind, original_path, body in sections:
                    rel = project_relative(original_path)
                    if rel is None:
                        continue
                    event = {'record_line': line_number, 'operation': kind, 'original_path': original_path, 'path': rel}
                    try:
                        if kind == 'Add':
                            if any(not x.startswith('+') for x in body):
                                raise ValueError('NON_ADD_CONTENT')
                            state[rel] = '\n'.join(x[1:] for x in body) + '\n'
                            metadata[rel] = {'last_applied_request_line': line_number, 'unapplied_updates': 0, 'source': 'RECORDED_TOOL_REQUEST_NOT_EXECUTION_CERTIFICATE'}
                        elif kind == 'Update':
                            if rel not in state:
                                raise ValueError('BASE_FILE_NOT_RECOVERED')
                            state[rel] = apply_update(state[rel], body)
                            metadata[rel]['last_applied_request_line'] = line_number
                        else:
                            state.pop(rel, None)
                            metadata.pop(rel, None)
                        event['status'] = 'TEXT_CANDIDATE_UPDATED_NOT_RETESTED'
                    except ValueError as exc:
                        event['status'] = str(exc)
                        if rel in metadata:
                            metadata[rel]['unapplied_updates'] += 1
                    events.append(event)
    published = []
    held = []
    for rel, text in sorted(state.items()):
        private_file = a.private / 'text_candidates' / rel
        private_file.parent.mkdir(parents=True, exist_ok=True)
        private_file.write_text(text)
        if public_candidate(rel) and not secret_marker(text):
            dest = a.repo / 'recovered' / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(text)
            published.append({'path': dest.relative_to(a.repo).as_posix(), 'sha256': sha(dest.read_bytes()), 'bytes': dest.stat().st_size, **metadata[rel], 'qualification': 'RECOVERED_TEXT_CANDIDATE_NOT_BUILT_OR_TESTED'})
        else:
            held.append(rel)
    write_json(a.private / 'PATCH_RECOVERY_EVENTS.json', events)
    # Preserve original privately supplied bundles and PDFs, without publishing.
    ids = {p.parent.name for p in a.attachments.glob('*/BP_SEU*.zip')}
    ids.update(['2989a548-e4d1-4aca-ae15-3e1477230d9c', 'a545d192-4eeb-4d24-aa75-4cdc376a1968'])
    originals = []
    for ident in sorted(ids):
        directory = a.attachments / ident
        if not directory.is_dir():
            continue
        for source in sorted(directory.iterdir()):
            if not source.is_file():
                continue
            data = source.read_bytes()
            if source.suffix.lower() == '.zip':
                with zipfile.ZipFile(source) as z:
                    assert z.testzip() is None, source.name
            dest = a.private / 'original_attachments' / ident / source.name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
            originals.append({'name': source.name, 'archive_path': dest.relative_to(a.private).as_posix(), 'bytes': len(data), 'sha256': sha(data), 'public_repository': False})
    assert outputs, 'No historical B4 summary output found.'
    record_line, summary_text = outputs[-1]
    proof = a.private / 'result_evidence' / ('record_%d.txt' % record_line)
    proof.parent.mkdir(exist_ok=True)
    proof.write_text(summary_text)
    results = []
    pattern = re.compile(r'^(\S+) (SOURCE_RAW130_CHARM_2000S|SSTAR346_SINGLE_SBU|WHOLE_K1_REF_SCALE1000000000000000) (\S+) mean net%A ([+-]?[0-9.]+) CI (\[[^\n]+?\]) signs (\d+) (\d+) (\d+)$', re.M)
    for m in pattern.finditer(summary_text):
        lo, hi = json.loads(m.group(5))
        results.append({'program': m.group(1), 'scenario': m.group(2), 'method': m.group(3), 'logged_mean_net_pct_A': float(m.group(4)), 'logged_bootstrap95_cycles_low': lo, 'logged_bootstrap95_cycles_high': hi, 'positive_owners': int(m.group(6)), 'zero_owners': int(m.group(7)), 'negative_owners': int(m.group(8)), 'historical_record_line': record_line, 'recovery_status': 'EXACT_LOGGED_SUMMARY_FIELDS_NOT_RECOVERED_OWNER_RAW'})
    assert len(results) == 42 and all(x['positive_owners'] + x['zero_owners'] + x['negative_owners'] == 8 for x in results)
    dest = a.repo / 'results/summaries/b4_eval_logged_summary.csv'
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0]))
        writer.writeheader()
        writer.writerows(results)
    status = {'recovery_date': '2026-11-05', 'status': 'PARTIAL_RECOVERY_FROM_SURVIVING_UPLOADS_AND_HISTORICAL_RECORDS', 'cutoff_record_line': a.max_line, 'recorded_patch_requests': patch_count, 'current_text_candidates': len(state), 'public_code_document_candidates': len(published), 'private_only_candidate_count': len(held), 'unapplied_patch_events': sum(x['status'] != 'TEXT_CANDIDATE_UPDATED_NOT_RETESTED' for x in events), 'original_attachment_count': len(originals), 'recovered_EVAL_summary_rows': len(results), 'original_completed_zip_recovered': False, 'full_owner_rows_recovered': False, 'gem5_ELF_and_raw_trials_recovered': False, 'simulation_or_recovered_code_executed': False, 'qualification': 'Do not treat candidate source or logged aggregates as a verified reconstructed producer or raw experiment archive.'}
    write_json(a.repo / 'recovery/RECOVERY_STATUS.json', status)
    write_json(a.repo / 'recovery/RECOVERED_FILES.json', published)
    write_json(a.private / 'ORIGINAL_ATTACHMENTS_MANIFEST.json', originals)
    write_json(a.private / 'RECOVERY_STATUS.json', status)
    # Bundle is completed separately after repository docs and remote receipts.
    print(json.dumps(status, indent=2))


if __name__ == '__main__':
    main()
