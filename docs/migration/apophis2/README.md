# apophis2 inventory (Q18)

Populate with the read-only inventory of the production pipeline host:

    ssh apophis2 bash -s < docs/migration/tools/apophis2_inventory.sh > docs/migration/apophis2/inventory-$(date +%F).txt
    ssh apophis2 'cd ~/git/neoexchange-devel && git --no-optional-locks diff' > docs/migration/apophis2/uncommitted.patch

Then review `uncommitted.patch` and the untracked-file list for secrets before committing anything from it, and record decisions (what to commit to `pipelines`, what to refactor, what to drop) in MIGRATION_PLAN.md §2 Phase 0 step 0.

## Contents after the 2026-09-29 inventory

- `ANALYSIS.md` — findings and per-change dispositions (start here)
- `inventory-2026-09-29.txt`, `inventory2-…`, `inventory3-…` — raw read-only inventory output (redacted)
- `uncommitted.patch` — the 4-file working-tree diff from `~/git/neoexchange-devel` (load-bearing; see ANALYSIS §2)
- `stashes/pipelines-stashes-0-4.patch` — the five `pipelines` stashes (superseded)
- `scripts/` — orphan IPython transcripts and scratch files; `scripts/stacking/` — untracked files from the stacking checkout
- `home-cron-scripts/` — apophis2's `~/download_*_cron`, `~/upload_data_cron` (differ from `docker/root/` copies only in paths/wrappers)
