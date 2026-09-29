# Complete narration and summary revision

User correction: speech is too slow; news must be summarized completely, every summary point displayed and spoken, no ellipsis standing in for omitted content.

- [x] Rewrite the same six news stories after reading full articles; 3–5 complete factual points with necessary qualifications.
- [x] Remove bullet truncation and 120–160-character clipping from automatic collection. Preserve context and use complete sentences.
- [x] Use one canonical title-plus-summary transcript for on-screen cards, narration and subtitles.
- [x] Paginate long summaries without dropping any bullet or text. Keep the page until its final audio finishes.
- [x] Increase Edge speech rate from -8% to +20%; expose a rate setting and speed up local fallback too.
- [x] Synthesize complete speech units, use word timing for subtitles, and validate the final word before encoding.
- [x] Generate a replacement video. Verify full content coverage, page coverage, final subtitle/audio timing and full MP4 decode.

Existing artifacts remain available; output the corrected edition to a new directory. No scheduling or publishing.

Verification: 47 tests and 14 subtests passed. Replacement MP4 is outputs/2026-09-12-complete-fast/daily.mp4 (273.708 seconds, +20% Edge speech). All 23 summary points, 31 speech units and 63 subtitle cues have exact transcript coverage. Full decode and visual page review passed; independent rendering review found no blocking issues. Stored-source automatic-summary regression: Habitat 434 characters/5 points; Bark 380/4; third story 469/3.
