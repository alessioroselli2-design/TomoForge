from reference_sources import (
    source_is_rule_source,
    source_metadata_for_page,
    source_requires_vision,
)
from reference_library import source_reference
from services.canonical import source_authority, source_record_is_excluded
from services.library import manual_source_metadata


def test_runtime_alias_maps_to_registered_phb():
    meta = source_metadata_for_page(
        "Manuale_del_giocatore__1787259882002.pdf",
        10,
    )
    assert meta["logical_source_id"] == "phb_2014_it"
    assert meta["language"] == "it"
    assert meta["authority_class"] == "licensed_translation"


def test_planescape_physical_pdf_maps_three_logical_books():
    filename = "762692978-D-D-5e-Planescape-Adventure-in-the-Multiverse.pdf"
    assert source_metadata_for_page(filename, 10)["logical_source_id"] == "ps_sigil_2023_en"
    assert source_metadata_for_page(filename, 120)["logical_source_id"] == "ps_tofw_2023_en"
    assert source_metadata_for_page(filename, 220)["logical_source_id"] == "ps_mpp_2023_en"
    assert source_metadata_for_page(filename, 120)["logical_page"] == 22


def test_multiverse_parts_share_logical_source_with_logical_page_offsets():
    first = source_metadata_for_page("Mostri del multi verso 1-100.pdf", 5)
    second = source_metadata_for_page("Mostri del multiverso 101-200.pdf", 5)
    third = source_metadata_for_page("Mostri del multiverso 201-294.pdf", 5)
    assert {first["logical_source_id"], second["logical_source_id"], third["logical_source_id"]} == {"mpmm_2022_it"}
    assert (first["logical_page"], second["logical_page"], third["logical_page"]) == (5, 105, 205)


def test_compilation_page_maps_to_its_logical_source():
    meta = source_metadata_for_page("701858566-RRN5YRR.pdf", 34)
    assert meta["logical_source_id"] == "mc_v4_eldraine_2023_en"
    assert meta["logical_page"] == 1
    assert meta["source_role"] == "ingest_copy"
    assert source_requires_vision("701858566-RRN5YRR.pdf", 34)


def test_duplicates_documents_misidentified_and_unknown_sources_do_not_auto_import():
    assert not source_is_rule_source("Manuale del Giocatore (1).pdf")
    assert not source_is_rule_source("655737067-png2pdf.pdf")
    assert not source_is_rule_source("440983851-Errata-D-D-ITA.pdf")
    assert not source_is_rule_source("Scheda personaggio .pdf")
    assert not source_is_rule_source("manuale-non-registrato.pdf")


def test_source_reference_persists_logical_provenance():
    ref = source_reference(
        "Guildmasters’ Guide to Ravnica.2 .pdf",
        40,
        "en",
    )
    assert ref["logical_source_id"] == "ggtr_2018_en"
    assert ref["ruleset"] == "2014"
    assert ref["authority_class"] == "official_supplement"
    assert ref["logical_page"] == 40
    assert ref["language"] == "en"


def test_manual_metadata_uses_registered_language_and_ocr_mode():
    english = manual_source_metadata("469650052-Explorer-s-Guide-to-Wildemount-pdf.pdf")
    scan = manual_source_metadata("847921086-Manuale-Dei-Mostri-5e.pdf")
    assert english["language"] == "en"
    assert english["logical_source_id"] == "egtw_2020_en"
    assert english["native_text"] is True
    assert scan["native_text"] is False


def record(authority, *, role="authority", status="active"):
    return {
        "source_refs": [{
            "filename": "source.pdf",
            "authority_class": authority,
            "source_role": role,
            "source_status": status,
            "ruleset": "2014",
        }]
    }


def test_explicit_source_authority_order_and_exclusions():
    assert source_authority(record("official_errata"))[0] > source_authority(record("official_supplement"))[0]
    assert source_authority(record("official_supplement"))[0] > source_authority(record("licensed_translation"))[0]
    assert source_authority(record("licensed_translation"))[0] > source_authority(record("extraction_aid", role="extraction_aid"))[0]
    assert source_record_is_excluded(record("official_errata", status="superseded"))
    assert source_authority(record("official_errata", status="superseded"))[0] < source_authority(record("official_supplement"))[0]
