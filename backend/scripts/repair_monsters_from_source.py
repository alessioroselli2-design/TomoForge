#!/usr/bin/env python3
"""Source-guided repair for legacy monster OCR records.

Default mode is a read-only single-record dry-run (Zuggtmoy). The script:
1. selects legacy verified monsters that fail current semantic/numeric gates;
2. removes manual headings and structurally corrupted OCR names from repair;
3. resolves provenance against the live active source registry;
4. materializes the exact source PDF locally and verifies its SHA-256;
5. OCRs at most a 3-page window (target page +/- 1) with two independent
   Tesseract layout modes;
6. applies a source-specific layout profile when a manual is known to use
   two-column stat blocks, OCRing each column independently before parsing;
7. requires an independently-agreed monster candidate matching the known name;
8. requires the repaired core attributes to pass ocr_semantic_gates;
9. prints BEFORE/AFTER JSON plus a separate corrupt-name bucket; and
10. performs no UPDATE unless --execute is explicitly supplied.

The script never auto-approves or canonicalizes. Even a successful repair is
written as review_status='pending' with review flag 'ocr_da_verificare'.
Hosted LLM providers are intentionally disabled in this implementation.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import hashlib
import io
from datetime import datetime, timezone
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from reference_library import normalize_reference_name
from scripts.pilot_local_ocr_from_r2 import (
    _agreement_metrics,
    _run_tesseract,
    _sha256_file,
)
from services.monster_name_diagnostics import (
    compact_name_boundary_match,
    compact_name_bounded_edit_match,
    compact_name_containment_match,
)
from services.monster_semantic_diagnostics import (
    deterministic_core_field_matches,
    semantic_core_field_matches,
)
from services.monster_speed_token_diagnostics import speed_multi_extra_token_profile
from services.monster_statblock_ocr import (
    agreed_monster_records,
    parse_monster_statblocks,
)
from services.ocr_semantic_gates import (
    CA_FORMAT_ERROR_FLAG,
    CA_OUT_OF_BOUNDS_FLAG,
    CORRUPTED_ENTITY_NAME_FLAG,
    HP_FORMAT_ERROR_FLAG,
    INVALID_ENTITY_TITLE_FLAG,
    OCR_REVIEW_FLAG,
    apply_ocr_review_gates,
    entity_name_semantic_flags,
    monster_identity_sanity_flags,
    monster_semantic_numeric_flags,
)

PAGE_SIZE = 1000
EXPECTED_INITIAL_FAILURES = 109
REPAIR_FLAG = "source_guided_repair"
ELIGIBLE_SOURCE_ROLES = {"authority", "ingest_copy"}
CRITICAL_GATE_FLAGS = {
    CA_FORMAT_ERROR_FLAG,
    CA_OUT_OF_BOUNDS_FLAG,
    CORRUPTED_ENTITY_NAME_FLAG,
    HP_FORMAT_ERROR_FLAG,
    INVALID_ENTITY_TITLE_FLAG,
}

EXPECTED_RESIDUAL_BATCH_COUNTS = {
    "batch_alpha": 10,
    "batch_beta": 10,
    "batch_gamma": 11,
}
EXPECTED_RESIDUAL_BATCH_IDS_MD5 = {
    "batch_alpha": "e19f7085e1f3329aed8f42791a6d20b1",
    "batch_beta": "e53fa1ee7936cb90f648c1bcbda823b7",
    "batch_gamma": "6390fb4dd862b232f2d088d7ca1059b6",
}
RESIDUAL_BATCH_TARGETS: dict[str, tuple[dict[str, str], ...]] = {
    "batch_alpha": (
        {
            "id": "ref_1e187bb2bbc257439e399104067bf326",
            "name": "8Hadar-Kai Trafficante",
        },
        {"id": "ref_c106f9a6c3115dbf8578f832b04e3a3a", "name": "Altisauro"},
        {"id": "ref_14406fab44dc5f57a4bb06187ba33465", "name": "Bael"},
        {"id": "ref_e42d82c62c7b5bdba13c3c73663966ff", "name": "Cerato Po"},
        {"id": "ref_83a6b991bfec5efdb2dda4da60d408bb", "name": "Colosso Runico"},
        {"id": "ref_7a8a7ac7d33c526486ec2e3ba1ed0b4b", "name": "Congreghe Di Megere"},
        {
            "id": "ref_20727b47fb7e5dc0b5e97867d8cdb6bc",
            "name": "Consigliere Imperituro",
        },
        {"id": "ref_5a08650dfd5d5eccb3664eeef39a100b", "name": "Difensore D'Acciaio"},
        {"id": "ref_bccdf665b4e05ba1bd9d7f1710103779", "name": "Dimetrodonte"},
        {"id": "ref_94dd0655e7fc518aaf9e3ad214e0dba7", "name": "Quetzalcoatlus"},
    ),
    "batch_beta": (
        {"id": "ref_0ee44c23b128519f9443af353d92be96", "name": "Fulmine Vivente"},
        {
            "id": "ref_9ac0de67090652bdbe5e7fd1e01d00cb",
            "name": "Granchio Delle Tempeste",
        },
        {"id": "ref_028882e4b0ba5545a8f24dce604ed8e5", "name": "Ippoaracne Maschio"},
        {"id": "ref_c02722ffc60b57609c97adb39c12c702", "name": "Larvico"},
        {"id": "ref_808e61bb52e050a8a7576b0941cfb3b9", "name": "M Orfico"},
        {"id": "ref_0efce052de2d5929ac2fd17ae92a0c75", "name": "Molo Oh"},
        {"id": "ref_a2f721b697c85415a3bf86134a5b1f4b", "name": "Nube Mortale Vivente"},
        {"id": "ref_65730c7abb315480a261c2f4b23b2913", "name": "Pelle Bestiale"},
        {"id": "ref_70901222165b54fe8e2827d5a3968998", "name": "Quori Hashalaq,"},
        {"id": "ref_2f64f571e368521f9ab39c4d6bd898d3", "name": "Rak Tulkhesh"},
    ),
    "batch_gamma": (
        {
            "id": "ref_6ba9bc46793a53c7b7a20ac5041daf18",
            "name": "Rampollo Delle Profondità",
        },
        {"id": "ref_66cc59680c4e58fa93a99656f8a07887", "name": "Rana"},
        {"id": "ref_5549d8d3a7ca5198abad7d6595b52641", "name": "Ratto Cranico"},
        {"id": "ref_77ef6b47608e5575b9723e8d11de2011", "name": "Regi Sauro"},
        {
            "id": "ref_b414135fe8fd5447a6aedfba2a419baa",
            "name": "Sciame Di Ratti Cranici",
        },
        {"id": "ref_ae3e94213cfa52be8a5ab76654b078ad", "name": "Spirito Della Fiamma"},
        {"id": "ref_92c9bcafc2775a3ca81f8665ed9495cc", "name": "Straziato Re"},
        {"id": "ref_a24cdc1e8d97597696d46edc193d03fd", "name": "Torre D'Assedio"},
        {"id": "ref_f2c063d5c85a54f3849f899180d92c98", "name": "Velociraptor"},
        {
            "id": "ref_f3bb42178ac251a6be889d3e3b48c603",
            "name": "Yuan-Ti Portavoce Degli Incubi",
        },
        {
            "id": "ref_6b0e1564d7325987a342097cebb39316",
            "name": "Yuan-Ti Signore Della Fossa",
        },
    ),
}

EXPECTED_HEALTHY22_COUNT = 22
EXPECTED_HEALTHY22_IDS_MD5 = "3c1f0be4ba3b7429694fe1a797c50870"
HEALTHY22_CONFIRMATION_TOKEN = "REPAIR-HEALTHY22-22-3c1f0be4ba3b7429694fe1a797c50870"
HEALTHY22_TARGETS: tuple[dict[str, str], ...] = (
    {
        "id": "ref_09eb88310e015ab6aa41d9dc35874f48",
        "name": "Grung Guerriero D'Élite",
        "source_text_checksum": "3b83895b29020edb44eee6a37161661d6fb2833041b5e4b46efea0e66f565790",
    },
    {
        "id": "ref_13c451b5c15a5014a05870c538c1027f",
        "name": "Abishai Nero",
        "source_text_checksum": "8b0f24b28b6b5c134abd1f043d4949d926ceb7dce9ce41f895f7da1ad47e33e0",
    },
    {
        "id": "ref_1f9f9e07e45c598aabfbf96b74f6da5c",
        "name": "Supremo",
        "source_text_checksum": "d4c1ff1ebf2e2517e5ffb03059cb0d0582a52a5e0a1e54d7ba82fbf302b0daf7",
    },
    {
        "id": "ref_4f37ea01e1385ebaa14bd94e9927c3fb",
        "name": "Di Tenebre",
        "source_text_checksum": "a5fe712f86535281be78a8fdc54a7cf3cd5b4581b7a2fd56ea36bcb44b9fc9b4",
    },
    {
        "id": "ref_4fc3bf9cf15f5e109f9a305789da3396",
        "name": "Di Bronzo",
        "source_text_checksum": "ff8f58d6047f2fd38b18326e414e9120cdafdc7dd48458813c2fb4b0331abd73",
    },
    {
        "id": "ref_774152a7b21953f99d394f65a852c8ca",
        "name": "Abishai Bianco",
        "source_text_checksum": "53d7c69d77be68865f9c6db8fe6ad6d95094c2d9209a93841c299c9eceda30e1",
    },
    {
        "id": "ref_7b77784c85825bfdbf0ee87caa77685c",
        "name": "Abishai Verde",
        "source_text_checksum": "47127852a9f847f7b40eed01b98d3501f0d12ff16162716e6e02d70507ac5f31",
    },
    {
        "id": "ref_86e7c81f54295e38bf97d70b8dd37f74",
        "name": "Idroloth",
        "source_text_checksum": "761338350331d83b7710b3fbc10812827dfb2480e2227b97b24edf9af586cb42",
    },
    {
        "id": "ref_872a575e21a65e0e9ef677227c7aee61",
        "name": "Petron",
        "source_text_checksum": "53a51b79e011cab1bf2a33bcfeb417f63da9f000a848546efaf3593b86e6cd23",
    },
    {
        "id": "ref_8be52d9c63b0507fb8a1ee943dfef4a7",
        "name": "Predatore D'Acciaio",
        "source_text_checksum": "dbb31095d0be61ee7176b349b0049c58fa2c2886a4e6f92bd7944ba8d2301d73",
    },
    {
        "id": "ref_92e3b080e4fe5ba58c7bf439251876a2",
        "name": "Mente",
        "source_text_checksum": "4ea538392992e57c9dc0224f46f40b51aaf78ebe1a029f67bfbe48b28f893b5b",
    },
    {
        "id": "ref_95407fdd26ae57e88fc3943545bd5cc4",
        "name": "Mago Trasmutatore",
        "source_text_checksum": "38c12e6bac483312455092a88e43c99107ac8eef1bb57c566e2957b7380cb862",
    },
    {
        "id": "ref_9675b27dfcf2508895f60fa16f372c25",
        "name": "Graz'Zt",
        "source_text_checksum": "09ab11db46773be1ea31bfd4e74bd90a2a9f79fcd0443e1f6cd6ef9afe66ffbe",
    },
    {
        "id": "ref_a2996e4f64235368b2f419b83e1a1aa3",
        "name": "Coboldo Stregone A Scaglie",
        "source_text_checksum": "f91892a56c6554a856e1dc621f8e1960c744220fd2430a0c9b73190981380bfb",
    },
    {
        "id": "ref_ab32494230d3599c84042660933cecf1",
        "name": "Dell'Ombra",
        "source_text_checksum": "b264b48ea1969c59a59bf4147a8a92d7dfc3dd64c534f04dd1095a30d865e1f6",
    },
    {
        "id": "ref_abaf4a8fe2395260991a96729a200351",
        "name": "Cacciatore Di Baphomet",
        "source_text_checksum": "94e2b86aa7bbd78a46dc484cf7e9b36b4290e38afea7d7ab7a8ac7dd152e93d1",
    },
    {
        "id": "ref_bb4edf45dab45e2a849aead637d922f7",
        "name": "Duergar Kavalracni",
        "source_text_checksum": "4c46e8046628ec6513bd94ce6e39db47b8785b3aebf8fc9af84dcb8378e9752a",
    },
    {
        "id": "ref_e0ed42b772a1564d8208dbee3557dae2",
        "name": "Mirmidone Elementale D'Aria",
        "source_text_checksum": "6a066bac120437f27ae5e6552ea6226a796e9dd8f9741f11f45b181a889581c3",
    },
    {
        "id": "ref_e35ab09f132e526292e86469507b55b0",
        "name": "Di Quercia",
        "source_text_checksum": "6b4bebe3fbc20186debbbc7cda213ef1754a05175af27d6e704f1f32304fe5f1",
    },
    {
        "id": "ref_e4ce5aac88725918a98e4f1dacc8cd1a",
        "name": "Githyanki Kith'Rak",
        "source_text_checksum": "15154d968982915f1aa1342e7f53ed67bd707e9c8c110b38dadfd64874217fbb",
    },
    {
        "id": "ref_f42275a1fc7956a88a2449eb3fc6d22d",
        "name": "Dell'Oscurità",
        "source_text_checksum": "933e922d521771cf049231668f6d4264875f3fba6e7de7110159087e17bc19f5",
    },
    {
        "id": "ref_fc9b6c580dc85c0a9ca6ec918192c216",
        "name": "Statua Sacra",
        "source_text_checksum": "194a9e65755a7efab06c3192afa0a1b606032a676a6fda9e495ab072d5304be2",
    },
)

EXPECTED_BIGBY19_COUNT = 19
EXPECTED_BIGBY19_IDS_MD5 = "16bfa1dc27d5d580b5c2703b5d7f1bf9"
BIGBY19_TARGETS: tuple[dict[str, str], ...] = (
    {
        "id": "ref_c106f9a6c3115dbf8578f832b04e3a3a",
        "name": "Altisauro",
        "source_text_checksum": "9680a14028c359d550587f69d890881a64731f0b51e30941476ff5e995debf2e",
    },
    {
        "id": "ref_28900cffd313554b81303ff3ce407cc1",
        "name": "Ammantato",
        "source_text_checksum": "b50cc4278a7fdd606f50a20f5b6f37d2fe4ce354094c8e2d60ffb73bd4e1e0e0",
    },
    {
        "id": "ref_5200eb51f6f555d5a52800dc3cfef0c4",
        "name": "Araldo Delle Tempeste",
        "source_text_checksum": "e64fd24af1656e2725f0ed425236226685a88d5dcc4df0a20ede61c7cb28279f",
    },
    {
        "id": "ref_e42d82c62c7b5bdba13c3c73663966ff",
        "name": "Cerato Po",
        "source_text_checksum": "a9365115d6e07317f75a602c6fcaea2d92e497e5c7c0a15cc8f273f452e0f2c3",
    },
    {
        "id": "ref_c2a7d3e06e52569e851f737c33260f9d",
        "name": "Colline",
        "source_text_checksum": "e66ab0e6fec743bc407b15e32a7d554927182e986521d5b4b09f274dade5c61f",
    },
    {
        "id": "ref_42d5121498575f11a310f549f441f4d7",
        "name": "Colosso Di Carne",
        "source_text_checksum": "827fb11acf989da9b32881d1ed85b4fcfd2570e8da0d72f70d6fede7e46d98a9",
    },
    {
        "id": "ref_83a6b991bfec5efdb2dda4da60d408bb",
        "name": "Colosso Runico",
        "source_text_checksum": "f1a8cbfb271853c0ec69468baa007afcabd94fe2bc0f5f68575028134c4494b5",
    },
    {
        "id": "ref_9ac0de67090652bdbe5e7fd1e01d00cb",
        "name": "Granchio Delle Tempeste",
        "source_text_checksum": "864505c5fc606dd81383ea6eae6395146e6ac5c9f94ca9ca41130acb2eaea9d0",
    },
    {
        "id": "ref_6d3eaf35463d556f961bbb7baa8d2b70",
        "name": "Ììtanoronte",
        "source_text_checksum": "a89571d106cf80b7d951673196b67f4929c609da73318cdae7c47ea64c193d5c",
    },
    {
        "id": "ref_c5f631a36b5f51dc9123a728f65c2ec9",
        "name": "Linguarupestre",
        "source_text_checksum": "9aee292abcf550f1a6e1abd97f366c0eaa793ee8b91b576132def21910e5c05f",
    },
    {
        "id": "ref_e965d3715ce456e1967dfdae85d0cdc3",
        "name": "Malvagia",
        "source_text_checksum": "aadc43f3446180bc087dbb0372b931d0ce9c7ea104edfa014ded112d89e263cc",
    },
    {
        "id": "ref_24fdfda426f35dc2b05cfdd7e17248d9",
        "name": "Malvagio",
        "source_text_checksum": "9e1b4b12e262e78a4fa258bd49be6a910ec257a8e6674499dbda98f0370d4b3b",
    },
    {
        "id": "ref_9b3fc6257b9f52819f603a4458318743",
        "name": "Mietitore",
        "source_text_checksum": "0417021c265927527cd35f5f88fd3e85a8fc03e3855a20e938aed407eb0ceaa1",
    },
    {
        "id": "ref_a4ca7d65762650dc8e24dcbde06a6342",
        "name": "Modellaghiaccio",
        "source_text_checksum": "0980bdaf9d426461e5666e89042b035985c551f66219878446fd7ca6621f0d4b",
    },
    {
        "id": "ref_1535557d71cd52849aba54a8418fbb2e",
        "name": "Pietre",
        "source_text_checksum": "351921045f55fdbc063e9e3cc7eeb315b908e7aba9e0bdafb93706abc56587ef",
    },
    {
        "id": "ref_77ef6b47608e5575b9723e8d11de2011",
        "name": "Regi Sauro",
        "source_text_checksum": "d30260741443c7f8d55c21df7cb772b46f4753f2a16da0b54816630bd1b676be",
    },
    {
        "id": "ref_8b550003f8045cc29a5edcfe9a6bce3b",
        "name": "Spirito Delle Tempeste",
        "source_text_checksum": "e28beb1d2d7a863ee680be953c36205b92fca6af2a24f77decc90c5988158399",
    },
    {
        "id": "ref_6b5c8da8abbf545e9f2ea14f88155b78",
        "name": "T'Erra Malvagia",
        "source_text_checksum": "6c01eae905b17ddbe67d9854820a8b6cbe88afb25525e7c7f63eb41763481ff4",
    },
    {
        "id": "ref_b0418fbbc1d85eaabb98d5891a4a45ab",
        "name": "Tempeste",
        "source_text_checksum": "e18c357eaea02487161d323745a1e06a55f440288eb633c4681da262cb570397",
    },
)

EXPECTED_APPROVED1_COUNT = 1
EXPECTED_APPROVED1_IDS_MD5 = "2bc07f76e1383e3d03b8cbdd644b3823"
APPROVED1_CONFIRMATION_TOKEN = "REPAIR-APPROVED1-1-2bc07f76e1383e3d03b8cbdd644b3823"
APPROVED1_TARGETS: tuple[dict[str, str], ...] = (
    {"id": "ref_36a7ca03ed43517b8b036334ea6d61ec", "name": "Abishai Rosso"},
)

EXPECTED_APPROVED5_COUNT = 5
EXPECTED_APPROVED5_IDS_MD5 = "413b398ac7e0c55dcd3b61eed14b66ef"
APPROVED5_CONFIRMATION_TOKEN = "REPAIR-APPROVED5-5-413b398ac7e0c55dcd3b61eed14b66ef"
APPROVED5_TARGETS: tuple[dict[str, str], ...] = (
    {
        "id": "ref_42d5121498575f11a310f549f441f4d7",
        "name": "Colosso Di Carne",
    },
    {
        "id": "ref_d3a9aeba19775d698d1dae2577086c2e",
        "name": "Di Terra",
    },
    {
        "id": "ref_b5a471157553590992c4b3af5c57deda",
        "name": "Fraz-Urb'Luu",
    },
    {
        "id": "ref_650f39bad9ac50c3a9d2ffcfde535f45",
        "name": "Lavamandra Warlock Di Imix",
    },
    {
        "id": "ref_a4ca7d65762650dc8e24dcbde06a6342",
        "name": "Modellaghiaccio",
    },
)

EXPECTED_OBLEX1_COUNT = 1
EXPECTED_OBLEX1_IDS_MD5 = "68e75df624874ee3cc9e3772fc9f34c0"
OBLEX1_CONFIRMATION_TOKEN = "REPAIR-OBLEX1-1-68e75df624874ee3cc9e3772fc9f34c0"
OBLEX1_TARGETS: tuple[dict[str, str], ...] = (
    {"id": "ref_2ea09533213a54178032bc4c5b0b952d", "name": "0Blex Antico"},
)

EXPECTED_READY6_COUNT = 6
EXPECTED_READY6_IDS_MD5 = "59e89d47077106ced525d5710408083d"
READY6_CONFIRMATION_TOKEN = "REPAIR-READY6-6-59e89d47077106ced525d5710408083d"
READY6_TARGETS: tuple[dict[str, str], ...] = (
    {
        "id": "ref_93a8b49f24dc5cfe957dfb9a24b24269",
        "name": "Mirmidone Elementale Dacqua",
    },
    {
        "id": "ref_4ae0befe0ab05648a78f846625ef39b5",
        "name": "Progenie Stellare Hulk",
    },
    {"id": "ref_77355e2e77585df9b6aaa8b42ca487af", "name": "Riportato Re"},
    {"id": "ref_6b5c8da8abbf545e9f2ea14f88155b78", "name": "T'Erra Malvagia"},
    {"id": "ref_5b8baa6ccbbb5191a0846187cafc5a82", "name": "T'Lincalli"},
    {"id": "ref_4ca8f4082f0c5721ace356f07fb8a756", "name": "Thstencefalo"},
)

EXPECTED_BIGBY4_COUNT = 4
EXPECTED_BIGBY4_IDS_MD5 = "82a891bb16d48d70e063b3c535fa0839"
BIGBY4_CONFIRMATION_TOKEN = "REPAIR-BIGBY4-4-82a891bb16d48d70e063b3c535fa0839"
BIGBY4_TARGETS: tuple[dict[str, str], ...] = (
    {
        "id": "ref_28900cffd313554b81303ff3ce407cc1",
        "name": "Ammantato",
        "source_text_checksum": "b50cc4278a7fdd606f50a20f5b6f37d2fe4ce354094c8e2d60ffb73bd4e1e0e0",
    },
    {
        "id": "ref_5200eb51f6f555d5a52800dc3cfef0c4",
        "name": "Araldo Delle Tempeste",
        "source_text_checksum": "e64fd24af1656e2725f0ed425236226685a88d5dcc4df0a20ede61c7cb28279f",
    },
    {
        "id": "ref_c5f631a36b5f51dc9123a728f65c2ec9",
        "name": "Linguarupestre",
        "source_text_checksum": "9aee292abcf550f1a6e1abd97f366c0eaa793ee8b91b576132def21910e5c05f",
    },
    {
        "id": "ref_8b550003f8045cc29a5edcfe9a6bce3b",
        "name": "Spirito Delle Tempeste",
        "source_text_checksum": "e28beb1d2d7a863ee680be953c36205b92fca6af2a24f77decc90c5988158399",
    },
)


# Known source families whose stat blocks are laid out in two vertical columns.
# Keep this explicit and source-guided: do not guess a layout from OCR output.
TWO_COLUMN_LOGICAL_SOURCE_IDS = {
    "mpmm_2022_it",  # Mordenkainen Presenta: Mostri del Multiverso
    "bgg_2023_it",  # Bigby Presenta: La Gloria dei Giganti
}
TWO_COLUMN_MIN_DPI = 300
TWO_COLUMN_PRIMARY_PSM = 3
TWO_COLUMN_COMPARISON_PSM = 4
HIT_POINTS_WHITELIST = "0123456789d+() "
HIT_POINTS_CONTRAST = 2.0
HIT_POINTS_FALLBACK_CONTRAST = 1.2
HIT_POINTS_FULL_SPECTRUM_THRESHOLDS = tuple(range(80, 201, 30))
HIT_POINTS_FULL_SPECTRUM_CONTRASTS = tuple(
    round(0.8 + step * 0.3, 1) for step in range(10)
)
HIT_POINTS_BACKGROUND_VARIANCE_THRESHOLD = 36.0
HIT_POINTS_BACKGROUND_MEAN_WHITE_THRESHOLD = 245.0
NONSTANDARD_MULTI_DIGIT_DIE_RE = re.compile(
    r"\([^)]*\b\d+d\d{3,4}\b[^)]*\)",
    re.IGNORECASE,
)


QUALITY_FAIL_PRE_OTSU_TARGETS = frozenset(
    {
        "Altisauro",
        "Bael",
        "Cerato Po",
        "Congreghe Di Megere",
        "Dimetrodonte",
        "Ippoaracne Maschio",
        "Larvico",
        "Molo Oh",
        "Rampollo Delle Profondità",
        "Ratto Cranico",
        "Regi Sauro",
        "Sciame Di Ratti Cranici",
        "Straziato Re",
        "Velociraptor",
    }
)


def _otsu_inverted_samples(samples: bytes) -> bytes:
    """Binarize grayscale samples with Otsu and invert to white-on-black."""
    if not samples:
        return b""
    histogram = [0] * 256
    for sample in samples:
        histogram[sample] += 1

    total = len(samples)
    weighted_total = sum(value * count for value, count in enumerate(histogram))
    background_weight = 0
    background_sum = 0
    best_variance = -1.0
    threshold = 0
    for value, count in enumerate(histogram):
        background_weight += count
        if background_weight == 0:
            continue
        foreground_weight = total - background_weight
        if foreground_weight == 0:
            break
        background_sum += value * count
        background_mean = background_sum / background_weight
        foreground_mean = (weighted_total - background_sum) / foreground_weight
        between_variance = (
            background_weight
            * foreground_weight
            * (background_mean - foreground_mean) ** 2
        )
        if between_variance > best_variance:
            best_variance = between_variance
            threshold = value

    return bytes(255 if sample <= threshold else 0 for sample in samples)


def _local_adaptive_inverted_samples(
    samples: bytes,
    width: int,
    height: int,
    *,
    window_size: int = 15,
    bias: int = 7,
) -> bytes:
    """Local mean threshold with a bounded 15x15 window, white text on black."""
    if width < 1 or height < 1 or len(samples) != width * height:
        raise ValueError("invalid grayscale raster for adaptive threshold")
    if window_size < 3 or window_size % 2 == 0:
        raise ValueError("adaptive threshold window must be odd and >= 3")

    stride = width + 1
    integral = [0] * ((height + 1) * stride)
    for y in range(height):
        row_sum = 0
        source_offset = y * width
        integral_offset = (y + 1) * stride
        previous_offset = y * stride
        for x in range(width):
            row_sum += samples[source_offset + x]
            integral[integral_offset + x + 1] = (
                integral[previous_offset + x + 1] + row_sum
            )

    radius = window_size // 2
    output = bytearray(len(samples))
    for y in range(height):
        y0 = max(0, y - radius)
        y1 = min(height, y + radius + 1)
        for x in range(width):
            x0 = max(0, x - radius)
            x1 = min(width, x + radius + 1)
            area = (x1 - x0) * (y1 - y0)
            total = (
                integral[y1 * stride + x1]
                - integral[y0 * stride + x1]
                - integral[y1 * stride + x0]
                + integral[y0 * stride + x0]
            )
            local_mean = total / area
            output[y * width + x] = (
                255 if samples[y * width + x] < local_mean - bias else 0
            )
    return bytes(output)


def _remove_isolated_foreground_noise(
    samples: bytes,
    width: int,
    height: int,
) -> bytes:
    """Remove one-pixel white foreground components without altering glyph clusters."""
    if width < 1 or height < 1 or len(samples) != width * height:
        raise ValueError("invalid bitonal raster for denoising")
    output = bytearray(samples)
    for y in range(height):
        for x in range(width):
            index = y * width + x
            if samples[index] == 0:
                continue
            connected = False
            for yy in range(max(0, y - 1), min(height, y + 2)):
                for xx in range(max(0, x - 1), min(width, x + 2)):
                    if (xx != x or yy != y) and samples[yy * width + xx] != 0:
                        connected = True
                        break
                if connected:
                    break
            if not connected:
                output[index] = 0
    return bytes(output)


def _pre_otsu_column_clean(image_path: Path) -> None:
    """Superscale x4, locally threshold, then remove isolated visual noise."""
    import fitz

    source = fitz.Pixmap(str(image_path))
    grayscale = fitz.Pixmap(fitz.csGRAY, source)
    # MuPDF's Pixmap resampler provides the high-fidelity native interpolation
    # already used by the bounded OCR fallbacks; superscale before thresholding.
    superscaled = fitz.Pixmap(
        grayscale,
        grayscale.width * 4,
        grayscale.height * 4,
    )
    adaptive = _local_adaptive_inverted_samples(
        superscaled.samples,
        superscaled.width,
        superscaled.height,
        window_size=15,
    )
    denoised = _remove_isolated_foreground_noise(
        adaptive,
        superscaled.width,
        superscaled.height,
    )
    cleaned = fitz.Pixmap(
        fitz.csGRAY,
        superscaled.width,
        superscaled.height,
        denoised,
        False,
    )
    cleaned.save(image_path)


def _dilate_dark_pixels(samples: bytes, width: int, height: int) -> bytes:
    """Apply a bounded 3x3 minimum filter to strengthen dark text strokes."""
    if width < 1 or height < 1 or len(samples) != width * height:
        raise ValueError("invalid grayscale raster for dark-pixel dilation")
    output = bytearray(len(samples))
    for y in range(height):
        y0 = max(0, y - 1)
        y1 = min(height, y + 2)
        for x in range(width):
            x0 = max(0, x - 1)
            x1 = min(width, x + 2)
            output[y * width + x] = min(
                samples[row * width + column]
                for row in range(y0, y1)
                for column in range(x0, x1)
            )
    return bytes(output)


def _erode_dark_pixels(samples: bytes, width: int, height: int) -> bytes:
    """Apply a bounded 3x3 maximum filter to thin fused dark strokes."""
    if width < 1 or height < 1 or len(samples) != width * height:
        raise ValueError("invalid grayscale raster for dark-pixel erosion")
    output = bytearray(len(samples))
    for y in range(height):
        y0 = max(0, y - 1)
        y1 = min(height, y + 2)
        for x in range(width):
            x0 = max(0, x - 1)
            x1 = min(width, x + 2)
            output[y * width + x] = max(
                samples[row * width + column]
                for row in range(y0, y1)
                for column in range(x0, x1)
            )
    return bytes(output)


def _sample_variance(samples: bytes) -> float:
    """Return grayscale variance without external image dependencies."""
    if not samples:
        return 0.0
    mean = sum(samples) / len(samples)
    return sum((sample - mean) ** 2 for sample in samples) / len(samples)


def _background_luminance_stats(
    samples: bytes,
    width: int,
    height: int,
) -> tuple[float, float]:
    """Estimate crop background from a bounded outer frame.

    The frame is intentionally narrow so the decision is driven mostly by the
    paper/background surrounding the dice text rather than by glyph pixels.
    """
    if width < 1 or height < 1 or len(samples) != width * height:
        raise ValueError("invalid grayscale raster for background statistics")
    edge_x = max(1, min(width // 8, 12))
    edge_y = max(1, min(height // 6, 8))
    border = bytearray()
    for y in range(height):
        for x in range(width):
            if x < edge_x or x >= width - edge_x or y < edge_y or y >= height - edge_y:
                border.append(samples[y * width + x])
    if not border:
        border.extend(samples)
    mean = sum(border) / len(border)
    variance = _sample_variance(bytes(border))
    return mean, variance


# Explicitly reviewed legacy upload aliases. Resolution is still accepted only
# if the destination registry row is active and authority/ingest_copy.
LEGACY_FILENAME_ALIASES = {
    "Calderone-Omnicomprensivo-di-TASHA_1787259976040.pdf": "Calderone-Omnicomprensivo-di-TASHA.pdf",
    "724962906-D-D-5e-Manuale-Del-Dungeon-Master_1787282954664.pdf": "724962906-D-D-5e-Manuale-Del-Dungeon-Master.pdf",
    "Manuale_del_giocatore__1787259882002.pdf": "Manuale del giocatore .pdf",
    # Diagnostics only: the registry currently classifies this extraction_aid,
    # therefore repair is blocked by the source-role gate.
    "731764731-D-D-Manual-Del-Jugador-5e_1787286581630.pdf": "731764731-D-D-Manual-Del-Jugador-5e(1).pdf",
}


class RepairBlocked(RuntimeError):
    """Expected fail-closed outcome for a record that is unsafe to repair."""

    def __init__(
        self,
        reason: str,
        detail: str = "",
        diagnostics: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(detail or reason)
        self.reason = reason
        self.detail = detail or reason
        self.diagnostics = diagnostics


async def _fetch_all(collection: Any, query: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    offset = 0
    while True:
        page = await collection.find(query).to_list(PAGE_SIZE, offset=offset)
        rows.extend(page)
        if len(page) < PAGE_SIZE:
            return rows
        offset += len(page)


def _legacy_failure_flags(record: dict[str, Any]) -> set[str]:
    """Return current failure flags, including identity only for numeric failures."""
    if str(record.get("reference_type") or "") != "monster":
        return set()
    title_flags = entity_name_semantic_flags(record.get("name"))
    if title_flags:
        return title_flags
    numeric_flags = monster_semantic_numeric_flags(record.get("attributes") or {})
    if not numeric_flags:
        return set()
    return numeric_flags | monster_identity_sanity_flags(record.get("name"))


def _record_sort_key(record: dict[str, Any]) -> tuple[str, str]:
    return (
        str(record.get("name") or "").casefold(),
        str(record.get("id") or ""),
    )


def select_failed_monsters(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Select failed monsters whose identity is safe enough for source repair."""
    selected = []
    for record in records:
        flags = _legacy_failure_flags(record)
        if not flags:
            continue
        if INVALID_ENTITY_TITLE_FLAG in flags:
            continue
        if CORRUPTED_ENTITY_NAME_FLAG in flags:
            continue
        selected.append(record)
    return sorted(selected, key=_record_sort_key)


