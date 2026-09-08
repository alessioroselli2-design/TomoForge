from pathlib import Path

from scripts.audit_concordant_text_peer_repo_artifacts import (
    load_structured_artifact_strings,
    summarize_concordant_text_peer_repo_artifacts,
)


def _source(
    source_id,
    sha,
    *,
    text_mode="vision_required",
    filename=None,
    source_role="visual_aid",
    logical_source_id="ggtr_2018_en",
    title="Guildmasters’ Guide to Ravnica",
):
    return {
        "id": source_id,
        "physical_filename": filename or f"{source_id}.pdf",
        "physical_sha256": sha,
        "physical_size_bytes": 1000,
        "physical_pages": 258,
        "logical_source_id": logical_source_id,
        "title": title,
        "language": "en",
        "ruleset": "2014",
        "authority_class": "official_supplement",
        "source_role": source_role,
        "source_status": "active",
        "page_start": 1,
        "page_end": 258,
        "text_mode": text_mode,
        "import_state": "catalogued",
        "imported_record_count": 0,
    }


def test_exact_sha_artifact_is_reported_but_never_authorizes_import(tmp_path: Path):
    blocked = _source("vision", "sha-vision")
    text_peer = _source(
        "text",
        "857059410acb8db20bf01e78fe0432e8f2a35948ed70db2ebdaaa3c1ab017956",
        text_mode="text",
        filename="Guildmasters’ Guide to Ravnica.2 .pdf",
        source_role="authority",
    )
    artifact = tmp_path / "artifact.json"
    artifact.write_text(
        '{"source_sha256":"857059410acb8db20bf01e78fe0432e8f2a35948ed70db2ebdaaa3c1ab017956"}',
        encoding="utf-8",
    )

    strings = load_structured_artifact_strings(tmp_path)
    result = summarize_concordant_text_peer_repo_artifacts([blocked, text_peer], [], strings)

    assert result["concordant_text_peer_pairs"] == 1
    assert result["pairs_with_exact_sha_structured_artifact"] == 1
    assert result["pairs_with_nominal_hint_but_no_exact_sha"] == 0
    assert result["pairs_with_ambiguous_nominal_hint"] == 0
    assert result["exact_sha_artifact_paths_by_pair"] == {
        "vision->text": [str(artifact)]
    }
    assert result["exact_sha_artifact_evidence_is_review_candidate_only"] is True
    assert result["automatic_import_authorized"] is False
    assert result["database_write_authorized"] is False
    assert result["canonicalization_authorized"] is False


def test_filename_and_title_hints_do_not_count_as_exact_sha_evidence(tmp_path: Path):
    blocked = _source("vision", "sha-vision")
    text_peer = _source(
        "text",
        "sha-text",
        text_mode="text",
        filename="Guildmasters’ Guide to Ravnica.2 .pdf",
        source_role="authority",
    )
    artifact = tmp_path / "artifact.json"
    artifact.write_text(
        '{"filename":"Guildmasters’ Guide to Ravnica.2 .pdf",'
        '"title":"Guildmasters’ Guide to Ravnica"}',
        encoding="utf-8",
    )

    strings = load_structured_artifact_strings(tmp_path)
    result = summarize_concordant_text_peer_repo_artifacts([blocked, text_peer], [], strings)

    assert result["pairs_with_exact_sha_structured_artifact"] == 0
    assert result["pairs_with_filename_only_or_additional_hint"] == 1
    assert result["pairs_with_title_only_or_additional_hint"] == 1
    assert result["pairs_with_nominal_hint_but_no_exact_sha"] == 1
    assert result["pairs_with_ambiguous_nominal_hint"] == 0
    assert result["filename_or_title_evidence_is_not_import_proof"] is True
    assert result["automatic_import_authorized"] is False


def test_shared_nominal_artifact_hint_is_marked_ambiguous(tmp_path: Path):
    sources = [
        _source("vision-a", "sha-vision-a", logical_source_id="source_a"),
        _source(
            "text-a",
            "sha-text-a",
            text_mode="text",
            filename="shared-name.pdf",
            source_role="authority",
            logical_source_id="source_a",
        ),
        _source("vision-b", "sha-vision-b", logical_source_id="source_b"),
        _source(
            "text-b",
            "sha-text-b",
            text_mode="text",
            filename="shared-name.pdf",
            source_role="authority",
            logical_source_id="source_b",
        ),
    ]
    artifact = tmp_path / "artifact.json"
    artifact.write_text('{"filename":"shared-name.pdf"}', encoding="utf-8")

    result = summarize_concordant_text_peer_repo_artifacts(
        sources,
        [],
        load_structured_artifact_strings(tmp_path),
    )

    assert result["concordant_text_peer_pairs"] == 2
    assert result["pairs_with_exact_sha_structured_artifact"] == 0
    assert result["pairs_with_nominal_hint_but_no_exact_sha"] == 2
    assert result["pairs_with_ambiguous_nominal_hint"] == 2
    assert result["ambiguous_nominal_artifact_paths"] == {
        str(artifact): ["vision-a->text-a", "vision-b->text-b"]
    }
    assert result["ambiguous_nominal_evidence_requires_manual_provenance_review"] is True
    assert result["automatic_import_authorized"] is False


def test_exact_sha_pair_is_excluded_from_nominal_ambiguity(tmp_path: Path):
    sources = [
        _source("vision-a", "sha-vision-a", logical_source_id="source_a"),
        _source(
            "text-a",
            "sha-text-a",
            text_mode="text",
            filename="shared-name.pdf",
            source_role="authority",
            logical_source_id="source_a",
        ),
        _source("vision-b", "sha-vision-b", logical_source_id="source_b"),
        _source(
            "text-b",
            "sha-text-b",
            text_mode="text",
            filename="shared-name.pdf",
            source_role="authority",
            logical_source_id="source_b",
        ),
    ]
    artifact = tmp_path / "artifact.json"
    artifact.write_text(
        '{"filename":"shared-name.pdf","source_sha256":"sha-text-a"}',
        encoding="utf-8",
    )

    result = summarize_concordant_text_peer_repo_artifacts(
        sources,
        [],
        load_structured_artifact_strings(tmp_path),
    )

    assert result["pairs_with_exact_sha_structured_artifact"] == 1
    assert result["pairs_with_nominal_hint_but_no_exact_sha"] == 1
    assert result["pairs_with_ambiguous_nominal_hint"] == 0
    assert result["ambiguous_nominal_artifact_paths"] == {}


def test_invalid_json_is_ignored_without_promoting_evidence(tmp_path: Path):
    (tmp_path / "broken.json").write_text("{not-json", encoding="utf-8")
    assert load_structured_artifact_strings(tmp_path) == {}
