# Checkpoint - 2026-08-11

## Recovery Anchor

- Active PDA repository: `/Users/johnelliottcisneros/Documents/Codex/2026-07-17/i/pda`
- Django app root: `src/`
- Virtual environment: `pda-venv-clean`
- Preserved working group test assessment: Assessment 5
- Group test access code: `!GROUPTEST`

## Group Workflow Validation

- Completed a genuine 70-question `!GROUPTEST` assessment.
- Confirmed all 70 responses saved.
- Confirmed Score and all subscores were created correctly.
- Identified abandoned Assessment 4 as contaminating group aggregation and isolated it.
- Confirmed `generate_pdf(5, False)` reaches the recovered group-report path.
- Corrected the group-report static-logo path using Django static finders.
- Diagnosed a ReportLab 3.6.13 failure in the group report's `HorizontalBarChart3D`.
- Created backup:
  `core/utilities.py.before-horizontal-chart-fix-2026-08-11`
- Changed the failing horizontal chart from:
  `HorizontalBarChart3D()`
  to:
  `HorizontalBarChart()`
- Disabled its 3D-only `zDepth` setting.
- Re-ran:
  `generate_pdf(5, False)`
- Result: completed successfully and returned `False` with no exception.
- Confirmed generated group PDF:
  `media/group_pdfs/Local_Group_Test_1_group_results.pdf`
- Visually inspected the PDF; layout, charts, logo, and report structure appeared correct.

## Current Conclusion

The recovered group/institutional workflow now successfully completes:

70-question assessment
→ saved responses
→ Score/subscores
→ group aggregation
→ group PDF generation

This is a major recovery milestone and substantially reduces uncertainty before modernization.

## Next Steps

1. Finish recovery validation and basic housekeeping.
2. Confirm the important individual and group user paths remain functional.
3. Document remaining legacy quirks that should be preserved or intentionally changed.
4. Establish a clean modernization baseline.
5. Before modernization decisions are finalized, use an independent second AI/system as a skeptical technical reviewer and compare recommendations against the recovered working application.
6. Treat automated group PowerPoint/presentation generation as a later enhancement, not part of core recovery.


## Automated Test Baseline

- Initial full suite run:
  - 316 tests
  - 67 errors
  - 1 failure
- Diagnosed a naming collision between the recovered PDA `Group` model and Django's authentication `Group`.
- Fixed production signal handlers to explicitly use Django `AuthGroup`.
- Fixed corresponding test references in `test_signals.py` and `test_admin.py`.
- Updated one stale consultation wording assertion from old phone/in-person language to the current online consultation wording.
- Targeted validation:
  - signals: 17/17 passing
  - admin: 56/56 passing
  - representative consultation test passing
- Final full suite:
  - `Ran 316 tests in 97.245s`
  - `OK`

Current recovery baseline: all 316 automated tests pass.