def select_corrupted_name_monsters(
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Isolate numerically failed monsters whose names look like OCR debris."""
    selected = []
    for record in records:
        flags = _legacy_failure_flags(record)
        if (
            CORRUPTED_ENTITY_NAME_FLAG in flags
            and INVALID_ENTITY_TITLE_FLAG not in flags
        ):
            selected.append(record)
    return sorted(selected, key=_record_sort_key)


def _ids_md5(records: list[dict[str, Any]] | tuple[dict[str, Any], ...]) -> str:
    joined = ",".join(sorted(str(record["id"]) for record in records))
    return hashlib.md5(
        joined.encode("utf-8"),
        usedforsecurity=False,
    ).hexdigest()


def select_residual_batch_targets(
    failures: list[dict[str, Any]],
    target_set: str,
) -> list[dict[str, Any]]:
    """Resolve one sealed residual dry-run batch by exact ID/name fingerprint."""
    expected_targets = RESIDUAL_BATCH_TARGETS[target_set]
    by_id = {str(record.get("id") or ""): record for record in failures}
    targets: list[dict[str, Any]] = []
    for expected in expected_targets:
        record = by_id.get(expected["id"])
        if record is None:
            raise RuntimeError(
                f"Sealed {target_set} target missing from current failures: {expected['id']}"
            )
        if str(record.get("name") or "") != expected["name"]:
            raise RuntimeError(f"{target_set} name drift: {expected['id']}")
        if str(record.get("review_status") or "") != "verified":
            raise RuntimeError(f"{target_set} status drift: {expected['id']}")
        if record.get("canonical_id"):
            raise RuntimeError(
                f"{target_set} canonical link detected: {expected['id']}"
            )
        targets.append(record)

    if (
        len(targets) != EXPECTED_RESIDUAL_BATCH_COUNTS[target_set]
        or _ids_md5(targets) != EXPECTED_RESIDUAL_BATCH_IDS_MD5[target_set]
    ):
        raise RuntimeError(f"{target_set} target count/fingerprint drift")
    return targets


def select_healthy22_targets(
    failures: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Resolve the reviewed 22-row batch by exact sealed identity."""
    by_id = {str(record.get("id") or ""): record for record in failures}
    targets: list[dict[str, Any]] = []
    for expected in HEALTHY22_TARGETS:
        record = by_id.get(expected["id"])
        if record is None:
            raise RuntimeError(
                f"Sealed healthy22 target missing from current failures: {expected['id']}"
            )
        if str(record.get("name") or "") != expected["name"]:
            raise RuntimeError(f"Healthy22 name drift: {expected['id']}")
        if (
            str(record.get("source_text_checksum") or "")
            != expected["source_text_checksum"]
        ):
            raise RuntimeError(f"Healthy22 checksum drift: {expected['id']}")
        if str(record.get("review_status") or "") != "verified":
            raise RuntimeError(f"Healthy22 status drift: {expected['id']}")
        if record.get("canonical_id"):
            raise RuntimeError(f"Healthy22 canonical link detected: {expected['id']}")
        if list(record.get("review_flags") or []):
            raise RuntimeError(
                f"Healthy22 unexpected pre-existing review flags: {expected['id']}"
            )
        if monster_identity_sanity_flags(record.get("name")):
            raise RuntimeError(f"Healthy22 identity gate failure: {expected['id']}")
        targets.append(record)

    if (
        len(targets) != EXPECTED_HEALTHY22_COUNT
        or _ids_md5(targets) != EXPECTED_HEALTHY22_IDS_MD5
    ):
        raise RuntimeError("Healthy22 target count/fingerprint drift")
    return targets


def select_bigby19_targets(
    failures: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Resolve the 19 reviewed Bigby disagreement rows for dry-run audit only."""
    by_id = {str(record.get("id") or ""): record for record in failures}
    targets: list[dict[str, Any]] = []
    for expected in BIGBY19_TARGETS:
        record = by_id.get(expected["id"])
        if record is None:
            raise RuntimeError(
                f"Sealed bigby19 target missing from current failures: {expected['id']}"
            )
        if str(record.get("name") or "") != expected["name"]:
            raise RuntimeError(f"Bigby19 name drift: {expected['id']}")
        if (
            str(record.get("source_text_checksum") or "")
            != expected["source_text_checksum"]
        ):
            raise RuntimeError(f"Bigby19 checksum drift: {expected['id']}")
        if str(record.get("review_status") or "") != "verified":
            raise RuntimeError(f"Bigby19 status drift: {expected['id']}")
        if record.get("canonical_id"):
            raise RuntimeError(f"Bigby19 canonical link detected: {expected['id']}")
        if list(record.get("review_flags") or []):
            raise RuntimeError(
                f"Bigby19 unexpected pre-existing review flags: {expected['id']}"
            )
        targets.append(record)

    if (
        len(targets) != EXPECTED_BIGBY19_COUNT
        or _ids_md5(targets) != EXPECTED_BIGBY19_IDS_MD5
    ):
        raise RuntimeError("Bigby19 target count/fingerprint drift")
    return targets


def select_approved1_targets(failures: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Resolve the sole identity with coherent core numerics by sealed identity."""
    by_id = {str(record.get("id") or ""): record for record in failures}
    targets: list[dict[str, Any]] = []
    for expected in APPROVED1_TARGETS:
        record = by_id.get(expected["id"])
        if record is None:
            raise RuntimeError(f"Sealed approved1 target missing: {expected['id']}")
        if str(record.get("name") or "") != expected["name"]:
            raise RuntimeError(f"Approved1 name drift: {expected['id']}")
        if str(record.get("review_status") or "") != "verified":
            raise RuntimeError(f"Approved1 status drift: {expected['id']}")
        if list(record.get("review_flags") or []):
            raise RuntimeError(f"Approved1 review flag drift: {expected['id']}")
        if record.get("canonical_id"):
            raise RuntimeError(f"Approved1 canonical link detected: {expected['id']}")
        if not str(record.get("source_text_checksum") or ""):
            raise RuntimeError(f"Approved1 checksum missing: {expected['id']}")
        if monster_identity_sanity_flags(record.get("name")):
            raise RuntimeError(f"Approved1 identity gate failure: {expected['id']}")
        targets.append(record)
    if (
        len(targets) != EXPECTED_APPROVED1_COUNT
        or _ids_md5(targets) != EXPECTED_APPROVED1_IDS_MD5
    ):
        raise RuntimeError("Approved1 target count/fingerprint drift")
    return targets


def select_approved5_targets(failures: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Resolve the five gate-clean repairs by exact sealed live identity."""
    by_id = {str(record.get("id") or ""): record for record in failures}
    targets: list[dict[str, Any]] = []
    for expected in APPROVED5_TARGETS:
        record = by_id.get(expected["id"])
        if record is None:
            raise RuntimeError(f"Sealed approved5 target missing: {expected['id']}")
        if str(record.get("name") or "") != expected["name"]:
            raise RuntimeError(f"Approved5 name drift: {expected['id']}")
        if str(record.get("review_status") or "") != "verified":
            raise RuntimeError(f"Approved5 status drift: {expected['id']}")
        if list(record.get("review_flags") or []):
            raise RuntimeError(f"Approved5 review flag drift: {expected['id']}")
        if record.get("canonical_id"):
            raise RuntimeError(f"Approved5 canonical link detected: {expected['id']}")
        if not str(record.get("source_text_checksum") or ""):
            raise RuntimeError(f"Approved5 checksum missing: {expected['id']}")
        if monster_identity_sanity_flags(record.get("name")):
            raise RuntimeError(f"Approved5 identity gate failure: {expected['id']}")
        targets.append(record)
    if (
        len(targets) != EXPECTED_APPROVED5_COUNT
        or _ids_md5(targets) != EXPECTED_APPROVED5_IDS_MD5
    ):
        raise RuntimeError("Approved5 target count/fingerprint drift")
    return targets


def select_oblex1_targets(failures: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Resolve the sole overlap-proven Oblex repair by sealed live identity."""
    by_id = {str(record.get("id") or ""): record for record in failures}
    targets: list[dict[str, Any]] = []
    for expected in OBLEX1_TARGETS:
        record = by_id.get(expected["id"])
        if record is None:
            raise RuntimeError(f"Sealed oblex1 target missing: {expected['id']}")
        if str(record.get("name") or "") != expected["name"]:
            raise RuntimeError(f"Oblex1 name drift: {expected['id']}")
        if str(record.get("review_status") or "") != "verified":
            raise RuntimeError(f"Oblex1 status drift: {expected['id']}")
        if list(record.get("review_flags") or []):
            raise RuntimeError(f"Oblex1 review flag drift: {expected['id']}")
        if record.get("canonical_id"):
            raise RuntimeError(f"Oblex1 canonical link detected: {expected['id']}")
        if not str(record.get("source_text_checksum") or ""):
            raise RuntimeError(f"Oblex1 checksum missing: {expected['id']}")
        targets.append(record)
    if (
        len(targets) != EXPECTED_OBLEX1_COUNT
        or _ids_md5(targets) != EXPECTED_OBLEX1_IDS_MD5
    ):
        raise RuntimeError("Oblex1 target count/fingerprint drift")
    return targets


def select_ready6_targets(failures: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Resolve the six newly gate-clean rows by exact sealed live identity."""
    by_id = {str(record.get("id") or ""): record for record in failures}
    targets: list[dict[str, Any]] = []
    for expected in READY6_TARGETS:
        record = by_id.get(expected["id"])
        if record is None:
            raise RuntimeError(f"Sealed ready6 target missing: {expected['id']}")
        if str(record.get("name") or "") != expected["name"]:
            raise RuntimeError(f"Ready6 name drift: {expected['id']}")
        if str(record.get("review_status") or "") != "verified":
            raise RuntimeError(f"Ready6 status drift: {expected['id']}")
        if list(record.get("review_flags") or []):
            raise RuntimeError(f"Ready6 review flag drift: {expected['id']}")
        if record.get("canonical_id"):
            raise RuntimeError(f"Ready6 canonical link detected: {expected['id']}")
        if not str(record.get("source_text_checksum") or ""):
            raise RuntimeError(f"Ready6 checksum missing: {expected['id']}")
        if monster_identity_sanity_flags(record.get("name")):
            raise RuntimeError(f"Ready6 identity gate failure: {expected['id']}")
        targets.append(record)
    if (
        len(targets) != EXPECTED_READY6_COUNT
        or _ids_md5(targets) != EXPECTED_READY6_IDS_MD5
    ):
        raise RuntimeError("Ready6 target count/fingerprint drift")
    return targets


def select_bigby4_targets(
    failures: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Resolve the four approved Bigby repair rows by exact sealed identity."""
    by_id = {str(record.get("id") or ""): record for record in failures}
    targets: list[dict[str, Any]] = []
    for expected in BIGBY4_TARGETS:
        record = by_id.get(expected["id"])
        if record is None:
            raise RuntimeError(
                f"Sealed bigby4 target missing from current failures: {expected['id']}"
            )
        if str(record.get("name") or "") != expected["name"]:
            raise RuntimeError(f"Bigby4 name drift: {expected['id']}")
        if (
            str(record.get("source_text_checksum") or "")
            != expected["source_text_checksum"]
        ):
            raise RuntimeError(f"Bigby4 checksum drift: {expected['id']}")
        if str(record.get("review_status") or "") != "verified":
            raise RuntimeError(f"Bigby4 status drift: {expected['id']}")
        if record.get("canonical_id"):
            raise RuntimeError(f"Bigby4 canonical link detected: {expected['id']}")
        if list(record.get("review_flags") or []):
            raise RuntimeError(
                f"Bigby4 unexpected pre-existing review flags: {expected['id']}"
            )
        if monster_identity_sanity_flags(record.get("name")):
            raise RuntimeError(f"Bigby4 identity gate failure: {expected['id']}")
        targets.append(record)

    if (
        len(targets) != EXPECTED_BIGBY4_COUNT
        or _ids_md5(targets) != EXPECTED_BIGBY4_IDS_MD5
    ):
        raise RuntimeError("Bigby4 target count/fingerprint drift")
    return targets


async def _revalidate_target_snapshots(
    collection: Any,
    originals: list[dict[str, Any]],
) -> None:
    """Abort the batch if any reviewed target changed while OCR was running."""
    protected_fields = (
        "name",
        "reference_type",
        "attributes",
        "review_flags",
        "review_status",
        "source_refs",
        "source_text_checksum",
        "canonical_id",
        "updated_at",
    )
    for original in originals:
        current = await collection.find_one({"id": str(original["id"])})
        if current is None:
            raise RuntimeError(f"Sealed target disappeared: {original['id']}")
        for field in protected_fields:
            if current.get(field) != original.get(field):
                raise RuntimeError(
                    f"Sealed target concurrent drift for {original['id']}: {field}"
                )


def _first_source_ref(record: dict[str, Any]) -> dict[str, Any]:
    refs = record.get("source_refs") or []
    for ref in refs:
        if isinstance(ref, dict) and ref.get("page") is not None:
            return ref
    raise RepairBlocked(
        "missing_source_ref",
        "Record has no source_ref with a physical page",
    )


def _legacy_filename(record: dict[str, Any], ref: dict[str, Any]) -> str:
    return str(ref.get("filename") or record.get("source_key") or "").strip()


def resolve_source(
    record: dict[str, Any],
    active_sources: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Resolve legacy provenance to one active registry row, fail-closed."""
    ref = _first_source_ref(record)
    legacy_filename = _legacy_filename(record, ref)
    if not legacy_filename:
        raise RepairBlocked("missing_source_filename")

    candidate_filename = LEGACY_FILENAME_ALIASES.get(
        legacy_filename,
        legacy_filename,
    )
    candidates = [
        source
        for source in active_sources
        if str(source.get("physical_filename") or "") == candidate_filename
    ]
    if len(candidates) != 1:
        raise RepairBlocked(
            "source_resolution_required",
            f"Expected one active registry source for "
            f"{candidate_filename!r}; got {len(candidates)}",
        )

    source = candidates[0]
    role = str(source.get("source_role") or "")
    if role not in ELIGIBLE_SOURCE_ROLES:
        raise RepairBlocked(
            "source_ineligible_role",
            f"Resolved source_role={role!r}",
        )
    if str(source.get("source_status") or "") != "active":
        raise RepairBlocked("source_not_active")

    page = int(ref.get("page") or 0)
    page_total = int(source.get("physical_pages") or 0)
    if page < 1 or page_total < 1 or page > page_total:
        raise RepairBlocked(
            "source_page_out_of_bounds",
            f"page={page}, physical_pages={page_total}",
        )
    return source, ref


def _layout_profile(source: dict[str, Any]) -> str:
    logical_source_id = str(source.get("logical_source_id") or "").strip()
    if logical_source_id in TWO_COLUMN_LOGICAL_SOURCE_IDS:
        return "two_column_vertical"
    return "full_page"


def _layout_segments(
    source: dict[str, Any],
    *,
    overlap_fraction: float = 0.02,
) -> tuple[tuple[str, tuple[float, float, float, float]], ...]:
    """Return normalized page clips; values are fractions of width/height."""
    if _layout_profile(source) == "two_column_vertical":
        if not 0.02 <= overlap_fraction <= 0.05:
            raise ValueError("column overlap must be between 2% and 5%")
        # The default 2% center overlap is about 40-50 raster pixels on the
        # supported legacy pages at 300 DPI. Identity-miss retries may expand
        # it up to 5%; clips remain page-bounded and duplicate candidates still
        # fail the unique independent-agreement gate.
        return (
            ("left", (0.0, 0.0, 0.5 + overlap_fraction, 1.0)),
            ("right", (0.5 - overlap_fraction, 0.0, 1.0, 1.0)),
        )
    return (("full", (0.0, 0.0, 1.0, 1.0)),)


def _layout_ocr_settings(
    source: dict[str, Any],
    *,
    dpi: int,
    psm: int,
    comparison_psm: int,
) -> tuple[int, int, int]:
    """Return (dpi, primary_psm, comparison_psm) for the resolved source."""
    if _layout_profile(source) == "two_column_vertical":
        # At 300 DPI PSM 3 and PSM 4 independently preserve compact dice tokens
        # in the MP:MM stat-block font while still using distinct page analysis.
        return (
            max(dpi, TWO_COLUMN_MIN_DPI),
            TWO_COLUMN_PRIMARY_PSM,
            TWO_COLUMN_COMPARISON_PSM,
        )
    return dpi, psm, comparison_psm


def _should_retry_dynamic_layout(exc: RepairBlocked, source: dict[str, Any]) -> bool:
    """Retry wider column clips only when target identity was absent in OCR."""
    if exc.reason != "no_unique_independent_agreement":
        return False
    if _layout_profile(source) != "two_column_vertical":
        return False
    diagnostics = exc.diagnostics or {}
    return bool(
        diagnostics.get("primary_name_candidates") == 0
        or diagnostics.get("comparison_name_candidates") == 0
    )


def _sparse_anchor_matches(page_text: str, target_name: str) -> bool:
    """Confirm that a PSM 11 page pass contains the compact target identity."""
    target = normalize_reference_name(target_name).replace(" ", "")
    page = normalize_reference_name(page_text).replace(" ", "")
    return bool(target and target in page)


def _sparse_anchor_crop_fractions(
    image_path: Path,
    languages: str,
    target_name: str,
) -> tuple[float, float, float, float] | None:
    """Locate one unique PSM11 title anchor and return a target-column crop.

    This is geometric evidence only. It never supplies values to the parser.
    Multiple or absent anchors fail closed.
    """
    import fitz

    command = [
        "tesseract",
        str(image_path),
        "stdout",
        "-l",
        languages,
        "--psm",
        "11",
        "tsv",
        "quiet",
    ]
    completed = subprocess.run(
        command,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=120,
    )
    rows = list(csv.DictReader(io.StringIO(completed.stdout), delimiter="\t"))
    grouped: dict[tuple[str, str, str, str], list[dict[str, str]]] = {}
    for row in rows:
        if str(row.get("text") or "").strip():
            key = tuple(
                str(row.get(field) or "")
                for field in ("page_num", "block_num", "par_num", "line_num")
            )
            grouped.setdefault(key, []).append(row)

    matches: list[list[dict[str, str]]] = []
    for words in grouped.values():
        text = " ".join(str(word.get("text") or "") for word in words).strip()
        if _sparse_anchor_matches(text, target_name):
            matches.append(words)
    if len(matches) != 1:
        print(
            "SPARSE_ANCHOR_GEOMETRY "
            + json.dumps(
                {
                    "name": target_name,
                    "matching_title_lines": len(matches),
                    "accepted": False,
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return None

    words = matches[0]
    left = min(int(word["left"]) for word in words)
    right = max(int(word["left"]) + int(word["width"]) for word in words)
    top = min(int(word["top"]) for word in words)
    bottom = max(int(word["top"]) + int(word["height"]) for word in words)
    pixmap = fitz.Pixmap(str(image_path))
    width = max(1, pixmap.width)
    height = max(1, pixmap.height)
    center_x = (left + right) / 2.0

    # The sparse retry is used after two-column layout retries are exhausted.
    # Recenter around the half-page containing the unique title, while keeping
    # a conservative 8% center overlap and all content below the title.
    if center_x < width / 2.0:
        x0, x1 = 0.0, 0.58
    else:
        x0, x1 = 0.42, 1.0
    title_height = max(1, bottom - top)
    y0_pixels = max(0, top - max(title_height * 2, int(height * 0.015)))
    fractions = (x0, y0_pixels / height, x1, 1.0)
    print(
        "SPARSE_ANCHOR_GEOMETRY "
        + json.dumps(
            {
                "name": target_name,
                "matching_title_lines": 1,
                "accepted": True,
                "anchor_bbox_px": [left, top, right, bottom],
                "crop_fractions": list(fractions),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return fractions


class SourcePdfCache:
    """Resolve exact registry PDFs locally; optional R2 fallback is explicit."""

    def __init__(self, pdf_root: str, allow_r2_download: bool) -> None:
        self.pdf_root = Path(pdf_root).expanduser() if pdf_root else None
        self.allow_r2_download = allow_r2_download
        self._tmp = tempfile.TemporaryDirectory(prefix="tomoforge-source-repair-")
        self._cache: dict[str, Path] = {}

    def close(self) -> None:
        self._tmp.cleanup()

    def _verify(self, path: Path, source: dict[str, Any]) -> Path:
        expected = str(source.get("physical_sha256") or "").strip().casefold()
        if not re.fullmatch(r"[0-9a-f]{64}", expected):
            raise RepairBlocked("missing_registry_sha256")
        actual = _sha256_file(path)
        if actual != expected:
            raise RepairBlocked(
                "source_sha256_mismatch",
                f"expected={expected} actual={actual}",
            )
        return path

    def get(self, source: dict[str, Any]) -> Path:
        filename = str(source.get("physical_filename") or "")
        if not filename:
            raise RepairBlocked("missing_registry_filename")
        if filename in self._cache:
            return self._cache[filename]

        if self.pdf_root is not None:
            local = self.pdf_root / filename
            if local.is_file():
                self._cache[filename] = self._verify(local, source)
                return self._cache[filename]

        if not self.allow_r2_download:
            raise RepairBlocked(
                "source_pdf_not_local",
                f"{filename!r} not found under --pdf-root and R2 fallback is disabled",
            )

        from scripts import import_manuals_from_r2 as r2_worker

        client = r2_worker._r2_client()
        bucket = (
            os.getenv("R2_BUCKET", "tomoforge-manuals").strip() or "tomoforge-manuals"
        )
        objects = r2_worker._list_pdf_objects(client, bucket)
        safe_name = r2_worker._safe_pdf_name(filename)
        metadata = objects.get(safe_name)
        if metadata is None:
            # Registry metadata stores the canonical source identity, while R2
            # may retain one explicitly registered upload alias. Resolve only
            # aliases that canonicalize to this exact filename; the downloaded
            # bytes must still pass the registry SHA-256 gate below.
            from reference_sources import (
                SOURCE_FILENAME_ALIASES,
                canonical_physical_filename,
            )

            alias_names = sorted(
                alias
                for alias, canonical in SOURCE_FILENAME_ALIASES.items()
                if canonical == canonical_physical_filename(filename)
                and alias in objects
            )
            if len(alias_names) > 1:
                raise RepairBlocked(
                    "source_pdf_ambiguous_r2_alias",
                    f"matching registered aliases={len(alias_names)}",
                )
            if alias_names:
                safe_name = alias_names[0]
                metadata = objects[safe_name]
        if metadata is None:
            raise RepairBlocked("source_pdf_missing_r2", safe_name)

        target = Path(self._tmp.name) / safe_name
        client.download_file(bucket, metadata["key"], str(target))
        self._cache[filename] = self._verify(target, source)
        return self._cache[filename]


def _clip_rect(
    page_rect: Any,
    fractions: tuple[float, float, float, float],
) -> Any:
    """Convert normalized clip fractions to a fitz.Rect."""
    import fitz

    x0, y0, x1, y1 = fractions
    return fitz.Rect(
        page_rect.x0 + page_rect.width * x0,
        page_rect.y0 + page_rect.height * y0,
        page_rect.x0 + page_rect.width * x1,
        page_rect.y0 + page_rect.height * y1,
    )


def _micro_ocr_hit_points_line(
    image_path: Path,
    languages: str,
    psm: int,
    page_text: str,
    name: str,
) -> str:
    """Re-OCR only the numeric part of the PF line with a strict whitelist.

    The ordinary segment OCR is retained for every other field. Tesseract TSV
    coordinates let us find the target monster first and then crop immediately
    after the first ``Punti Ferita`` label below it. This prevents a different
    stat block on the same segment from supplying the core HP evidence. The
    whitelist cannot remove or alter surrounding stat-block content.
    """
    import fitz

    diagnostics: dict[str, object] = {
        "page_text_target_count": None,
        "page_text_local_hp_count": None,
        "tsv_page_wide_hp_label_count": None,
        "tsv_name_anchor_found": None,
        "tsv_local_label_found": None,
    }

    def fail_closed(reason: str) -> str:
        print(
            "HP_ANCHOR_DIAGNOSTIC "
            + json.dumps(
                {"name": name, "reason": reason, **diagnostics},
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return page_text

    hp_line_pattern = re.compile(
        r"^(?P<label>[ \t]*Punti[ \t]+Ferita[ \t]*)(?P<value>.*)$",
        re.IGNORECASE | re.MULTILINE,
    )
    if not hp_line_pattern.search(page_text):
        diagnostics["page_text_local_hp_count"] = 0
        return fail_closed("page_text_hp_label_missing")

    command = [
        "tesseract",
        str(image_path),
        "stdout",
        "-l",
        languages,
        "--psm",
        str(psm),
        "tsv",
        "quiet",
    ]
    completed = subprocess.run(
        command,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=120,
    )
    rows = list(csv.DictReader(io.StringIO(completed.stdout), delimiter="\t"))
    grouped: dict[tuple[str, str, str, str], list[dict[str, str]]] = {}
    for row in rows:
        if str(row.get("text") or "").strip():
            key = tuple(
                str(row.get(field) or "")
                for field in ("page_num", "block_num", "par_num", "line_num")
            )
            grouped.setdefault(key, []).append(row)

    ordered_lines = sorted(
        grouped.values(),
        key=lambda words: (
            min(int(word["top"]) for word in words),
            min(int(word["left"]) for word in words),
        ),
    )
    normalized_name = normalize_reference_name(name).replace(" ", "")
    if not normalized_name:
        diagnostics["page_text_target_count"] = 0
        return fail_closed("normalized_target_name_empty")

    def page_text_anchor_counts() -> tuple[int, int]:
        text_lines = page_text.splitlines()
        target_indexes = [
            index
            for index, line in enumerate(text_lines)
            if normalized_name in normalize_reference_name(line).replace(" ", "")
        ]
        if len(target_indexes) != 1:
            return len(target_indexes), 0
        target_index = target_indexes[0]
        hp_indexes = [
            index
            for index, line in enumerate(
                text_lines[target_index + 1 : target_index + 13],
                start=target_index + 1,
            )
            if re.search(r"\bPunti\s+Ferita\b", line, re.IGNORECASE)
        ]
        return len(target_indexes), len(hp_indexes)

    def page_wide_tsv_labels() -> list[list[dict[str, str]]]:
        labels: list[list[dict[str, str]]] = []
        for index, words in enumerate(ordered_lines):
            normalized = " ".join(str(word["text"]) for word in words).casefold()
            if "punti" not in normalized:
                continue
            if "ferita" in normalized:
                labels.append(words)
                continue
            for following in ordered_lines[index + 1 : index + 3]:
                following_text = " ".join(
                    str(word["text"]) for word in following
                ).casefold()
                vertical_gap = min(int(word["top"]) for word in following) - max(
                    int(word["top"]) + int(word["height"]) for word in words
                )
                if "ferita" in following_text and 0 <= vertical_gap <= 20:
                    labels.append(
                        words + [word for word in following if word not in words]
                    )
                    break
        return labels

    page_target_count, page_local_hp_count = page_text_anchor_counts()
    diagnostics["page_text_target_count"] = page_target_count
    diagnostics["page_text_local_hp_count"] = page_local_hp_count
    global_labels = page_wide_tsv_labels()
    diagnostics["tsv_page_wide_hp_label_count"] = len(global_labels)

    name_line_index = next(
        (
            index
            for index, words in enumerate(ordered_lines)
            if normalized_name
            in normalize_reference_name(
                " ".join(str(word["text"]) for word in words)
            ).replace(" ", "")
        ),
        None,
    )
    diagnostics["tsv_name_anchor_found"] = name_line_index is not None
    label_words: list[dict[str, str]] | None = None
    # The target name remains the required upper anchor. Descriptor and wrapped
    # lines vary across legacy layouts, so scan subsequent TSV lines; the crop
    # is still bound to the first HP label below that exact target identity.
    if name_line_index is not None:
        for words in ordered_lines[name_line_index + 1 :]:
            normalized = " ".join(str(word["text"]) for word in words).casefold()
            if "punti" in normalized and "ferita" in normalized:
                label_words = words
                break
    if label_words is None and name_line_index is not None:
        name_words = ordered_lines[name_line_index]
        name_bottom = max(int(word["top"]) + int(word["height"]) for word in name_words)
        geometric_window = [
            words
            for words in ordered_lines[name_line_index + 1 : name_line_index + 13]
            if 0 <= min(int(word["top"]) for word in words) - name_bottom <= 60
        ]
        for index, words in enumerate(geometric_window):
            normalized = " ".join(str(word["text"]) for word in words).casefold()
            if "punti" not in normalized:
                continue
            for following in geometric_window[index : index + 3]:
                following_text = " ".join(
                    str(word["text"]) for word in following
                ).casefold()
                if "ferita" in following_text:
                    label_words = words + [
                        word for word in following if word not in words
                    ]
                    break
            if label_words is not None:
                break
    diagnostics["tsv_local_label_found"] = label_words is not None
    if label_words is None and page_target_count == 1 and page_local_hp_count == 1:
        if len(global_labels) == 1:
            label_words = global_labels[0]
            print(
                "HP_PAGE_WIDE_FALLBACK "
                + json.dumps(
                    {"name": name, "unique_tsv_hp_labels": 1},
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )
    if label_words is None:
        return fail_closed("no_unique_structural_hp_anchor")

    ferita_index = next(
        (
            index
            for index, word in enumerate(label_words)
            if "ferita" in str(word["text"]).casefold()
        ),
        None,
    )
    if ferita_index is None:
        return fail_closed("ferita_token_missing_from_label")

    label_end = int(label_words[ferita_index]["left"]) + int(
        label_words[ferita_index]["width"]
    )
    line_top = min(int(word["top"]) for word in label_words)
    line_bottom = max(int(word["top"]) + int(word["height"]) for word in label_words)
    source_pixmap = fitz.Pixmap(str(image_path))
    grayscale = fitz.Pixmap(fitz.csGRAY, source_pixmap)
    padding = max(2, (line_bottom - line_top) // 3)
    crop_rect = fitz.IRect(
        max(0, label_end),
        max(0, line_top - padding),
        grayscale.width,
        min(grayscale.height, line_bottom + padding),
    )
    crop_width = crop_rect.x1 - crop_rect.x0
    crop_height = crop_rect.y1 - crop_rect.y0
    source_samples = grayscale.samples
    crop_samples = b"".join(
        source_samples[
            row * grayscale.stride + crop_rect.x0 : row * grayscale.stride
            + crop_rect.x1
        ]
        for row in range(crop_rect.y0, crop_rect.y1)
    )

    def run_micro_ocr(
        contrast: float,
        directory: Path,
        *,
        otsu_inverted: bool = False,
        scale_factor: int = 1,
        morphological_dark_dilation: bool = False,
        morphological_dark_erosion: bool = False,
        bitonal_threshold: int | None = None,
        adaptive_background_inversion: bool = False,
    ) -> str:
        contrasted_samples = bytes(
            max(0, min(255, round(128 + (sample - 128) * contrast)))
            for sample in crop_samples
        )
        contrasted = fitz.Pixmap(
            fitz.csGRAY,
            crop_width,
            crop_height,
            contrasted_samples,
            False,
        )
        if scale_factor > 1:
            # Let MuPDF interpolate the crop before thresholding so fused
            # legacy-font strokes have additional geometric resolution.
            raster = fitz.Pixmap(
                contrasted,
                crop_width * scale_factor,
                crop_height * scale_factor,
            )
        else:
            raster = contrasted
        threshold_samples = raster.samples
        if morphological_dark_dilation:
            threshold_samples = _dilate_dark_pixels(
                threshold_samples,
                raster.width,
                raster.height,
            )
        if morphological_dark_erosion:
            threshold_samples = _erode_dark_pixels(
                threshold_samples,
                raster.width,
                raster.height,
            )
        background_mean, background_variance = _background_luminance_stats(
            threshold_samples,
            raster.width,
            raster.height,
        )
        use_adaptive_inversion = bool(
            adaptive_background_inversion
            and (
                background_mean < HIT_POINTS_BACKGROUND_MEAN_WHITE_THRESHOLD
                or background_variance > HIT_POINTS_BACKGROUND_VARIANCE_THRESHOLD
            )
        )
        if bitonal_threshold is not None and not use_adaptive_inversion:
            threshold_samples = bytes(
                0 if sample <= bitonal_threshold else 255
                for sample in threshold_samples
            )
        if otsu_inverted or use_adaptive_inversion:
            processed = fitz.Pixmap(
                fitz.csGRAY,
                raster.width,
                raster.height,
                _otsu_inverted_samples(threshold_samples),
                False,
            )
        else:
            processed = raster
        suffix = "-otsu-inverted" if otsu_inverted else ""
        if scale_factor > 1:
            suffix = f"-upscaled-x{scale_factor}" + suffix
        if morphological_dark_dilation:
            suffix = "-dark-dilated" + suffix
        if morphological_dark_erosion:
            suffix = "-dark-eroded" + suffix
        if bitonal_threshold is not None:
            suffix = f"-threshold-{bitonal_threshold}" + suffix
        if use_adaptive_inversion:
            suffix = "-adaptive-background-inverted" + suffix
        crop_path = directory / f"hit-points-{contrast:.1f}{suffix}.png"
        processed.save(crop_path)
        command = [
            "tesseract",
            str(crop_path),
            "stdout",
            "-l",
            languages,
            "--psm",
            "7",
            "-c",
            f"tessedit_char_whitelist={HIT_POINTS_WHITELIST}",
            "quiet",
        ]
        try:
            return subprocess.run(
                command,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=15,
            ).stdout
        except subprocess.TimeoutExpired:
            # subprocess.run() kills and waits for the direct Tesseract child
            # before re-raising TimeoutExpired. Treat this variant as a
            # fail-closed miss so the full-spectrum loop can continue.
            print(
                "HP_MICRO_OCR_SUBPROCESS_TIMEOUT "
                + json.dumps(
                    {
                        "name": name,
                        "timeout_seconds": 15,
                        "variant": crop_path.name,
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )
            return ""
        except subprocess.CalledProcessError as exc:
            print(
                "HP_MICRO_OCR_SUBPROCESS_FAILURE "
                + json.dumps(
                    {
                        "name": name,
                        "returncode": exc.returncode,
                        "signal": -exc.returncode if exc.returncode < 0 else None,
                        "variant": crop_path.name,
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )
            return ""

    def hp_micro_ocr_failed(raw_text: str) -> bool:
        normalized = " ".join(raw_text.split())
        return HP_FORMAT_ERROR_FLAG in monster_semantic_numeric_flags(
            {
                "classe_armatura": "10",
                "punti_ferita": normalized,
            }
        )

    with tempfile.TemporaryDirectory(prefix="tomoforge-hp-micro-ocr-") as tmp:
        directory = Path(tmp)
        micro = run_micro_ocr(HIT_POINTS_CONTRAST, directory)
        initial_micro = micro
        if NONSTANDARD_MULTI_DIGIT_DIE_RE.search(micro) or hp_micro_ocr_failed(micro):
            otsu_micro = run_micro_ocr(
                HIT_POINTS_FALLBACK_CONTRAST,
                directory,
                otsu_inverted=True,
            )
            upscaled_otsu_micro = None
            if hp_micro_ocr_failed(otsu_micro):
                upscaled_otsu_micro = run_micro_ocr(
                    HIT_POINTS_FALLBACK_CONTRAST,
                    directory,
                    otsu_inverted=True,
                    scale_factor=2,
                )
                micro = upscaled_otsu_micro
                superscaled_otsu_micro = None
                if hp_micro_ocr_failed(upscaled_otsu_micro):
                    superscaled_otsu_micro = run_micro_ocr(
                        HIT_POINTS_FALLBACK_CONTRAST,
                        directory,
                        otsu_inverted=True,
                        scale_factor=4,
                        morphological_dark_dilation=True,
                    )
                    micro = superscaled_otsu_micro
            else:
                micro = otsu_micro
                superscaled_otsu_micro = None
            full_spectrum_attempts: list[dict[str, object]] = []
            full_spectrum_accepted: dict[str, object] | None = None
            if hp_micro_ocr_failed(micro):
                crop_background_mean, crop_background_variance = (
                    _background_luminance_stats(
                        crop_samples,
                        crop_width,
                        crop_height,
                    )
                )
                # Progressive full-spectrum search: exhaust x2 first and pay
                # the x4 superscaling cost only when every lower-density
                # candidate still fails the existing deterministic HP gate.
                # hp_micro_ocr_failed() includes both strict expression parsing
                # and PF-average/hit-dice mathematical coherence, so early exit
                # cannot weaken the fail-closed acceptance criteria.
                for scale_factor in (2, 4):
                    for contrast in HIT_POINTS_FULL_SPECTRUM_CONTRASTS:
                        for threshold in HIT_POINTS_FULL_SPECTRUM_THRESHOLDS:
                            for morphology in (
                                "erosion",
                                "dilation",
                                "dilation_erosion",
                                "none",
                            ):
                                candidate = run_micro_ocr(
                                    contrast,
                                    directory,
                                    scale_factor=scale_factor,
                                    morphological_dark_erosion=morphology
                                    in {"erosion", "dilation_erosion"},
                                    morphological_dark_dilation=morphology
                                    in {"dilation", "dilation_erosion"},
                                    bitonal_threshold=threshold,
                                    adaptive_background_inversion=True,
                                )
                                failed = hp_micro_ocr_failed(candidate)
                                attempt = {
                                    "scale_factor": scale_factor,
                                    "contrast": contrast,
                                    "threshold": threshold,
                                    "morphology": morphology,
                                    "hp_format_error": failed,
                                    "background_mean": crop_background_mean,
                                    "background_variance": crop_background_variance,
                                    "adaptive_background_inversion": (
                                        crop_background_mean
                                        < HIT_POINTS_BACKGROUND_MEAN_WHITE_THRESHOLD
                                        or crop_background_variance
                                        > HIT_POINTS_BACKGROUND_VARIANCE_THRESHOLD
                                    ),
                                }
                                full_spectrum_attempts.append(attempt)
                                if not failed:
                                    micro = candidate
                                    full_spectrum_accepted = attempt
                                    break
                            if full_spectrum_accepted is not None:
                                break
                        if full_spectrum_accepted is not None:
                            break
                    if full_spectrum_accepted is not None:
                        break
            print(
                "HP_MICRO_OCR_DIAGNOSTIC "
                + json.dumps(
                    {
                        "name": name,
                        "initial_raw": initial_micro,
                        "otsu_inverted_raw": otsu_micro,
                        "otsu_hp_format_error": hp_micro_ocr_failed(otsu_micro),
                        "upscaled_otsu_inverted_raw": upscaled_otsu_micro,
                        "upscaled_otsu_hp_format_error": (
                            hp_micro_ocr_failed(upscaled_otsu_micro)
                            if upscaled_otsu_micro is not None
                            else None
                        ),
                        "superscaled_otsu_inverted_raw": superscaled_otsu_micro,
                        "superscaled_otsu_hp_format_error": (
                            hp_micro_ocr_failed(superscaled_otsu_micro)
                            if superscaled_otsu_micro is not None
                            else None
                        ),
                        "full_spectrum_attempt_count": len(full_spectrum_attempts),
                        "full_spectrum_accepted": full_spectrum_accepted,
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )
        elif re.search(r"\([^)]*\b\d{4,}\b", micro):
            micro = run_micro_ocr(HIT_POINTS_FALLBACK_CONTRAST, directory)

    value = " ".join(micro.split())
    if not value or not re.search(r"\d", value):
        return fail_closed("micro_ocr_numeric_value_missing")
    return hp_line_pattern.sub(
        lambda match: f"{match.group('label').rstrip()} {value}",
        page_text,
        count=1,
    )


def _ocr_source_window(
    pdf_path: Path,
    target_page: int,
    page_total: int,
    source: dict[str, Any],
    name: str,
    *,
    dpi: int,
    languages: str,
    psm: int,
    comparison_psm: int,
    column_overlap: float = 0.02,
    sparse_full_page: bool = False,
) -> tuple[
    list[tuple[int, str]],
    list[tuple[int, str]],
    dict[int, dict[str, Any]],
]:
    """OCR <=3 pages, isolating columns and any quality-fail segment."""
    import fitz

    start_page = max(1, target_page - 1)
    end_page = min(page_total, target_page + 1)
    if end_page - start_page + 1 > 3:
        raise AssertionError(
            "source-guided repair window unexpectedly exceeded 3 pages"
        )

    effective_dpi, primary_psm, secondary_psm = _layout_ocr_settings(
        source,
        dpi=dpi,
        psm=psm,
        comparison_psm=comparison_psm,
    )
    if primary_psm == secondary_psm:
        raise RepairBlocked("ocr_layout_modes_not_independent")

    primary_pages: list[tuple[int, str]] = []
    comparison_pages: list[tuple[int, str]] = []
    metrics: dict[int, dict[str, Any]] = {}
    matrix = fitz.Matrix(effective_dpi / 72.0, effective_dpi / 72.0)
    segments = (
        (("sparse-full", (0.0, 0.0, 1.0, 1.0)),)
        if sparse_full_page
        else _layout_segments(source, overlap_fraction=column_overlap)
    )

    document = fitz.open(pdf_path)
    try:
        with tempfile.TemporaryDirectory(
            prefix="tomoforge-source-repair-ocr-"
        ) as image_tmp:
            image_root = Path(image_tmp)
            for page_number in range(start_page, end_page + 1):
                page = document.load_page(page_number - 1)
                primary_parts: list[str] = []
                comparison_parts: list[str] = []
                segment_metrics: dict[str, dict[str, Any]] = {}

                for segment_name, fractions in segments:
                    clip = _clip_rect(page.rect, fractions)
                    image_path = (
                        image_root / f"page-{page_number:04d}-{segment_name}.png"
                    )
                    page.get_pixmap(
                        matrix=matrix,
                        clip=clip,
                        alpha=False,
                        colorspace=fitz.csGRAY,
                    ).save(image_path)

                    if name in QUALITY_FAIL_PRE_OTSU_TARGETS and not sparse_full_page:
                        _pre_otsu_column_clean(image_path)

                    sparse_anchor_found = None
                    sparse_anchor_crop = None
                    if sparse_full_page:
                        sparse_anchor_crop = _sparse_anchor_crop_fractions(
                            image_path,
                            languages,
                            name,
                        )
                        sparse_anchor_found = sparse_anchor_crop is not None
                        if not sparse_anchor_found:
                            segment_metrics[segment_name] = {
                                "quality_pass": False,
                                "sparse_anchor_found": False,
                                "sparse_anchor_crop": None,
                            }
                            continue
                        target_clip = _clip_rect(page.rect, sparse_anchor_crop)
                        target_image_path = (
                            image_root
                            / f"page-{page_number:04d}-{segment_name}-target.png"
                        )
                        page.get_pixmap(
                            matrix=matrix,
                            clip=target_clip,
                            alpha=False,
                            colorspace=fitz.csGRAY,
                        ).save(target_image_path)
                        image_path = target_image_path

                    primary = _run_tesseract(
                        image_path,
                        languages,
                        primary_psm,
                    )
                    primary = _micro_ocr_hit_points_line(
                        image_path,
                        languages,
                        primary_psm,
                        primary,
                        name,
                    )
                    comparison = _run_tesseract(
                        image_path,
                        languages,
                        secondary_psm,
                    )
                    comparison = _micro_ocr_hit_points_line(
                        image_path,
                        languages,
                        secondary_psm,
                        comparison,
                        name,
                    )
                    agreement = _agreement_metrics(
                        primary,
                        comparison,
                    )
                    if sparse_full_page:
                        agreement["sparse_anchor_found"] = sparse_anchor_found
                        agreement["sparse_anchor_crop"] = (
                            list(sparse_anchor_crop)
                            if sparse_anchor_crop is not None
                            else None
                        )
                    segment_metrics[segment_name] = agreement

                    # Fail closed per segment. A bad neighboring column is
                    # isolated and cannot poison a clean target column.
                    if agreement["quality_pass"]:
                        primary_parts.append(primary)
                        comparison_parts.append(comparison)

                page_quality_pass = bool(primary_parts)
                metrics[page_number] = {
                    "quality_pass": page_quality_pass,
                    "layout_profile": _layout_profile(source),
                    "effective_dpi": effective_dpi,
                    "primary_psm": primary_psm,
                    "comparison_psm": secondary_psm,
                    "segments": segment_metrics,
                    "column_overlap": column_overlap,
                    "sparse_full_page": sparse_full_page,
                }
                if page_quality_pass:
                    # Column outputs are concatenated only after independent
                    # OCR/quality checks; no pixels or same-line text can bleed.
                    primary_pages.append((page_number, "\n\n".join(primary_parts)))
                    comparison_pages.append(
                        (page_number, "\n\n".join(comparison_parts))
                    )
    finally:
        document.close()

    if target_page not in {page for page, _ in primary_pages}:
        raise RepairBlocked("target_page_quality_fail")
    return primary_pages, comparison_pages, metrics


def _candidate_matches_target(
    candidate: dict[str, Any],
    target_name: str,
    target_page: int,
) -> bool:
    candidate_name = str(
        candidate.get("normalized_name") or candidate.get("name") or ""
    )
    target_normalized = normalize_reference_name(target_name)
    pages = {
        int(ref.get("page"))
        for ref in (candidate.get("source_refs") or [])
        if isinstance(ref, dict) and ref.get("page") is not None
    }
    name_match = (
        candidate_name == target_normalized
        or compact_name_boundary_match(candidate_name, target_normalized)
        or compact_name_containment_match(candidate_name, target_normalized)
        or compact_name_bounded_edit_match(candidate_name, target_normalized)
    )
    same_page = target_page in pages
    adjacent_page = bool(
        len(candidate_name.split()) >= 2
        and len(target_normalized.split()) >= 2
        and any(abs(page - target_page) == 1 for page in pages)
        and (candidate.get("attributes") or {}).get("ocr_independent_agreement") is True
        and (candidate.get("attributes") or {}).get(
            "ocr_clean_deterministic_core_agreement"
        )
        is True
    )
    return name_match and (same_page or adjacent_page)


def _agreed_target_candidate(
    primary_pages: list[tuple[int, str]],
    comparison_pages: list[tuple[int, str]],
    source_filename: str,
    source_language: str,
    target_name: str,
    target_page: int,
) -> dict[str, Any]:
    primary = parse_monster_statblocks(
        primary_pages,
        source_filename,
        source_language,
    )
    comparison = parse_monster_statblocks(
        comparison_pages,
        source_filename,
        source_language,
    )
    agreed_forward = agreed_monster_records(
        primary,
        comparison,
        target_name=target_name,
    )
    agreed_reverse = agreed_monster_records(
        comparison,
        primary,
        target_name=target_name,
    )
    agreed: list[dict[str, Any]] = []
    for candidate in [*agreed_forward, *agreed_reverse]:
        duplicate = False
        candidate_page = int(candidate.get("start_page") or 0)
        candidate_name = str(
            candidate.get("normalized_name") or candidate.get("name") or ""
        )
        candidate_attributes = candidate.get("attributes") or {}
        for existing in agreed:
            if int(existing.get("start_page") or 0) != candidate_page:
                continue
            existing_name = str(
                existing.get("normalized_name") or existing.get("name") or ""
            )
            if existing_name != candidate_name:
                continue
            deterministic = deterministic_core_field_matches(
                candidate_attributes,
                existing.get("attributes") or {},
            )
            if all(
                deterministic.get(f"{field}_deterministic_match", False)
                for field in ("classe_armatura", "punti_ferita", "velocita")
            ):
                duplicate = True
                break
        if not duplicate:
            agreed.append(candidate)

    matches = [
        candidate
        for candidate in agreed
        if _candidate_matches_target(
            candidate,
            target_name,
            target_page,
        )
    ]
    if len(matches) > 1:
        target_normalized_for_rank = normalize_reference_name(target_name)

        def identity_rank(candidate: dict[str, Any]) -> int:
            candidate_name = str(
                candidate.get("normalized_name") or candidate.get("name") or ""
            )
            if candidate_name == target_normalized_for_rank:
                return 4
            if compact_name_boundary_match(
                candidate_name,
                target_normalized_for_rank,
            ):
                return 3
            if compact_name_containment_match(
                candidate_name,
                target_normalized_for_rank,
            ):
                return 2
            if compact_name_bounded_edit_match(
                candidate_name,
                target_normalized_for_rank,
            ):
                return 1
            return 0

        first_attributes = matches[0].get("attributes") or {}
        core_equivalent = all(
            all(
                deterministic_core_field_matches(
                    first_attributes,
                    candidate.get("attributes") or {},
                ).get(f"{field}_deterministic_match", False)
                for field in ("classe_armatura", "punti_ferita", "velocita")
            )
            for candidate in matches[1:]
        )
        if core_equivalent:
            ranked = [(identity_rank(candidate), candidate) for candidate in matches]
            best_rank = max(rank for rank, _candidate in ranked)
            best = [
                candidate
                for rank, candidate in ranked
                if rank == best_rank and best_rank > 0
            ]
            if len(best) == 1:
                matches = best

    if len(matches) != 1:
        core_fields = ("classe_armatura", "punti_ferita", "velocita")
        target_normalized = normalize_reference_name(target_name)

        def target_candidates(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
            return [
                candidate
                for candidate in records
                if _candidate_matches_target(candidate, target_name, target_page)
            ]

        primary_targets = target_candidates(primary)
        comparison_targets = target_candidates(comparison)

        def name_candidates(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
            return [
                candidate
                for candidate in records
                if (
                    str(candidate.get("normalized_name") or candidate.get("name") or "")
                    == target_normalized
                    or compact_name_containment_match(
                        str(
                            candidate.get("normalized_name")
                            or candidate.get("name")
                            or ""
                        ),
                        target_normalized,
                    )
                )
            ]

        primary_name_candidates = name_candidates(primary)
        comparison_name_candidates = name_candidates(comparison)
        divergent_fields: set[str] = set()
        discarded_pairs: list[dict[str, Any]] = []
        exact_name_match_count = 0
        containment_match_count = 0
        for left in primary_name_candidates:
            left_name = str(left.get("normalized_name") or left.get("name") or "")
            left_attributes = left.get("attributes") or {}
            for right in comparison_name_candidates:
                right_name = str(
                    right.get("normalized_name") or right.get("name") or ""
                )
                exact_name_match = left_name == right_name
                containment_match = compact_name_containment_match(
                    left_name,
                    right_name,
                )
                if exact_name_match:
                    exact_name_match_count += 1
                elif containment_match:
                    containment_match_count += 1
                if not (exact_name_match or containment_match):
                    continue
                right_attributes = right.get("attributes") or {}
                for field in core_fields:
                    if (
                        " ".join(
                            str(left_attributes.get(field) or "").split()
                        ).casefold()
                        != " ".join(
                            str(right_attributes.get(field) or "").split()
                        ).casefold()
                    ):
                        divergent_fields.add(field)
                semantic = semantic_core_field_matches(
                    left_attributes,
                    right_attributes,
                )
                deterministic = deterministic_core_field_matches(
                    left_attributes,
                    right_attributes,
                )
                speed_profile = speed_multi_extra_token_profile(
                    left_attributes,
                    right_attributes,
                )
                left_start_page = int(left.get("start_page") or 0)
                right_start_page = int(right.get("start_page") or 0)
                discarded_pairs.append(
                    {
                        "start_page_mismatch": left_start_page != right_start_page,
                        "primary_start_page": left_start_page,
                        "comparison_start_page": right_start_page,
                        "exact_name_match": exact_name_match,
                        "containment_match": containment_match,
                        "semantic_matches": {
                            key: bool(value)
                            for key, value in sorted(semantic.items())
                            if key.endswith("_semantic_match")
                        },
                        "deterministic_matches": {
                            key: bool(value)
                            for key, value in sorted(deterministic.items())
                            if key.endswith("_deterministic_match")
                        },
                        "velocita_duplicate_ambiguous": bool(
                            speed_profile.get(
                                "velocita_residual_duplicate_ambiguous",
                                False,
                            )
                        ),
                    }
                )

        raise RepairBlocked(
            "no_unique_independent_agreement",
            f"matching independently-agreed candidates={len(matches)}",
            {
                "primary_candidates_found": len(primary),
                "comparison_candidates_found": len(comparison),
                "primary_target_candidates": len(primary_targets),
                "comparison_target_candidates": len(comparison_targets),
                "primary_name_candidates": len(primary_name_candidates),
                "comparison_name_candidates": len(comparison_name_candidates),
                "exact_name_match_count": exact_name_match_count,
                "containment_match_count": containment_match_count,
                "divergent_core_fields": sorted(divergent_fields),
                "discarded_pairs": discarded_pairs,
                "target_normalized_name": target_normalized,
                "target_page": target_page,
            },
        )
    return matches[0]


def build_repair_proposal(
    legacy: dict[str, Any],
    candidate: dict[str, Any],
) -> dict[str, Any]:
    """Build a minimal core-field repair and run all OCR gates in memory."""
    candidate_attributes = dict(candidate.get("attributes") or {})
    gate_failures = monster_semantic_numeric_flags(candidate_attributes)
    if gate_failures:
        raise RepairBlocked(
            "repaired_candidate_failed_gates",
            ",".join(sorted(gate_failures)),
        )
    if not str(candidate_attributes.get("velocita") or "").strip():
        raise RepairBlocked("repaired_candidate_missing_speed")
    if entity_name_semantic_flags(candidate.get("name")):
        raise RepairBlocked("repaired_candidate_invalid_title")
    if monster_identity_sanity_flags(candidate.get("name")):
        raise RepairBlocked("repaired_candidate_corrupted_name")

    merged_attributes = dict(legacy.get("attributes") or {})
    for field in ("classe_armatura", "punti_ferita", "velocita"):
        merged_attributes[field] = candidate_attributes[field]

    existing_flags = {
        str(flag)
        for flag in (legacy.get("review_flags") or [])
        if str(flag) not in CRITICAL_GATE_FLAGS
    }
    existing_flags.add(REPAIR_FLAG)

    gated = apply_ocr_review_gates(
        {
            **legacy,
            "attributes": merged_attributes,
            "review_flags": sorted(existing_flags),
            "review_status": "pending",
        }
    )

    post_flags = monster_semantic_numeric_flags(gated.get("attributes") or {})
    if post_flags:
        raise RepairBlocked(
            "post_merge_gate_failure",
            ",".join(sorted(post_flags)),
        )
    gated_flags = set(gated.get("review_flags") or [])
    if INVALID_ENTITY_TITLE_FLAG in gated_flags:
        raise RepairBlocked("post_merge_invalid_title")
    if CORRUPTED_ENTITY_NAME_FLAG in gated_flags:
        raise RepairBlocked("post_merge_corrupted_name")
    if gated.get("review_status") != "pending" or OCR_REVIEW_FLAG not in gated_flags:
        raise AssertionError("OCR repair proposal lost mandatory review state")

    return {
        "attributes": gated["attributes"],
        "review_flags": gated["review_flags"],
        "review_status": "pending",
    }


async def _apply_update(
    collection: Any,
    legacy: dict[str, Any],
    proposal: dict[str, Any],
    *,
    updated_at: str | None = None,
) -> None:
    if legacy.get("canonical_id"):
        raise RepairBlocked(
            "canonical_record_linked",
            "Refusing to mutate a record already linked to canonical data",
        )
    if monster_identity_sanity_flags(legacy.get("name")):
        raise RepairBlocked(
            "corrupted_entity_name",
            "Refusing to mutate a monster with a structurally corrupt legacy name",
        )

    query: dict[str, Any] = {
        "id": str(legacy["id"]),
        "review_status": "verified",
    }
    checksum = str(legacy.get("source_text_checksum") or "")
    if checksum:
        query["source_text_checksum"] = checksum

    write_payload = {
        **proposal,
        "updated_at": updated_at
        or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    result = await collection.update_one(
        query,
        {"$set": write_payload},
    )
    if result.matched_count != 1:
        raise RepairBlocked(
            "concurrent_record_drift",
            f"matched_count={result.matched_count}",
        )

    verify = await collection.find_one({"id": str(legacy["id"])})
    if not verify or verify.get("review_status") != "pending":
        raise RuntimeError("post-update verification failed")
    verify_flags = {str(flag) for flag in (verify.get("review_flags") or [])}
    if OCR_REVIEW_FLAG not in verify_flags or REPAIR_FLAG not in verify_flags:
        raise RuntimeError("post-update review flags verification failed")
    if CORRUPTED_ENTITY_NAME_FLAG in verify_flags:
        raise RuntimeError("post-update corrupted name verification failed")
    if monster_semantic_numeric_flags(verify.get("attributes") or {}):
        raise RuntimeError("post-update semantic/numeric verification failed")
    if str(verify.get("updated_at") or "") == str(legacy.get("updated_at") or ""):
        raise RuntimeError("post-update updated_at verification failed")
    if updated_at is not None:
        expected_timestamp = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
        actual_timestamp = datetime.fromisoformat(
            str(verify.get("updated_at") or "").replace("Z", "+00:00")
        )
        if actual_timestamp != expected_timestamp:
            raise RuntimeError("post-update batch timestamp verification failed")


def _json_view(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": record.get("id"),
        "name": record.get("name"),
        "attributes": record.get("attributes") or {},
        "review_flags": record.get("review_flags") or [],
        "review_status": record.get("review_status"),
        "source_refs": record.get("source_refs") or [],
    }


def _corrupted_name_report(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "record_id": record.get("id"),
        "name": record.get("name"),
        "review_flags": [CORRUPTED_ENTITY_NAME_FLAG],
        "classification": "Record con Nome Corrotto (Scorie OCR)",
        "executed": False,
    }


async def _repair_one(
    collection: Any,
    record: dict[str, Any],
    active_sources: list[dict[str, Any]],
    pdf_cache: SourcePdfCache,
    args: argparse.Namespace,
) -> dict[str, Any]:
    source, source_ref = resolve_source(
        record,
        active_sources,
    )
    physical_page = int(source_ref["page"])
    pdf_path = pdf_cache.get(source)

    candidate = None
    quality = None
    selected_overlap = 0.02
    sparse_retry_required = False
    overlaps = (0.02, 0.03, 0.04, 0.05)
    for overlap_index, overlap in enumerate(overlaps):
        primary_pages, comparison_pages, quality = _ocr_source_window(
            pdf_path,
            physical_page,
            int(source["physical_pages"]),
            source,
            str(record.get("name") or ""),
            dpi=args.dpi,
            languages=args.languages,
            psm=args.psm,
            comparison_psm=args.comparison_psm,
            column_overlap=overlap,
        )
        try:
            candidate = _agreed_target_candidate(
                primary_pages,
                comparison_pages,
                str(source["physical_filename"]),
                str(source.get("language") or "it"),
                str(record.get("name") or ""),
                physical_page,
            )
            selected_overlap = overlap
            break
        except RepairBlocked as exc:
            if not _should_retry_dynamic_layout(exc, source):
                raise
            if overlap_index == len(overlaps) - 1:
                sparse_retry_required = True
                break
            print(
                "DYNAMIC_COLUMN_RETRY "
                + json.dumps(
                    {
                        "name": record.get("name"),
                        "failed_overlap": overlap,
                        "next_overlap": overlaps[overlap_index + 1],
                        "reason": exc.reason,
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )
    if candidate is None and sparse_retry_required:
        print(
            "SPARSE_PAGE_RETRY "
            + json.dumps(
                {"name": record.get("name"), "psm": 11},
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        primary_pages, comparison_pages, quality = _ocr_source_window(
            pdf_path,
            physical_page,
            int(source["physical_pages"]),
            source,
            str(record.get("name") or ""),
            dpi=args.dpi,
            languages=args.languages,
            psm=args.psm,
            comparison_psm=args.comparison_psm,
            column_overlap=0.05,
            sparse_full_page=True,
        )
        candidate = _agreed_target_candidate(
            primary_pages,
            comparison_pages,
            str(source["physical_filename"]),
            str(source.get("language") or "it"),
            str(record.get("name") or ""),
            physical_page,
        )
        selected_overlap = 0.05
    if candidate is None or quality is None:
        raise RepairBlocked("dynamic_layout_exhausted")
    proposal = build_repair_proposal(
        record,
        candidate,
    )

    target_metrics = quality[physical_page]
    report = {
        "name": record.get("name"),
        "record_id": record.get("id"),
        "source": {
            "physical_filename": source.get("physical_filename"),
            "logical_source_id": source.get("logical_source_id"),
            "source_role": source.get("source_role"),
            "source_status": source.get("source_status"),
            "physical_page": physical_page,
            "logical_page": source_ref.get("logical_page"),
        },
        "layout": {
            "profile": target_metrics["layout_profile"],
            "effective_dpi": target_metrics["effective_dpi"],
            "primary_psm": target_metrics["primary_psm"],
            "comparison_psm": target_metrics["comparison_psm"],
            "segments": sorted(target_metrics["segments"].keys()),
            "column_overlap": selected_overlap,
            "sparse_full_page": bool(target_metrics.get("sparse_full_page")),
        },
        "ocr_pages": sorted(quality),
        "quality_fail_pages": sorted(
            page
            for page, page_metrics in quality.items()
            if not page_metrics["quality_pass"]
        ),
        "before": _json_view(record),
        "after": {
            **_json_view(record),
            **proposal,
        },
        "gate_failures_before": sorted(
            monster_semantic_numeric_flags(record.get("attributes") or {})
        ),
        "gate_failures_after": [],
        "would_update": True,
        "executed": False,
    }

    if args.execute:
        await _apply_update(
            collection,
            record,
            proposal,
        )
        report["executed"] = True
    return report


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Source-guided legacy monster repair")
    parser.add_argument(
        "--name",
        default="Zuggtmoy",
        help="Single monster name; default dry-run sample",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Process every currently failed legacy monster with a sane name",
    )
    parser.add_argument(
        "--target-set",
        choices=(
            "healthy22",
            "approved1",
            "approved5",
            "oblex1",
            "ready6",
            "bigby19",
            "bigby4",
            "batch_alpha",
            "batch_beta",
            "batch_gamma",
        ),
        default=None,
        help="Process only an exact reviewed sealed target set",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Apply validated repairs; default is dry-run",
    )
    parser.add_argument(
        "--confirm",
        default="",
        help="Exact confirmation token required for sealed batch execution",
    )
    parser.add_argument(
        "--pdf-root",
        default=os.getenv("TOMOFORGE_PDF_ROOT", ""),
    )
    parser.add_argument(
        "--allow-r2-download",
        action="store_true",
        help="Download exact registry PDF to a temporary local path",
    )
    parser.add_argument("--dpi", type=int, default=220)
    parser.add_argument("--languages", default="ita")
    parser.add_argument("--psm", type=int, default=6)
    parser.add_argument("--comparison-psm", type=int, default=4)
    return parser


async def _run(args: argparse.Namespace) -> int:
    if args.psm == args.comparison_psm:
        raise RuntimeError("OCR layout modes must differ")
    if not 120 <= args.dpi <= 300:
        raise RuntimeError("dpi must be between 120 and 300")
    if args.all and args.target_set:
        raise RuntimeError("--all and --target-set are mutually exclusive")
    if args.execute and not args.all and not args.target_set and not args.name:
        raise RuntimeError(
            "execution requires an explicit --name, --all, or --target-set"
        )
    if args.execute and args.target_set in {
        "bigby19",
        "batch_alpha",
        "batch_beta",
        "batch_gamma",
    }:
        raise RuntimeError(f"{args.target_set} is a dry-run-only audit target set")
    if (
        args.execute
        and args.target_set == "healthy22"
        and args.confirm != HEALTHY22_CONFIRMATION_TOKEN
    ):
        raise RuntimeError("Healthy22 confirmation token mismatch")
    if (
        args.execute
        and args.target_set == "bigby4"
        and args.confirm != BIGBY4_CONFIRMATION_TOKEN
    ):
        raise RuntimeError("Bigby4 confirmation token mismatch")
    if (
        args.execute
        and args.target_set == "approved1"
        and args.confirm != APPROVED1_CONFIRMATION_TOKEN
    ):
        raise RuntimeError("Approved1 confirmation token mismatch")
    if (
        args.execute
        and args.target_set == "approved5"
        and args.confirm != APPROVED5_CONFIRMATION_TOKEN
    ):
        raise RuntimeError("Approved5 confirmation token mismatch")
    if (
        args.execute
        and args.target_set == "oblex1"
        and args.confirm != OBLEX1_CONFIRMATION_TOKEN
    ):
        raise RuntimeError("Oblex1 confirmation token mismatch")
    if (
        args.execute
        and args.target_set == "ready6"
        and args.confirm != READY6_CONFIRMATION_TOKEN
    ):
        raise RuntimeError("Ready6 confirmation token mismatch")

    # Defense in depth: this repair path must never call hosted AI.
    os.environ.pop("OPENAI_API_KEY", None)
    os.environ.pop("GEMINI_API_KEY", None)

    from core.db import db

    if not db.configured:
        raise RuntimeError("Supabase is not configured")

    records_collection = db.private_reference_records
    source_collection = db.private_reference_sources
    verified = await _fetch_all(
        records_collection,
        {
            "review_status": "verified",
            "reference_type": "monster",
        },
    )
    failures = select_failed_monsters(verified)
    corrupted_names = select_corrupted_name_monsters(verified)
    active_sources = await _fetch_all(
        source_collection,
        {"source_status": "active"},
    )

    summary = {
        "verified_monsters": len(verified),
        "failed_monsters_total": len(failures) + len(corrupted_names),
        "failed_monsters_selected": len(failures),
        "corrupted_entity_names": len(corrupted_names),
        "expected_initial_failures": EXPECTED_INITIAL_FAILURES,
        "dry_run": not args.execute,
    }
    print("SOURCE_GUIDED_REPAIR_SUMMARY")
    print(
        json.dumps(
            summary,
            ensure_ascii=False,
            sort_keys=True,
        )
    )

    if not failures and not corrupted_names:
        return 0

    sealed_batch = args.target_set in {
        "healthy22",
        "approved1",
        "approved5",
        "oblex1",
        "ready6",
        "bigby4",
    }
    if args.target_set in RESIDUAL_BATCH_TARGETS:
        targets = select_residual_batch_targets(failures, args.target_set)
        sealed_expected_count = None
        sealed_label = args.target_set
    elif args.target_set == "healthy22":
        targets = select_healthy22_targets(failures)
        sealed_expected_count = EXPECTED_HEALTHY22_COUNT
        sealed_label = "Healthy22"
    elif args.target_set == "bigby4":
        targets = select_bigby4_targets(failures)
        sealed_expected_count = EXPECTED_BIGBY4_COUNT
        sealed_label = "Bigby4"
    elif args.target_set == "approved1":
        targets = select_approved1_targets(failures)
        sealed_expected_count = EXPECTED_APPROVED1_COUNT
        sealed_label = "Approved1"
    elif args.target_set == "approved5":
        targets = select_approved5_targets(failures)
        sealed_expected_count = EXPECTED_APPROVED5_COUNT
        sealed_label = "Approved5"
    elif args.target_set == "oblex1":
        targets = select_oblex1_targets(failures)
        sealed_expected_count = EXPECTED_OBLEX1_COUNT
        sealed_label = "Oblex1"
    elif args.target_set == "ready6":
        targets = select_ready6_targets(failures)
        sealed_expected_count = EXPECTED_READY6_COUNT
        sealed_label = "Ready6"
    elif args.target_set == "bigby19":
        targets = select_bigby19_targets(failures)
        sealed_expected_count = None
        sealed_label = "Bigby19"
    elif args.all:
        targets = failures
        sealed_expected_count = None
        sealed_label = "all"
        targets = failures
    else:
        wanted = str(args.name or "").casefold()
        corrupt_wanted = [
            record
            for record in corrupted_names
            if str(record.get("name") or "").casefold() == wanted
        ]
        if corrupt_wanted:
            raise RuntimeError(
                f"Monster {args.name!r} is isolated by "
                f"{CORRUPTED_ENTITY_NAME_FLAG} and cannot enter repair"
            )
        targets = [
            record
            for record in failures
            if str(record.get("name") or "").casefold() == wanted
        ]
        if len(targets) != 1:
            raise RuntimeError(
                f"Expected one failed monster named {args.name!r}; found {len(targets)}"
            )

    pdf_cache = SourcePdfCache(
        args.pdf_root,
        args.allow_r2_download,
    )
    reports = []
    blocked = []
    stage_args = argparse.Namespace(**vars(args))
    if sealed_batch:
        # No live write is allowed until every one of the 22 proposals has
        # completed OCR, independent agreement and semantic/numeric gates.
        stage_args.execute = False
    try:
        for record in targets:
            try:
                reports.append(
                    await _repair_one(
                        records_collection,
                        record,
                        active_sources,
                        pdf_cache,
                        stage_args,
                    )
                )
            except RepairBlocked as exc:
                blocked.append(
                    {
                        "record_id": record.get("id"),
                        "name": record.get("name"),
                        "reason": exc.reason,
                        "detail": exc.detail,
                        "executed": False,
                        **(
                            {"diagnostics": exc.diagnostics}
                            if exc.diagnostics is not None
                            else {}
                        ),
                    }
                )
            except Exception as exc:
                blocked.append(
                    {
                        "record_id": record.get("id"),
                        "name": record.get("name"),
                        "reason": "crash_eccezione_raw",
                        "detail": str(exc),
                        "executed": False,
                    }
                )
    finally:
        pdf_cache.close()

    if sealed_batch and args.execute:
        if blocked or len(reports) != sealed_expected_count:
            raise RuntimeError(
                f"{sealed_label} batch refused: all {sealed_expected_count} proposals "
                "must be repairable before any UPDATE"
            )
        await _revalidate_target_snapshots(records_collection, targets)
        originals = {str(record["id"]): record for record in targets}
        batch_updated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        for report in reports:
            expected_flags = sorted([OCR_REVIEW_FLAG, REPAIR_FLAG])
            actual_flags = sorted(str(flag) for flag in report["after"]["review_flags"])
            if actual_flags != expected_flags:
                raise RuntimeError(
                    f"{sealed_label} unexpected proposal flags for "
                    f"{report['record_id']}: {actual_flags!r}"
                )
            proposal = {
                "attributes": report["after"]["attributes"],
                "review_flags": report["after"]["review_flags"],
                "review_status": "pending",
            }
            before_attributes = (
                originals[str(report["record_id"])].get("attributes") or {}
            )
            after_attributes = proposal["attributes"]
            for field in set(before_attributes) | set(after_attributes):
                if field not in {
                    "classe_armatura",
                    "punti_ferita",
                    "velocita",
                } and before_attributes.get(field) != after_attributes.get(field):
                    raise RuntimeError(
                        f"{sealed_label} non-core attribute drift for {report['record_id']}: {field}"
                    )
            await _apply_update(
                records_collection,
                originals[str(report["record_id"])],
                proposal,
                updated_at=batch_updated_at,
            )
            report["executed"] = True

    name_corruption_bucket = {
        "label": "Record con Nome Corrotto (Scorie OCR)",
        "count": len(corrupted_names),
        "records": [_corrupted_name_report(record) for record in corrupted_names],
    }
    final = {
        "dry_run": not args.execute,
        "failed_monsters_total": len(failures) + len(corrupted_names),
        "targets": len(targets),
        "repairable": len(reports),
        "blocked": len(blocked),
        "corrupted_entity_names": len(corrupted_names),
        "name_corruption_bucket": name_corruption_bucket,
        "updates_performed": sum(1 for report in reports if report["executed"]),
        "batch_updated_at": batch_updated_at if sealed_batch and args.execute else None,
        "reports": reports,
        "blocked_records": blocked,
    }
    print("FINAL_REPORT")
    print(
        json.dumps(
            final,
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0 if reports or blocked or corrupted_names else 1


def main() -> int:
    try:
        return asyncio.run(_run(_parser().parse_args()))
    except Exception as exc:
        print(
            f"Source-guided monster repair aborted: {exc}",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
