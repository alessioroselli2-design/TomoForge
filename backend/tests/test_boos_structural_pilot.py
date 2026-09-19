from scripts.pilot_boos_structural_diagnostics_from_r2 import (
    END_PAGE,
    SEGMENTS,
    SKIPPED_PAGE,
    START_PAGE,
)


def test_boos_diagnostic_skips_page_21_and_covers_other_pages_once():
    covered = [
        page
        for segment_start, segment_end in SEGMENTS
        for page in range(segment_start, segment_end + 1)
    ]
    expected = [
        page for page in range(START_PAGE, END_PAGE + 1) if page != SKIPPED_PAGE
    ]

    assert SKIPPED_PAGE == 21
    assert covered == expected
    assert len(covered) == 23
    assert len(set(covered)) == len(covered)
    assert all(
        (segment_end - segment_start + 1) <= 12
        for segment_start, segment_end in SEGMENTS
    )
