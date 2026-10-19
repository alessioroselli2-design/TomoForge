"""Original Italian Monster Manual: physical-page statblock census 297–304.

Page images privately inspected in this session; no licensed scan or complete
ability/action texts committed. This is a coverage inventory, not an assertion
of complete verified statistics or an importer. Future records must pass the
independent 6-ability, CA/PF/HD, source, collision and CI gates.
"""
from __future__ import annotations

SOURCE_ID = "mm_2014_it"
FILENAME = "847921086-Manuale-Dei-Mostri-5e.pdf"
SOURCE_SHA256 = "b33eb72e5eb78fe3e3dcbde5315f5b9afbe42e4a457a518cc93f7766979a381c"
SOURCE_PAGE_COUNT = 353

PHYSICAL_PAGE_STATBLOCKS: dict[int, tuple[str, ...]] = {
    297: ("Vampiro",),
    298: ("Progenie Vampirica",),
    299: ("Verme Purpureo",),
    300: ("Vermeiena",),
    301: ("Viverna",),
    302: ("Wight",),
    303: ("Wraith",),
    304: ("Xorn",),
}

STATUS = "source_page_identity_checked_not_integral_statblock_verified"
WRITES = 0

def checked_inventory(catalog: dict) -> dict[int, tuple[str, ...]]:
    required = {
        "logical_source_id": SOURCE_ID,
        "physical_filename": FILENAME,
        "physical_sha256": SOURCE_SHA256,
        "physical_pages": SOURCE_PAGE_COUNT,
        "source_status": "active",
        "source_role": "authority",
        "authority_class": "licensed_translation",
        "text_mode": "vision_required",
    }
    if not isinstance(catalog, dict) or any(catalog.get(k) != v for k, v in required.items()):
        raise ValueError("original_source_mismatch")
    return {page: tuple(names) for page, names in PHYSICAL_PAGE_STATBLOCKS.items()}
