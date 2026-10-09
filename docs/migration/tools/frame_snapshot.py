"""Snapshot the pipeline's Frame products for some Blocks, and compare two snapshots.

Used to check that a code change (e.g. the apophis2 recovery: moving find_block_for_frame/
determine_original_name into catalog_subs, the update_frame_zeropoint reconciliation) leaves
reprocessed data unchanged.

DO NOT rerun the pipeline over these Blocks against neoexchange-dev-copy: that is the database of
record for the pipelines branch and DART/Hera, and a rerun overwrites Frames (and e92 files) in
place. Rerun only against a scratch database (NEOX_DB_ENGINE/NEOX_DB_NAME) seeded with these
Blocks, with REDIS_HOSTNAME pointing at a local redis (not apophis2) so the local worktree's
workers do the work:

    python docs/migration/tools/frame_snapshot.py snapshot > before.tsv  # after the "before" code's rerun
    python docs/migration/tools/frame_snapshot.py snapshot > after.tsv   # after the "after" code's rerun
    python docs/migration/tools/frame_snapshot.py compare before.tsv after.tsv

Snapshotting neoexchange-dev-copy itself is safe (read-only) and records the copy of record.

Default reference Blocks (IDs from neoexchange-dev-copy, 2026-10-08):
  35906  65803 Didymos, coj 2m0 MuSCAT, 2026-07-12 (343 e92 frames, 4 filters)
  36170  164216, sin 1m0 Sinistro, 2026-07-31 (96 e92)
  25250  65803 Didymos, Swope ('lco' 1m0), 2022 (401 e92) -- DART copy of record; exercises the
         rccd* (Swope) code path

Run from anywhere in the repo; it finds neoexchange/ relative to this file and uses the
environment's NEOX_DB_* settings. Read-only on the DB.
"""
import argparse
import csv
import math
import os
import sys
from collections import Counter
from pathlib import Path

DEFAULT_BLOCKS = [35906, 36170, 25250]
FIELDS = ['block_id', 'filename', 'frametype', 'id', 'sitecode', 'instrument', 'filter', 'midpoint',
          'zeropoint', 'zeropoint_err', 'zeropoint_src', 'color_used', 'color', 'color_err', 'fwhm',
          'rms_of_fit', 'nstars_in_fit', 'astrometric_catalog', 'photometric_catalog', 'n_catsrcs']
KEY = ('block_id', 'filename', 'frametype')
# Expected to change if a Frame is deleted and recreated; reported separately, not as a value change.
IDENTITY = ('id',)


def setup_django():
    project = Path(__file__).resolve().parents[3] / 'neoexchange'
    sys.path.insert(0, str(project))
    os.chdir(project)
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'neox.settings')
    import django
    django.setup()


def snapshot(block_ids, out):
    setup_django()
    from django.db.models import Count
    from core.models import Frame

    qs = (Frame.objects.filter(block_id__in=block_ids).defer('wcs')
          .annotate(n_catsrcs=Count('catalogsources', distinct=True))
          .order_by('block_id', 'filename', 'frametype', 'id'))
    writer = csv.writer(out, delimiter='\t', lineterminator='\n')
    writer.writerow(FIELDS)
    found = Counter()
    for frame in qs:
        found[frame.block_id] += 1
        writer.writerow(['' if v is None else v for v in (getattr(frame, f) for f in FIELDS)])
    for block_id in block_ids:
        print(f'# Block {block_id}: {found[block_id]} Frames', file=sys.stderr)


def read(path):
    with open(path, newline='') as fh:
        rows = list(csv.DictReader(fh, delimiter='\t'))
    by_key = {}
    dupes = Counter(tuple(r[k] for k in KEY) for r in rows)
    for r in rows:
        by_key.setdefault(tuple(r[k] for k in KEY), []).append(r)
    return by_key, {k: n for k, n in dupes.items() if n > 1}


def as_float(v):
    try:
        return float(v)
    except ValueError:
        return None


def compare(before_path, after_path, rtol, atol):
    before, before_dupes = read(before_path)
    after, after_dupes = read(after_path)
    problems = 0

    only_before = sorted(set(before) - set(after))
    only_after = sorted(set(after) - set(before))
    for label, keys in (('only in before', only_before), ('only in after', only_after)):
        if keys:
            problems += len(keys)
            print(f'{len(keys)} Frames {label}:')
            for k in keys[:20]:
                print('   ', *k)
            if len(keys) > 20:
                print(f'    ... and {len(keys) - 20} more')

    new_dupes = {k: n for k, n in after_dupes.items() if n > before_dupes.get(k, 1)}
    if new_dupes:
        problems += len(new_dupes)
        print(f'{len(new_dupes)} (block, filename, frametype) keys gained duplicate Frames:')
        for k, n in sorted(new_dupes.items())[:20]:
            print('   ', *k, f'x{n}')

    value_fields = [f for f in FIELDS if f not in KEY and f not in IDENTITY]
    changed = Counter()
    max_delta = {}
    examples = {}
    recreated = 0
    for k in sorted(set(before) & set(after)):
        b, a = before[k][0], after[k][0]
        if b['id'] != a['id']:
            recreated += 1
        for f in value_fields:
            if b[f] == a[f]:
                continue
            fb, fa = as_float(b[f]), as_float(a[f])
            if fb is not None and fa is not None:
                if math.isclose(fb, fa, rel_tol=rtol, abs_tol=atol):
                    continue
                max_delta[f] = max(max_delta.get(f, 0.0), abs(fa - fb))
            changed[f] += 1
            examples.setdefault(f, (k, b[f], a[f]))

    common = len(set(before) & set(after))
    print(f'{common} Frames in both snapshots; {recreated} have a new Frame id (deleted and recreated)')
    if changed:
        problems += sum(changed.values())
        print('Changed values (field: n Frames, max |delta|, example):')
        for f in value_fields:
            if f in changed:
                (blk, fn, ft), vb, va = examples[f]
                delta = f'{max_delta[f]:.6g}' if f in max_delta else 'n/a'
                print(f'  {f}: {changed[f]}, {delta}, {fn} (type {ft}, block {blk}): {vb!r} -> {va!r}')
    print('IDENTICAL' if problems == 0 else f'{problems} differences')
    return 0 if problems == 0 else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='cmd', required=True)
    p_snap = sub.add_parser('snapshot', help='write a TSV of Frame values for the Blocks to stdout')
    p_snap.add_argument('blocks', nargs='*', type=int, default=DEFAULT_BLOCKS)
    p_cmp = sub.add_parser('compare', help='compare two snapshots; exit status 1 if they differ')
    p_cmp.add_argument('before')
    p_cmp.add_argument('after')
    p_cmp.add_argument('--rtol', type=float, default=1e-9)
    p_cmp.add_argument('--atol', type=float, default=1e-9)
    args = parser.parse_args()
    if args.cmd == 'snapshot':
        snapshot(args.blocks, sys.stdout)
        return 0
    return compare(args.before, args.after, args.rtol, args.atol)


if __name__ == '__main__':
    sys.exit(main())
