# CrownPath — Repository Search Addendum: Photo Data Paths

**Date:** 2026-10-13. **Status:** Evidence gathering only; not a complete code audit.

## Searches on repository default branch

GitHub repository code search was run for `UploadFile`, `consent`, `delete image`, and `scalp photo`.

- `UploadFile`: no matching indexed files returned. This does **not** rule out upload implementations under other identifiers or unindexed files.
- `consent`: returned curriculum, operations and pilot documentation including `crownpath/advanced_lesson_content.py`, `crownpath/wellness_lesson_content.py`, `crownpath/experience_agent_lesson_content.py`, and multiple `docs/` lesson/operations files.
- `delete image`: returned `crownpath/experience_agent_lesson_content.py`; its implementation relevance has **not** been inspected yet.
- `scalp photo`: returned pilot and curriculum documents.

These searches corroborate substantial **policy and training content**, but do not verify operational consent capture, secure image storage, access controls, deletion, or withdrawal.

## Next technical review

1. Inspect `crownpath/experience_agent_lesson_content.py` for the precise `delete image` reference and distinguish curriculum from executable behavior.
2. Inventory the repository's API routes, storage adapters, frontend camera/upload handlers, and external processing integrations using file-tree inspection and targeted code searches.
3. Build a data-flow map from image capture through retention and deletion; explicitly mark unimplemented or unverified stages.
4. Test any actual workflows with synthetic images in an isolated environment only after access protection is confirmed.
5. Require privacy and security reviewer sign-off plus owner approval before participant photos.

**Interim rule:** No real participant images in previews or pilot services. Use mannequins or synthetic examples. Keep issue #41 open; no automatic release or enrollment.
