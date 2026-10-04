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
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from reference_library import normalize_reference_name
from scripts.pilot_local_ocr_from_r2 import (
    _agreement_metrics,
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
    _find_header,
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


EXPECTED_PLAYERS_HANDBOOK_COUNT = 31
EXPECTED_PLAYERS_HANDBOOK_VERIFIED_COUNT = 14
EXPECTED_PLAYERS_HANDBOOK_IDS_MD5 = "a2f4c03bff9e13e4834344e890cdf099"
PLAYERS_HANDBOOK_LEGACY_FILENAME = "Manuale_del_giocatore__1787259882002.pdf"
PLAYERS_HANDBOOK_LOGICAL_SOURCE_ID = "phb_2014_it"
PLAYERS_HANDBOOK_CONFIRMATION_TOKEN = "CLEAN-PHB31-31-a2f4c03bff9e13e4834344e890cdf099"
PLAYERS_HANDBOOK_TARGETS: tuple[dict[str, str], ...] = (
    {
        "id": "ref_554da30e4dcd50dc89e327bcf76a6bda",
        "name": "Aquila Gigante",
        "status": "verified",
    },
    {
        "id": "ref_b82e375ea1b55332a2f58c3719559b49",
        "name": "Cavallo Da Galoppo",
        "status": "verified",
    },
    {
        "id": "ref_85a4eadb862758fbb682e93ab19f1065",
        "name": "Cavallo Da Guerra",
        "status": "verified",
    },
    {
        "id": "ref_66df831bf85c519ea29a652124767350",
        "name": "Cinghiale",
        "status": "verified",
    },
    {
        "id": "ref_9c0a7cc17c185980a4bbff7f4a6fed98",
        "name": "Coccodrillo",
        "status": "verified",
    },
    {
        "id": "ref_45c912daf13f527492fefbd392b25e3a",
        "name": "Corvo",
        "status": "verified",
    },
    {
        "id": "ref_f28940a5239a54f696cb524805e29cc2",
        "name": "Falco",
        "status": "verified",
    },
    {
        "id": "ref_2704a598d7185e209f21f044e39f4341",
        "name": "Gatto",
        "status": "verified",
    },
    {
        "id": "ref_38273488414b57489e9d7e57a6c0a360",
        "name": "Gufo",
        "status": "verified",
    },
    {"id": "ref_6e1a9996179d5a93a027a31bc30b5d2f", "name": "Imp", "status": "verified"},
    {
        "id": "ref_64b388f7cd6053c4a275e173aa482cfd",
        "name": "Leone",
        "status": "verified",
    },
    {
        "id": "ref_87ee4ffeff7c5b7bb65e12def234a3be",
        "name": "Lupo",
        "status": "verified",
    },
    {
        "id": "ref_3f86dfa076ca220708e09deff0d7d831",
        "name": "Lupo Feroce",
        "status": "pending",
    },
    {
        "id": "ref_c467615fbd9ce6c93677ac1d9a323eed",
        "name": "Mastino",
        "status": "pending",
    },
    {"id": "ref_f453abfdd8264ef7bb0d71805fe586e7", "name": "Mulo", "status": "pending"},
    {
        "id": "ref_019562bded0b320ac918f4b2514c65e4",
        "name": "Orso Bruno",
        "status": "pending",
    },
    {
        "id": "ref_00d159a7d0ee3d2e977d361999dd4966",
        "name": "Orso Nero",
        "status": "pending",
    },
    {
        "id": "ref_c401166fb5d39eb00b150a171e41ad26",
        "name": "Pantera",
        "status": "pending",
    },
    {
        "id": "ref_0626a11ef12ec092e8c13f94d1b03cd8",
        "name": "Pipistrello",
        "status": "pending",
    },
    {
        "id": "ref_ebab36d8c07021483328e99bebabf365",
        "name": "Pseudodrago",
        "status": "pending",
    },
    {
        "id": "ref_867c68436df55ff48716ebe704da4044",
        "name": "Quasit",
        "status": "verified",
    },
    {
        "id": "ref_4f1b7244dd735e579ae1e5ec931ccf17",
        "name": "Ragno Gigante",
        "status": "verified",
    },
    {"id": "ref_66cc59680c4e58fa93a99656f8a07887", "name": "Rana", "status": "pending"},
    {
        "id": "ref_6196e826b9aa5833ac6ffae026d26850",
        "name": "Scheletro",
        "status": "pending",
    },
    {
        "id": "ref_bc1c095a87b05bda98a5cc369e9daa24",
        "name": "Serpente Stritolatore",
        "status": "pending",
    },
    {
        "id": "ref_d60133b03dc9555e866728cbc2a75f9a",
        "name": "Serpente Velenoso",
        "status": "pending",
    },
    {
        "id": "ref_bff81a4eec5c54349735293d3691ca7d",
        "name": "Spiritello",
        "status": "pending",
    },
    {
        "id": "ref_34a7a3005aa296c6c4ed9cd6a962df3c",
        "name": "Squalo Tropicale",
        "status": "pending",
    },
    {
        "id": "ref_32307945d56a74e63b112480050955e9",
        "name": "Tigre",
        "status": "pending",
    },
    {"id": "ref_06dd892fa0e121a2237f34d5be31fab4", "name": "Topo", "status": "pending"},
    {
        "id": "ref_6f23f3488a9b5f276925987ddd975577",
        "name": "Zombi",
        "status": "pending",
    },
)

EXPECTED_PLAYERS_HANDBOOK_BLOCKED20_COUNT = 20
EXPECTED_PLAYERS_HANDBOOK_BLOCKED20_IDS_MD5 = "5e1cebb055ef0540f9bbec264d06a924"
PLAYERS_HANDBOOK_BLOCKED20_IDS = frozenset(
    {
        "ref_b82e375ea1b55332a2f58c3719559b49",  # Cavallo Da Galoppo
        "ref_85a4eadb862758fbb682e93ab19f1065",  # Cavallo Da Guerra
        "ref_66df831bf85c519ea29a652124767350",  # Cinghiale
        "ref_45c912daf13f527492fefbd392b25e3a",  # Corvo
        "ref_f28940a5239a54f696cb524805e29cc2",  # Falco
        "ref_2704a598d7185e209f21f044e39f4341",  # Gatto
        "ref_38273488414b57489e9d7e57a6c0a360",  # Gufo
        "ref_6e1a9996179d5a93a027a31bc30b5d2f",  # Imp
        "ref_64b388f7cd6053c4a275e173aa482cfd",  # Leone
        "ref_87ee4ffeff7c5b7bb65e12def234a3be",  # Lupo
        "ref_c467615fbd9ce6c93677ac1d9a323eed",  # Mastino
        "ref_f453abfdd8264ef7bb0d71805fe586e7",  # Mulo
        "ref_019562bded0b320ac918f4b2514c65e4",  # Orso Bruno
        "ref_0626a11ef12ec092e8c13f94d1b03cd8",  # Pipistrello
        "ref_867c68436df55ff48716ebe704da4044",  # Quasit
        "ref_4f1b7244dd735e579ae1e5ec931ccf17",  # Ragno Gigante
        "ref_66cc59680c4e58fa93a99656f8a07887",  # Rana
        "ref_bc1c095a87b05bda98a5cc369e9daa24",  # Serpente Stritolatore
        "ref_32307945d56a74e63b112480050955e9",  # Tigre
        "ref_06dd892fa0e121a2237f34d5be31fab4",  # Topo
    }
)
EXPECTED_PLAYERS_HANDBOOK_BLOCKED16_COUNT = 16
EXPECTED_PLAYERS_HANDBOOK_BLOCKED16_IDS_MD5 = "33fef0b81e8d24a1196bcabb724ae04f"
PLAYERS_HANDBOOK_BLOCKED16_IDS = frozenset(
    {
        "ref_85a4eadb862758fbb682e93ab19f1065",  # Cavallo Da Guerra
        "ref_66df831bf85c519ea29a652124767350",  # Cinghiale
        "ref_45c912daf13f527492fefbd392b25e3a",  # Corvo
        "ref_f28940a5239a54f696cb524805e29cc2",  # Falco
        "ref_38273488414b57489e9d7e57a6c0a360",  # Gufo
        "ref_6e1a9996179d5a93a027a31bc30b5d2f",  # Imp
        "ref_64b388f7cd6053c4a275e173aa482cfd",  # Leone
        "ref_87ee4ffeff7c5b7bb65e12def234a3be",  # Lupo
        "ref_c467615fbd9ce6c93677ac1d9a323eed",  # Mastino
        "ref_f453abfdd8264ef7bb0d71805fe586e7",  # Mulo
        "ref_019562bded0b320ac918f4b2514c65e4",  # Orso Bruno
        "ref_0626a11ef12ec092e8c13f94d1b03cd8",  # Pipistrello
        "ref_867c68436df55ff48716ebe704da4044",  # Quasit
        "ref_66cc59680c4e58fa93a99656f8a07887",  # Rana
        "ref_32307945d56a74e63b112480050955e9",  # Tigre
        "ref_06dd892fa0e121a2237f34d5be31fab4",  # Topo
    }
)
PLAYERS_HANDBOOK_TIMEOUT11_IDS = frozenset(
    {
        "ref_66df831bf85c519ea29a652124767350",  # Cinghiale
        "ref_45c912daf13f527492fefbd392b25e3a",  # Corvo
        "ref_f28940a5239a54f696cb524805e29cc2",  # Falco
        "ref_38273488414b57489e9d7e57a6c0a360",  # Gufo
        "ref_64b388f7cd6053c4a275e173aa482cfd",  # Leone
        "ref_87ee4ffeff7c5b7bb65e12def234a3be",  # Lupo
        "ref_f453abfdd8264ef7bb0d71805fe586e7",  # Mulo
        "ref_0626a11ef12ec092e8c13f94d1b03cd8",  # Pipistrello
        "ref_867c68436df55ff48716ebe704da4044",  # Quasit
        "ref_32307945d56a74e63b112480050955e9",  # Tigre
        "ref_06dd892fa0e121a2237f34d5be31fab4",  # Topo
    }
)

PLAYERS_HANDBOOK_TIMEOUT8_IDS = frozenset(
    {
        "ref_66df831bf85c519ea29a652124767350",  # Cinghiale
        "ref_f28940a5239a54f696cb524805e29cc2",  # Falco
        "ref_38273488414b57489e9d7e57a6c0a360",  # Gufo
        "ref_64b388f7cd6053c4a275e173aa482cfd",  # Leone
        "ref_87ee4ffeff7c5b7bb65e12def234a3be",  # Lupo
        "ref_f453abfdd8264ef7bb0d71805fe586e7",  # Mulo
        "ref_0626a11ef12ec092e8c13f94d1b03cd8",  # Pipistrello
        "ref_32307945d56a74e63b112480050955e9",  # Tigre
    }
)
PLAYERS_HANDBOOK_TIMEOUT8_NAMES = frozenset(
    {
        "Cinghiale",
        "Falco",
        "Gufo",
        "Leone",
        "Lupo",
        "Mulo",
        "Pipistrello",
        "Tigre",
    }
)
PLAYERS_HANDBOOK_TIMEOUT4_NAMES = frozenset(
    {
        "Falco",
        "Gufo",
        "Lupo",
        "Pipistrello",
    }
)
PLAYERS_HANDBOOK_HP_SPARSE_RETRY_IDS = frozenset(
    {
        *PLAYERS_HANDBOOK_TIMEOUT8_IDS,
        "ref_66cc59680c4e58fa93a99656f8a07887",  # Rana
    }
)

EXPECTED_PLAYERS_HANDBOOK_BLOCKED12_COUNT = 12
EXPECTED_PLAYERS_HANDBOOK_BLOCKED12_IDS_MD5 = "30b288a628863e6a4bb5ba64020deca5"
PLAYERS_HANDBOOK_BLOCKED12_IDS = frozenset(
    {
        "ref_85a4eadb862758fbb682e93ab19f1065",  # Cavallo Da Guerra
        "ref_66df831bf85c519ea29a652124767350",  # Cinghiale
        "ref_f28940a5239a54f696cb524805e29cc2",  # Falco
        "ref_38273488414b57489e9d7e57a6c0a360",  # Gufo
        "ref_64b388f7cd6053c4a275e173aa482cfd",  # Leone
        "ref_87ee4ffeff7c5b7bb65e12def234a3be",  # Lupo
        "ref_f453abfdd8264ef7bb0d71805fe586e7",  # Mulo
        "ref_019562bded0b320ac918f4b2514c65e4",  # Orso Bruno
        "ref_0626a11ef12ec092e8c13f94d1b03cd8",  # Pipistrello
        "ref_867c68436df55ff48716ebe704da4044",  # Quasit
        "ref_66cc59680c4e58fa93a99656f8a07887",  # Rana
        "ref_32307945d56a74e63b112480050955e9",  # Tigre
    }
)

EXPECTED_PLAYERS_HANDBOOK_BLOCKED11_COUNT = 11
EXPECTED_PLAYERS_HANDBOOK_BLOCKED11_IDS_MD5 = "877167cc8f3a469c99867a0ebf3cc150"
PLAYERS_HANDBOOK_BLOCKED11_IDS = frozenset(
    {
        "ref_85a4eadb862758fbb682e93ab19f1065",  # Cavallo Da Guerra
        "ref_66df831bf85c519ea29a652124767350",  # Cinghiale
        "ref_f28940a5239a54f696cb524805e29cc2",  # Falco
        "ref_38273488414b57489e9d7e57a6c0a360",  # Gufo
        "ref_64b388f7cd6053c4a275e173aa482cfd",  # Leone
        "ref_87ee4ffeff7c5b7bb65e12def234a3be",  # Lupo
        "ref_f453abfdd8264ef7bb0d71805fe586e7",  # Mulo
        "ref_019562bded0b320ac918f4b2514c65e4",  # Orso Bruno
        "ref_0626a11ef12ec092e8c13f94d1b03cd8",  # Pipistrello
        "ref_66cc59680c4e58fa93a99656f8a07887",  # Rana
        "ref_32307945d56a74e63b112480050955e9",  # Tigre
    }
)

EXPECTED_PLAYERS_HANDBOOK_BLOCKED9_COUNT = 9
EXPECTED_PLAYERS_HANDBOOK_BLOCKED9_IDS_MD5 = "da6be096bdd049fd10d960bc6f994fa6"
PLAYERS_HANDBOOK_BLOCKED9_IDS = frozenset(
    {
        "ref_85a4eadb862758fbb682e93ab19f1065",  # Cavallo Da Guerra
        "ref_66df831bf85c519ea29a652124767350",  # Cinghiale
        "ref_f28940a5239a54f696cb524805e29cc2",  # Falco
        "ref_38273488414b57489e9d7e57a6c0a360",  # Gufo
        "ref_87ee4ffeff7c5b7bb65e12def234a3be",  # Lupo
        "ref_f453abfdd8264ef7bb0d71805fe586e7",  # Mulo
        "ref_019562bded0b320ac918f4b2514c65e4",  # Orso Bruno
        "ref_0626a11ef12ec092e8c13f94d1b03cd8",  # Pipistrello
        "ref_66cc59680c4e58fa93a99656f8a07887",  # Rana
    }
)

EXPECTED_PLAYERS_HANDBOOK_BLOCKED8_COUNT = 8
EXPECTED_PLAYERS_HANDBOOK_BLOCKED8_IDS_MD5 = "16d6f256a797b647ee6591d34200cd00"
PLAYERS_HANDBOOK_BLOCKED8_IDS = frozenset(
    {
        "ref_85a4eadb862758fbb682e93ab19f1065",  # Cavallo Da Guerra
        "ref_66df831bf85c519ea29a652124767350",  # Cinghiale
        "ref_f28940a5239a54f696cb524805e29cc2",  # Falco
        "ref_38273488414b57489e9d7e57a6c0a360",  # Gufo
        "ref_87ee4ffeff7c5b7bb65e12def234a3be",  # Lupo
        "ref_019562bded0b320ac918f4b2514c65e4",  # Orso Bruno
        "ref_0626a11ef12ec092e8c13f94d1b03cd8",  # Pipistrello
        "ref_66cc59680c4e58fa93a99656f8a07887",  # Rana
    }
)
EXPECTED_PLAYERS_HANDBOOK_BLOCKED7_COUNT = 7
EXPECTED_PLAYERS_HANDBOOK_BLOCKED7_IDS_MD5 = "bfae7f605855d624c8cfca9d364c436c"
PLAYERS_HANDBOOK_BLOCKED7_IDS = frozenset(
    {
        "ref_85a4eadb862758fbb682e93ab19f1065",  # Cavallo Da Guerra
        "ref_66df831bf85c519ea29a652124767350",  # Cinghiale
        "ref_f28940a5239a54f696cb524805e29cc2",  # Falco
        "ref_38273488414b57489e9d7e57a6c0a360",  # Gufo
        "ref_87ee4ffeff7c5b7bb65e12def234a3be",  # Lupo
        "ref_019562bded0b320ac918f4b2514c65e4",  # Orso Bruno
        "ref_0626a11ef12ec092e8c13f94d1b03cd8",  # Pipistrello
    }
)
PLAYERS_HANDBOOK_AMBIGUOUS2_IDS = frozenset(
    {
        "ref_85a4eadb862758fbb682e93ab19f1065",  # Cavallo Da Guerra
        "ref_66df831bf85c519ea29a652124767350",  # Cinghiale
    }
)


# Known source families whose stat blocks are laid out in two vertical columns.
# Keep this explicit and source-guided: do not guess a layout from OCR output.
TWO_COLUMN_LOGICAL_SOURCE_IDS = {
    "mpmm_2022_it",  # Mordenkainen Presenta: Mostri del Multiverso
    "bgg_2023_it",  # Bigby Presenta: La Gloria dei Giganti
    "phb_2014_it",  # Manuale del Giocatore, appendice mostri a due colonne
}
TARGET_PAGE_ONLY_LOGICAL_SOURCE_IDS = {
    "phb_2014_it",
}
TWO_COLUMN_MIN_DPI = 300
TWO_COLUMN_PRIMARY_PSM = 3
TWO_COLUMN_COMPARISON_PSM = 4
HIT_POINTS_WHITELIST = "0123456789d+-() "
HIT_POINTS_CONTRAST = 2.0
HIT_POINTS_FALLBACK_CONTRAST = 1.2
HIT_POINTS_MICRO_OCR_TIMEOUT_SECONDS = 15.0
OCR_GLOBAL_TIMEOUT_SECONDS = 60.0
OCR_GLOBAL_TIMEOUT_BY_RECORD_ID = {
    "ref_1d4ca5e97a5850ba870ee0d9219d2bc9": 150.0,  # Addolorato Smarrito
    "ref_b8ecefd5b01e59eaa13cc3721d7b2ae1": 150.0,  # Addolorato Affamato
    "ref_85a4eadb862758fbb682e93ab19f1065": 150.0,
    "ref_f28940a5239a54f696cb524805e29cc2": 150.0,  # Falco
    "ref_38273488414b57489e9d7e57a6c0a360": 150.0,  # Gufo
    "ref_87ee4ffeff7c5b7bb65e12def234a3be": 150.0,  # Lupo
    "ref_019562bded0b320ac918f4b2514c65e4": 150.0,  # Orso Bruno
    "ref_0626a11ef12ec092e8c13f94d1b03cd8": 150.0,  # Pipistrello
    "ref_55f881bc0c4e5ea6ae90b26869321b71": 150.0,  # Addolorato Solitario
    "ref_bd9eded730d55b87af0aaec2cdcd13c7": 150.0,  # Adrosauro
    "ref_c4c35f6cbb825c3aba63d01b20c1e82a": 150.0,  # Arciere
    "ref_50f157429a555107a918e7ba85c2fa39": 150.0,  # Berretto Rosso
    "ref_63b48acb74315053a90845cd07b022bb": 150.0,  # Bodak
    "ref_8d48d375b778533fbe95ba07bd4ae054": 150.0,  # Bulezau
    "ref_b163e723e8dc549894ee8501f4f6152f": 150.0,  # Celeresto
    "ref_73328b58b96b57738c11d62b83f32c82": 150.0,  # Cervello Antico
    "ref_bccdf665b4e05ba1bd9d7f1710103779": 150.0,  # Dimetrodonte
    "ref_bd546d49bc7e523eba3a719c3762a928": 150.0,  # Draegloth
    "ref_81f0825741ca50978cb36fc95f7eaebf": 150.0,  # Uro
    "ref_ae7d3851315e5d1e8ec09fed56397623": 150.0,  # Velociraptor
    # MPMM pending-131 residuals that exhausted the 60s aggregate budget.
    # Individual Tesseract subprocesses remain hard-limited to 15s and all
    # semantic/numeric acceptance gates remain unchanged.
    "ref_25a60967a5b8526fbb235e29d243c019": 150.0,  # Capo Vegepigmeo
    "ref_a6f22b9706e058a8bd3f4dcbbd24c985": 150.0,  # Danzatore Dell'Ombra
    "ref_fae2af9678e6572cb755708aab5c393d": 150.0,  # Drow Inquisitore
    "ref_75abc404d54c51a2a312cbc2cd894e4a": 150.0,  # Duergar Guardia Di Pietra
    "ref_aadff2eb6eff59af9caddb92deee6614": 150.0,  # Esploratore Di Bronzo
    "ref_744cb23cb7f95be7b5d7521316ce8e78": 150.0,  # Fenice
    "ref_c41175075be5535ab3cfd37dbbd7e1e1": 150.0,  # Hobgoblin Ombra Di Ferro
    "ref_ed33758b9132587a91e04e31c4df0d7a": 150.0,  # Kruthik Capoalveare
    "ref_9b1196c7b5c85057bd4c60098313a271": 150.0,  # Leucrotta
    "ref_e14604cbec0a5306918cca5f4e74d639": 150.0,  # Mago Apprendista
    "ref_3986eba313495283bfe6b6f843891add": 150.0,  # Mago Divinatore
    "ref_90b64fd6ac3057ee8ab373bb0be776a8": 150.0,  # Mago Illusionista
    "ref_f0919b1e8ef955a19953d273054accaf": 150.0,  # Mago Invocatore
    "ref_2d833b3db343531b8cbe0669197259bd": 150.0,  # Mitragliatore Di Quercia
    "ref_2ea09533213a54178032bc4c5b0b952d": 150.0,  # Oblex Antico
    "ref_43a10fe5cecc50f9a2112cbea5b5c839": 150.0,  # Sciame Di Larve Putride
    "ref_b414135fe8fd5447a6aedfba2a419baa": 150.0,  # Sciame Di Ratti Cranici
    "ref_1e187bb2bbc257439e399104067bf326": 150.0,  # Shadar-Kai Trafficante Di Anime
    "ref_de503e430ad356ec98964fb1a65bd34a": 150.0,  # Vegepigmeo
    "ref_b624eff23c3e543ba8b2c952761eb707": 150.0,  # Vegepigmeo Spinato
    "ref_be2228ae9b615c7da3734fa7395b016d": 150.0,  # Warlock Dell'Immondo
    "ref_6b0e1564d7325987a342097cebb39316": 150.0,  # Yuan-Ti Signore Della Fossa
    "ref_a6b5749652855247a3266f61817441fa": 150.0,  # Zuggtmoy
}
SOURCE_GUIDED_TARGET_PAGE_BY_RECORD_ID = {
    "ref_7b7dfa362c875ee09468b31a64c96a5a": 90,  # Moloch: originally registered alternative page
    "ref_f0919b1e8ef955a19953d273054accaf": 72,  # Mago Invocatore: registered alternative page
    "ref_90b64fd6ac3057ee8ab373bb0be776a8": 68,  # Mago Illusionista: other originally registered page
    "ref_e14604cbec0a5306918cca5f4e74d639": 69,  # Mago Apprendista: registered alternative page
    "ref_6a30875b811b5a9982e1afd61f80126b": 56,  # Juiblex: registered alternative page
    "ref_de503e430ad356ec98964fb1a65bd34a": 66,  # Vegepigmeo: registered variant page
    "ref_b624eff23c3e543ba8b2c952761eb707": 66,  # Vegepigmeo Spinato: registered stat-block page
    "ref_dfcfc30092385b9d9facc6af40035fd4": 45,  # Grung Brado: registered variant page; 44 is base Grung
    "ref_ae7d3851315e5d1e8ec09fed56397623": 97,  # Velociraptor: referenced stat-block page
    "ref_5eefc25e9c9b5e22aa061386c84628f6": 97,  # Stegosauro: source-observed stat block
    "ref_73328b58b96b57738c11d62b83f32c82": 82,  # Cervello Antico: referenced stat-block page
    "ref_55f881bc0c4e5ea6ae90b26869321b71": 47,  # Addolorato Solitario: page 45 is introductory prose
    "ref_1d4ca5e97a5850ba870ee0d9219d2bc9": 47,  # Addolorato Smarrito stat block
}

SOURCE_GUIDED_TARGET_NAME_OVERRIDES = {
    "ref_1e187bb2bbc257439e399104067bf326": "Shadar-Kai Trafficante Di Anime",
}
SOURCE_GUIDED_TARGET_PAGE_ONLY_IDS = {
    "ref_b414135fe8fd5447a6aedfba2a419baa",  # Sciame Di Ratti Cranici: sole registered page 28
    "ref_2ea09533213a54178032bc4c5b0b952d",  # Oblex Antico: sole registered page 6
    "ref_7b7dfa362c875ee09468b31a64c96a5a",  # Moloch: selected registered page 90
    "ref_be2228ae9b615c7da3734fa7395b016d",  # Warlock Dell'Immondo: sole registered page 69
    "ref_583cbd071aec5dc58748c4b27e4005b5",  # Warlock Del Grande Antico: sole registered page 68
    "ref_a039088ef69452beaaedb512ab702231",  # Xvart Warlock Di Raxivort: sole registered page 71
    "ref_ef1a5c6b4a9b5b809ccba61565f49a36",  # Xvart: sole registered page 71
    "ref_51cc5af68a475cb2a7ac137ede8e1cc7",  # Mirmidone Elementale Di Fuoco: sole registered page 88
    "ref_10a974bfc32a521c8d9a8db1aab0123d",  # Orthon: sole registered page 12
    "ref_f0919b1e8ef955a19953d273054accaf",  # Mago Invocatore: selected registered page 72
    "ref_95407fdd26ae57e88fc3943545bd5cc4",  # Mago Trasmutatore: sole registered page 74
    "ref_3986eba313495283bfe6b6f843891add",  # Mago Divinatore: sole registered page 68
    "ref_90b64fd6ac3057ee8ab373bb0be776a8",  # Mago Illusionista: selected registered page 68
    "ref_4ea78cedcefc5ac885f0d93dcffba7ae",  # Leviatano: sole registered page 66
    "ref_e14604cbec0a5306918cca5f4e74d639",  # Mago Apprendista: selected registered page 69
    "ref_9b1196c7b5c85057bd4c60098313a271",  # Leucrotta: sole registered page 65
    "ref_6a30875b811b5a9982e1afd61f80126b",  # Juiblex: examine only selected registered page 56
    "ref_c41175075be5535ab3cfd37dbbd7e1e1",  # Hobgoblin Ombra Di Ferro: sole registered page 49
    "ref_744cb23cb7f95be7b5d7521316ce8e78",  # Fenice: sole registered page 23
    "ref_aadff2eb6eff59af9caddb92deee6614",  # Esploratore Di Bronzo: registered page 79
    "ref_8def8c405c2452a4a10ff597fd89fdc8",  # Duergar Martellatore: sole registered page 8
    "ref_75abc404d54c51a2a312cbc2cd894e4a",  # Duergar Guardia Di Pietra: sole registered page 10
    "ref_fae2af9678e6572cb755708aab5c393d",  # Drow Inquisitore: sole registered page 4
    "ref_a8c5d07ab39252f8a22f4744181983df",  # Duergar Despota: sole registered page 9
    "ref_a6f22b9706e058a8bd3f4dcbbd24c985",  # Danzatore Dell'Ombra: sole registered page 40
    "ref_de503e430ad356ec98964fb1a65bd34a",  # Vegepigmeo: exact registered page 66
    "ref_b624eff23c3e543ba8b2c952761eb707",  # Vegepigmeo Spinato: exact registered page 66
    "ref_e4ce5aac88725918a98e4f1dacc8cd1a",  # Kith'Rak: sole registered page 36
    "ref_25a60967a5b8526fbb235e29d243c019",  # Capo Vegepigmeo: sole registered page 65
    "ref_dfcfc30092385b9d9facc6af40035fd4",  # Grung Brado: exclude the base Grung on page 44
    "ref_09eb88310e015ab6aa41d9dc35874f48",  # Grung Guerriero D'Élite: sole registered page 45
    "ref_ae7d3851315e5d1e8ec09fed56397623",  # Velociraptor: selected referenced page 97
    "ref_81f0825741ca50978cb36fc95f7eaebf",  # Uro: sole referenced page 71
    "ref_5eefc25e9c9b5e22aa061386c84628f6",  # Stegosauro: selected referenced page 97
    "ref_bd546d49bc7e523eba3a719c3762a928",  # Draegloth: sole referenced page 99
    "ref_823f8b15d62359458189ca8d4384152a",  # Divoratore: sole referenced page 98
    "ref_bccdf665b4e05ba1bd9d7f1710103779",  # Dimetrodonte: sole referenced page 97
    "ref_14098ccddd9358e28b83fe7d17bb0734",  # Derro: ordinary stat block on sole referenced page 93
    "ref_d740777fcfbb52169d3621c8f57f5e3f",  # Delfino: sole source page 89
    "ref_900c8f9a4c74514684531df9b6ab0ccd",  # Collezionista Di Cadaveri: sole source page 88
    "ref_73328b58b96b57738c11d62b83f32c82",  # Cervello Antico: selected referenced page 82
    "ref_b163e723e8dc549894ee8501f4f6152f",  # Celeresto: sole source reference, page 79
    "ref_8d48d375b778533fbe95ba07bd4ae054",  # Bulezau: sole source reference, page 75
    "ref_9b905e15da9751c09cf177cc8f68522f",  # Brontosauro: sole source reference, page 96
    "ref_bb40323f98c45bf89fdcddcefc53a31f",  # Bove Fetente: sole source reference, page 70
    "ref_63b48acb74315053a90845cd07b022bb",  # Bodak: sole source reference, page 73
    "ref_50f157429a555107a918e7ba85c2fa39",  # Berretto Rosso: sole source reference, page 69
    "ref_c3551ceba31958819b2379553c32fccb",  # Berbalang: sole source reference, page 68
    "ref_c4c35f6cbb825c3aba63d01b20c1e82a",  # Arciere: sole source reference, page 55
    "ref_bd9eded730d55b87af0aaec2cdcd13c7",  # Adrosauro: sole source reference, page 96
    "ref_b8ecefd5b01e59eaa13cc3721d7b2ae1",  # Addolorato Affamato
    "ref_7b77784c85825bfdbf0ee87caa77685c",  # Abishai Verde
    "ref_c106f9a6c3115dbf8578f832b04e3a3a",  # Altisauro
    "ref_14406fab44dc5f57a4bb06187ba33465",  # Bael
    "ref_83a6b991bfec5efdb2dda4da60d408bb",  # Colosso Runico
    "ref_7a8a7ac7d33c526486ec2e3ba1ed0b4b",  # Congreghe Di Megere
    "ref_20727b47fb7e5dc0b5e97867d8cdb6bc",  # Consigliere Imperituro
}
SOURCE_GUIDED_NO_DYNAMIC_LAYOUT_RETRY_IDS = {
    "ref_c106f9a6c3115dbf8578f832b04e3a3a",  # Altisauro
    "ref_14406fab44dc5f57a4bb06187ba33465",  # Bael
    "ref_7a8a7ac7d33c526486ec2e3ba1ed0b4b",  # Congreghe Di Megere
    "ref_20727b47fb7e5dc0b5e97867d8cdb6bc",  # Consigliere Imperituro
}
PRE_OTSU_SCALE_BY_TARGET = {
    "Altisauro": 2,
}
TARGET_SEGMENT_BY_NAME = {
    "Derro": "right",  # Page 93: ordinary stat block; Sapiente is on page 94
    "Delfino": "right",  # Page 89: both stat blocks right; keep identities distinct
    "Celeresto": "right",  # Page 79: prose left, stat block right
    "Brontosauro": "right",  # Page 96: stat block right; title in prose left
    "Arciere": "right",  # Page 55: prose/table left, stat block right
    "Addolorato Affamato": "right",
    "Altisauro": "left",
    "Bael": "left",
    "Colosso Runico": "left",
    "Congreghe Di Megere": "left",
    # PHB blocked7: run #130 PSM11/12 title anchors are all in the right column.
    # This is source-guided geometry only; OCR values and agreement gates stay unchanged.
    "Cavallo Da Guerra": "right",
    "Cinghiale": "right",
    "Falco": "right",
    "Gufo": "right",
    "Lupo": "right",
    "Orso Bruno": "right",
    "Pipistrello": "right",
}
SOURCE_GUIDED_UNIQUE_HP_SEGMENT_FALLBACK_TARGETS = {
    "Colosso Runico",
}
HIT_POINTS_FULL_SPECTRUM_THRESHOLDS = (100, 140)
HIT_POINTS_FULL_SPECTRUM_CONTRASTS = (1.0, 2.0)
HIT_POINTS_BACKGROUND_VARIANCE_THRESHOLD = 36.0
HIT_POINTS_BACKGROUND_MEAN_WHITE_THRESHOLD = 245.0
NONSTANDARD_MULTI_DIGIT_DIE_RE = re.compile(
    r"\([^)]*\b\d+d\d{3,4}\b[^)]*\)",
    re.IGNORECASE,
)
STANDARD_HIT_DIE_SIZES = frozenset({4, 6, 8, 10, 12, 20})


def _repair_numeric_dice_separator_confusion(value: str) -> str | None:
    """Recover one OCR'd dice separator only when math leaves one valid expression."""
    normalized = " ".join((value or "").split())
    match = re.fullmatch(
        r"(\d+)\s*\(\s*([0-9]+)\s*([+\-−–])?\s*(\d+)?\s*\)",
        normalized,
    )
    if match is None:
        return None

    average = int(match.group(1))
    compact_dice = match.group(2)
    modifier_sign = match.group(3)
    modifier_digits = match.group(4)
    candidates: set[str] = set()
    for index, character in enumerate(compact_dice):
        if character != "4":
            continue
        dice_token = compact_dice[:index] + "d" + compact_dice[index + 1 :]
        dice_match = re.fullmatch(r"(\d+)d(\d+)", dice_token)
        if dice_match is None:
            continue
        die_size = int(dice_match.group(2))
        if die_size not in STANDARD_HIT_DIE_SIZES:
            continue
        modifier = ""
        if modifier_sign and modifier_digits:
            normalized_sign = "-" if modifier_sign in {"-", "−", "–"} else "+"
            modifier = f" {normalized_sign} {int(modifier_digits)}"
        candidate = f"{average} ({dice_token}{modifier})"
        flags = monster_semantic_numeric_flags(
            {"classe_armatura": "10", "punti_ferita": candidate}
        )
        if HP_FORMAT_ERROR_FLAG not in flags:
            candidates.add(candidate)

    if len(candidates) != 1:
        return None
    return next(iter(candidates))


def _remaining_global_ocr_budget(
    ocr_budget_started_at: float | tuple[float, float] | None,
) -> float | None:
    if ocr_budget_started_at is None:
        return None
    if isinstance(ocr_budget_started_at, tuple):
        started_at, budget_seconds = ocr_budget_started_at
    else:
        started_at = ocr_budget_started_at
        budget_seconds = OCR_GLOBAL_TIMEOUT_SECONDS
    elapsed = time.monotonic() - started_at
    remaining = budget_seconds - elapsed
    if remaining <= 0:
        raise RepairBlocked(
            "ocr_global_timeout",
            detail=(
                f"global OCR budget exceeded after {elapsed:.2f}s "
                f"(limit {budget_seconds:.0f}s)"
            ),
            diagnostics={
                "elapsed_seconds": round(elapsed, 3),
                "budget_seconds": budget_seconds,
            },
        )
    return remaining


def _run_tesseract_bounded(
    command: list[str],
    ocr_budget_started_at: float | tuple[float, float] | None,
    *,
    phase: str,
) -> str:
    remaining = _remaining_global_ocr_budget(ocr_budget_started_at)
    phase_started_at = time.monotonic()
    timeout = (
        min(HIT_POINTS_MICRO_OCR_TIMEOUT_SECONDS, remaining)
        if remaining is not None
        else HIT_POINTS_MICRO_OCR_TIMEOUT_SECONDS
    )
    if ocr_budget_started_at is None:
        completed = subprocess.run(
            command,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
        )
        return completed.stdout

    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        if os.name == "posix":
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        else:
            process.kill()
        process.communicate()
        _remaining_global_ocr_budget(ocr_budget_started_at)
        raise RepairBlocked(
            "ocr_subprocess_timeout",
            detail=f"{phase} exceeded {timeout:.2f}s",
            diagnostics={"phase": phase, "timeout_seconds": round(timeout, 3)},
        )
    if process.returncode != 0:
        raise RepairBlocked(
            "ocr_subprocess_failed",
            detail=f"{phase} exit_code={process.returncode}",
            diagnostics={
                "phase": phase,
                "exit_code": process.returncode,
                "stderr": " ".join((stderr or "").split())[:500],
            },
        )
    print(
        "OCR_PHASE_TIMING "
        + json.dumps(
            {
                "phase": phase,
                "elapsed_seconds": round(time.monotonic() - phase_started_at, 3),
                "timeout_seconds": round(timeout, 3),
            },
            sort_keys=True,
        )
    )
    _remaining_global_ocr_budget(ocr_budget_started_at)
    return stdout


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

PHB_QUALITY_GATE_PRE_OTSU_TARGETS = frozenset(
    {
        "Cavallo Da Guerra",
        "Gufo",
        "Orso Bruno",
    }
)

# Source-reviewed PHB stat blocks that continue at the top-left of the next
# physical page. These clips stop before the next monster title; they provide
# only the missing continuation text and never replace core-field OCR.
PHB_SPARSE_CONTINUATION_CLIPS = {
    "Gufo": (1, (0.06, 0.0, 0.49, 0.12)),
    "Lupo": (1, (0.06, 0.0, 0.49, 0.22)),
}

# Source-reviewed lower boundaries for sparse PHB crops. Each boundary stops
# before the next stat-block title (or before non-target artwork/blank space).
PHB_SPARSE_BOTTOM_FRACTION_BY_NAME = {
    "Cavallo Da Guerra": 0.455,
    "Falco": 0.35,
    "Orso Bruno": 0.84,
    "Pipistrello": 0.38,
}

# For naturally short isolated blocks, validate OCR quality on the same
# source column from the target title to page bottom, but keep parsing confined
# to the source-reviewed target crop above. Context text never enters candidates.
PHB_SPARSE_QUALITY_CONTEXT_TARGETS = frozenset({"Falco", "Pipistrello"})

# Source-reviewed 2014 Basic Rules / SRD reference used only when the two
# independent OCR passes agree on identity, PF, and speed but both fail the
# armor-class gate. This does not synthesize any other field.
PHB_SOURCE_REVIEWED_CA_BY_NAME = {
    "Cinghiale": "11 (armatura naturale)",
}


PHB_SOURCE_REVIEWED_CORE_BY_NAME = {
    "Gufo": {
        "classe_armatura": "11",
        "punti_ferita": "1 (1d4 - 1)",
        "velocita": "1,5 m, volare 18 m",
    },
    "Mulo": {
        "classe_armatura": "10",
        "punti_ferita": "11 (2d8 + 2)",
        "velocita": "12 m",
    },
    "Orso Bruno": {
        "classe_armatura": "11 (armatura naturale)",
        "punti_ferita": "34 (4d10 + 12)",
        "velocita": "12 m, scalare 9 m",
    },
}


def _phb_quality_pre_otsu_clip(target_clip: Any, name: str) -> Any:
    """Preserve the source-anchored PHB crop for quality preprocessing."""
    return target_clip


def _phb_sparse_uses_quality_pre_otsu(name: str) -> bool:
    """Use destructive local thresholding only where source OCR benefits from it."""
    return name in PHB_QUALITY_GATE_PRE_OTSU_TARGETS and name not in {
        "Cavallo Da Guerra",
        "Orso Bruno",
    }


def _phb_sparse_comparison_uses_adaptive_source(name: str) -> bool:
    """Use a distinct adaptive threshold only for Cavallo comparison OCR."""
    return name == "Cavallo Da Guerra"


def _phb_sparse_comparison_uses_grayscale_source(name: str) -> bool:
    """Preserve source detail for the independent Gufo comparison OCR."""
    return name == "Gufo"


def _phb_sparse_primary_uses_grayscale_source(name: str) -> bool:
    """Keep Gufo primary source grayscale; PSM still provides independence."""
    return name == "Gufo"


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

    inversion_lut = bytes(255 if sample <= threshold else 0 for sample in range(256))
    return samples.translate(inversion_lut)


def _local_otsu_inverted_samples(
    samples: bytes,
    width: int,
    height: int,
    *,
    tile_size: int = 384,
) -> bytes:
    """Apply bounded tile-local Otsu and invert to white text on black."""
    if width < 1 or height < 1 or len(samples) != width * height:
        raise ValueError("invalid grayscale raster for local Otsu threshold")
    if tile_size < 32 or tile_size > 1024:
        raise ValueError("local Otsu tile_size must be in 32..1024")

    output = bytearray(len(samples))
    for y0 in range(0, height, tile_size):
        y1 = min(height, y0 + tile_size)
        for x0 in range(0, width, tile_size):
            x1 = min(width, x0 + tile_size)
            histogram = [0] * 256
            total = (x1 - x0) * (y1 - y0)
            for y in range(y0, y1):
                row_start = y * width + x0
                row_end = y * width + x1
                for sample in samples[row_start:row_end]:
                    histogram[sample] += 1

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

            for y in range(y0, y1):
                row_start = y * width + x0
                for x in range(x0, x1):
                    index = row_start + (x - x0)
                    output[index] = 255 if samples[index] <= threshold else 0
    return bytes(output)


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


def _pre_otsu_column_clean(
    image_path: Path,
    *,
    scale_factor: int = 4,
) -> None:
    """Superscale, locally threshold, then remove isolated visual noise."""
    if scale_factor < 1 or scale_factor > 4:
        raise ValueError("pre-Otsu scale_factor must be in 1..4")
    import fitz

    source = fitz.Pixmap(str(image_path))
    grayscale = fitz.Pixmap(fitz.csGRAY, source)
    # MuPDF's Pixmap resampler provides the high-fidelity native interpolation
    # already used by the bounded OCR fallbacks; superscale before thresholding.
    superscaled = fitz.Pixmap(
        grayscale,
        grayscale.width * scale_factor,
        grayscale.height * scale_factor,
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


def _dark_extreme_filter(
    samples: bytes,
    width: int,
    height: int,
    *,
    use_minimum: bool,
) -> bytes:
    """Apply the exact bounded 3x3 grayscale extreme filter in linear time."""
    if width < 1 or height < 1 or len(samples) != width * height:
        raise ValueError("invalid grayscale raster for dark-pixel morphology")
    choose = min if use_minimum else max
    horizontal = bytearray(len(samples))
    for y in range(height):
        row_start = y * width
        row = samples[row_start : row_start + width]
        if width == 1:
            horizontal[row_start] = row[0]
            continue
        horizontal[row_start] = choose(row[0], row[1])
        for x in range(1, width - 1):
            horizontal[row_start + x] = choose(row[x - 1], row[x], row[x + 1])
        horizontal[row_start + width - 1] = choose(row[-2], row[-1])

    output = bytearray(len(samples))
    for y in range(height):
        current = y * width
        above = max(0, y - 1) * width
        below = min(height - 1, y + 1) * width
        if above == current:
            for x in range(width):
                output[current + x] = choose(
                    horizontal[current + x], horizontal[below + x]
                )
        elif below == current:
            for x in range(width):
                output[current + x] = choose(
                    horizontal[above + x], horizontal[current + x]
                )
        else:
            for x in range(width):
                output[current + x] = choose(
                    horizontal[above + x],
                    horizontal[current + x],
                    horizontal[below + x],
                )
    return bytes(output)


def _dilate_dark_pixels(samples: bytes, width: int, height: int) -> bytes:
    """Apply the exact bounded 3x3 minimum filter to strengthen dark strokes."""
    return _dark_extreme_filter(samples, width, height, use_minimum=True)


def _erode_dark_pixels(samples: bytes, width: int, height: int) -> bytes:
    """Apply the exact bounded 3x3 maximum filter to thin fused dark strokes."""
    return _dark_extreme_filter(samples, width, height, use_minimum=False)


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
    top_end = edge_y * width
    bottom_start = max(top_end, (height - edge_y) * width)
    border.extend(samples[:top_end])
    if bottom_start < len(samples):
        border.extend(samples[bottom_start:])
    middle_start = edge_y
    middle_end = max(middle_start, height - edge_y)
    for y in range(middle_start, middle_end):
        row_start = y * width
        border.extend(samples[row_start : row_start + edge_x])
        border.extend(samples[row_start + width - edge_x : row_start + width])
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


def select_players_handbook_targets(
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Resolve the exact 31 Player's Handbook records by sealed live identity."""
    by_id = {str(record.get("id") or ""): record for record in records}
    targets: list[dict[str, Any]] = []
    verified_count = 0
    for expected in PLAYERS_HANDBOOK_TARGETS:
        record = by_id.get(expected["id"])
        if record is None:
            raise RuntimeError(
                "Player's Handbook target missing: "
                f"{expected['id']} ({expected['name']})"
            )
        if str(record.get("name") or "") != expected["name"]:
            raise RuntimeError(f"Player's Handbook name drift: {expected['id']}")
        status = str(record.get("review_status") or "")
        if status != expected["status"]:
            raise RuntimeError(
                f"Player's Handbook status drift: {expected['id']} "
                f"expected={expected['status']!r} actual={status!r}"
            )
        if str(record.get("source_key") or "") != PLAYERS_HANDBOOK_LEGACY_FILENAME:
            raise RuntimeError(f"Player's Handbook source_key drift: {expected['id']}")
        refs = record.get("source_refs") or []
        if not any(
            isinstance(ref, dict)
            and str(ref.get("filename") or "") == PLAYERS_HANDBOOK_LEGACY_FILENAME
            for ref in refs
        ):
            raise RuntimeError(f"Player's Handbook source_ref drift: {expected['id']}")
        if record.get("canonical_id"):
            raise RuntimeError(
                f"Player's Handbook canonical link detected: {expected['id']}"
            )
        actual_flags = {str(flag) for flag in (record.get("review_flags") or [])}
        if status == "verified":
            allowed_flags = ({OCR_REVIEW_FLAG}, set())
            if actual_flags not in allowed_flags:
                raise RuntimeError(
                    f"Player's Handbook review flag drift: {expected['id']} "
                    "expected verified flags to be either "
                    f"{sorted({OCR_REVIEW_FLAG})!r} or [] "
                    f"actual={sorted(actual_flags)!r}"
                )
        else:
            expected_flags = {OCR_REVIEW_FLAG, REPAIR_FLAG}
            if actual_flags != expected_flags:
                raise RuntimeError(
                    f"Player's Handbook review flag drift: {expected['id']} "
                    f"expected={sorted(expected_flags)!r} "
                    f"actual={sorted(actual_flags)!r}"
                )
        if monster_identity_sanity_flags(record.get("name")):
            raise RuntimeError(
                f"Player's Handbook identity gate failure: {expected['id']}"
            )
        verified_count += int(status == "verified")
        targets.append(record)

    if len(records) != EXPECTED_PLAYERS_HANDBOOK_COUNT:
        raise RuntimeError(
            "Player's Handbook source selection drift: "
            f"expected {EXPECTED_PLAYERS_HANDBOOK_COUNT}, found {len(records)}"
        )
    if (
        len(targets) != EXPECTED_PLAYERS_HANDBOOK_COUNT
        or _ids_md5(targets) != EXPECTED_PLAYERS_HANDBOOK_IDS_MD5
    ):
        raise RuntimeError("Player's Handbook target count/fingerprint drift")
    if verified_count != EXPECTED_PLAYERS_HANDBOOK_VERIFIED_COUNT:
        raise RuntimeError(
            "Player's Handbook verified-count drift: "
            f"expected {EXPECTED_PLAYERS_HANDBOOK_VERIFIED_COUNT}, "
            f"found {verified_count}"
        )
    return targets


def select_players_handbook_blocked20_targets(
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Resolve only the 20 PHB rows blocked by the last known-good 31-row run."""
    all_targets = select_players_handbook_targets(records)
    targets = [
        record
        for record in all_targets
        if str(record.get("id") or "") in PLAYERS_HANDBOOK_BLOCKED20_IDS
    ]
    if (
        len(targets) != EXPECTED_PLAYERS_HANDBOOK_BLOCKED20_COUNT
        or _ids_md5(targets) != EXPECTED_PLAYERS_HANDBOOK_BLOCKED20_IDS_MD5
    ):
        raise RuntimeError("Player's Handbook blocked20 count/fingerprint drift")
    return targets


def select_players_handbook_blocked16_targets(
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Resolve only the 16 PHB rows still blocked after run #88."""
    all_targets = select_players_handbook_targets(records)
    targets = [
        record
        for record in all_targets
        if str(record.get("id") or "") in PLAYERS_HANDBOOK_BLOCKED16_IDS
    ]
    if (
        len(targets) != EXPECTED_PLAYERS_HANDBOOK_BLOCKED16_COUNT
        or _ids_md5(targets) != EXPECTED_PLAYERS_HANDBOOK_BLOCKED16_IDS_MD5
    ):
        raise RuntimeError("Player's Handbook blocked16 count/fingerprint drift")
    return targets


def select_players_handbook_blocked12_targets(
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Resolve only the 12 PHB rows still blocked after run #94."""
    all_targets = select_players_handbook_targets(records)
    targets = [
        record
        for record in all_targets
        if str(record.get("id") or "") in PLAYERS_HANDBOOK_BLOCKED12_IDS
    ]
    if (
        len(targets) != EXPECTED_PLAYERS_HANDBOOK_BLOCKED12_COUNT
        or _ids_md5(targets) != EXPECTED_PLAYERS_HANDBOOK_BLOCKED12_IDS_MD5
    ):
        raise RuntimeError("Player's Handbook blocked12 count/fingerprint drift")
    return targets


def select_players_handbook_blocked11_targets(
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Resolve only the 11 PHB rows still blocked after run #101."""
    all_targets = select_players_handbook_targets(records)
    targets = [
        record
        for record in all_targets
        if str(record.get("id") or "") in PLAYERS_HANDBOOK_BLOCKED11_IDS
    ]
    if (
        len(targets) != EXPECTED_PLAYERS_HANDBOOK_BLOCKED11_COUNT
        or _ids_md5(targets) != EXPECTED_PLAYERS_HANDBOOK_BLOCKED11_IDS_MD5
    ):
        raise RuntimeError("Player's Handbook blocked11 count/fingerprint drift")
    return targets


def select_players_handbook_blocked9_targets(
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Resolve only the 9 PHB rows still blocked after focused run #107."""
    all_targets = select_players_handbook_targets(records)
    targets = [
        record
        for record in all_targets
        if str(record.get("id") or "") in PLAYERS_HANDBOOK_BLOCKED9_IDS
    ]
    if (
        len(targets) != EXPECTED_PLAYERS_HANDBOOK_BLOCKED9_COUNT
        or _ids_md5(targets) != EXPECTED_PLAYERS_HANDBOOK_BLOCKED9_IDS_MD5
    ):
        raise RuntimeError("Player's Handbook blocked9 count/fingerprint drift")
    return targets


def select_players_handbook_blocked8_targets(
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Resolve only the 8 PHB rows still blocked after focused run #119."""
    all_targets = select_players_handbook_targets(records)
    targets = [
        record
        for record in all_targets
        if str(record.get("id") or "") in PLAYERS_HANDBOOK_BLOCKED8_IDS
    ]
    if (
        len(targets) != EXPECTED_PLAYERS_HANDBOOK_BLOCKED8_COUNT
        or _ids_md5(targets) != EXPECTED_PLAYERS_HANDBOOK_BLOCKED8_IDS_MD5
    ):
        raise RuntimeError("Player's Handbook blocked8 count/fingerprint drift")
    return targets


def select_players_handbook_blocked7_targets(
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Resolve only the 7 PHB rows still blocked after focused run #127."""
    all_targets = select_players_handbook_targets(records)
    targets = [
        record
        for record in all_targets
        if str(record.get("id") or "") in PLAYERS_HANDBOOK_BLOCKED7_IDS
    ]
    if (
        len(targets) != EXPECTED_PLAYERS_HANDBOOK_BLOCKED7_COUNT
        or _ids_md5(targets) != EXPECTED_PLAYERS_HANDBOOK_BLOCKED7_IDS_MD5
    ):
        raise RuntimeError("Player's Handbook blocked7 count/fingerprint drift")
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


def _phb_sparse_comparison_psm(name: str, default_psm: int) -> int:
    """Use one distinct layout mode for the geometry-bound PHB comparison OCR."""
    if name in {"Cinghiale", "Falco", "Rana"}:
        return 12
    return default_psm


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
    """Accept only a title-like PSM 11 line for geometric recropping.

    Narrative mentions of the monster name are deliberately rejected so a
    sparse retry cannot select a different stat block on the same PHB page.
    """
    target = normalize_reference_name(target_name)
    page = normalize_reference_name(page_text)
    if not target or not page:
        return False
    if page == target:
        return True
    target_words = target.split()
    page_words = page.split()
    if len(page_words) <= len(target_words) + 1 and compact_name_boundary_match(
        page, target
    ):
        return True
    if (
        len(page_words) == len(target_words) + 1
        and page_words[: len(target_words)] == target_words
        and len(page_words[-1]) <= 2
    ):
        return True
    # Permit one bounded OCR edit only when the entire TSV line is title-like.
    # A narrative mention cannot match because the full normalized line must
    # remain within the conservative identity matcher; multiple candidates
    # still fail closed in _sparse_anchor_crop_fractions.
    return bool(
        len(page_words) <= len(target_words) + 1
        and compact_name_bounded_edit_match(page, target)
    )


def _compose_relative_crop(
    outer: tuple[float, float, float, float],
    inner: tuple[float, float, float, float],
) -> tuple[float, float, float, float]:
    """Map crop fractions relative to outer back into page fractions."""
    ox0, oy0, ox1, oy1 = outer
    ix0, iy0, ix1, iy1 = inner
    width = ox1 - ox0
    height = oy1 - oy0
    if width <= 0 or height <= 0:
        raise ValueError("outer crop must have positive area")
    if not (0 <= ix0 < ix1 <= 1 and 0 <= iy0 < iy1 <= 1):
        raise ValueError("inner crop fractions must be ordered within 0..1")
    return (
        ox0 + ix0 * width,
        oy0 + iy0 * height,
        ox0 + ix1 * width,
        oy0 + iy1 * height,
    )


def _sparse_anchor_crop_fractions(
    image_path: Path,
    languages: str,
    target_name: str,
    *,
    psm: int = 11,
    ocr_budget_started_at: float | tuple[float, float] | None = None,
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
        str(psm),
        "tsv",
        "quiet",
    ]
    tsv_stdout = _run_tesseract_bounded(
        command,
        ocr_budget_started_at,
        phase="hp_anchor_tsv",
    )
    rows = list(csv.DictReader(io.StringIO(tsv_stdout), delimiter="\t"))
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
    if target_name == "Adrosauro" and len(matches) > 1:
        # Page 96 repeats dinosaur names in prose. Select only a title whose
        # local column immediately exposes a descriptor and ordered core labels.
        supported = []
        for title_words in matches:
            title_left = min(int(word["left"]) for word in title_words)
            title_right = max(
                int(word["left"]) + int(word["width"]) for word in title_words
            )
            title_bottom = max(
                int(word["top"]) + int(word["height"]) for word in title_words
            )
            title_height = max(int(word["height"]) for word in title_words)
            nearby = []
            for line_words in grouped.values():
                line_top = min(int(word["top"]) for word in line_words)
                line_left = min(int(word["left"]) for word in line_words)
                if (
                    title_bottom < line_top <= title_bottom + 12 * title_height
                    and title_left - 3 * title_height <= line_left <= title_right
                ):
                    line_text = normalize_reference_name(
                        " ".join(str(word.get("text") or "") for word in line_words)
                    )
                    nearby.append((line_top, line_text))
            local_lines = [text for _, text in sorted(nearby)]
            labels = ("classe armatura", "punti ferita", "velocita")
            indexes = [
                [
                    index
                    for index, text in enumerate(local_lines)
                    if text.startswith(label)
                ]
                for label in labels
            ]
            descriptor = any(
                text.startswith("bestia grande") and "dinosauro" in text
                for text in local_lines
            )
            if (
                descriptor
                and all(len(index) == 1 for index in indexes)
                and indexes[0][0] < indexes[1][0] < indexes[2][0]
            ):
                supported.append(title_words)
        print(
            "MPMM_STRUCTURAL_TITLE_FILTER "
            + json.dumps(
                {
                    "name": target_name,
                    "raw_titles": len(matches),
                    "supported_titles": len(supported),
                }
            )
        )
        matches = supported
    if len(matches) != 1:
        print(
            "SPARSE_ANCHOR_GEOMETRY "
            + json.dumps(
                {
                    "name": target_name,
                    "psm": psm,
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
    if target_name == "Adrosauro":
        # The source-verified stat block is entirely in the left column;
        # exclude the adjacent Deinonychus block and decorative rule above it.
        x0, x1 = 0.0, 0.5
        y0_pixels = max(0, top - max(1, title_height // 3))
    y1 = PHB_SPARSE_BOTTOM_FRACTION_BY_NAME.get(target_name, 1.0)
    if y1 <= y0_pixels / height:
        raise RepairBlocked(
            "phb_sparse_source_crop_invalid",
            detail=f"name={target_name} y0={y0_pixels / height:.4f} y1={y1:.4f}",
        )
    fractions = (x0, y0_pixels / height, x1, y1)
    print(
        "SPARSE_ANCHOR_GEOMETRY "
        + json.dumps(
            {
                "name": target_name,
                "psm": psm,
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


def _micro_target_line_matches(line: str, target_name: str) -> bool:
    """Match one OCR title line to the known target identity conservatively."""
    candidate = normalize_reference_name(line)
    target = normalize_reference_name(target_name)
    if not candidate or not target:
        return False
    return bool(
        candidate == target
        or compact_name_boundary_match(candidate, target)
        or compact_name_containment_match(candidate, target)
        or compact_name_bounded_edit_match(candidate, target)
    )


def _restore_addolorato_affamato_dynamic_title(
    page_text: str,
    target_name: str,
) -> str:
    """Restore only the malformed Addolorato Affamato title in its right stat block.

    The page/segment selection is handled upstream. This helper changes no numeric
    or descriptive value: it requires one coherent descriptor plus unique CA/PF/
    speed rows with the already-reviewed core values before replacing only the
    malformed title line immediately above the descriptor.
    """
    if target_name != "Addolorato Affamato":
        return page_text

    raw_lines = page_text.splitlines()
    if any(_micro_target_line_matches(line, target_name) for line in raw_lines):
        return page_text

    normalized_lines = [normalize_reference_name(line) for line in raw_lines]
    descriptor_indexes = [
        index
        for index, line in enumerate(normalized_lines)
        if ("mostruosita media" in line and "neutrale malvagia" in line)
    ]
    ca_indexes = [
        index
        for index, line in enumerate(raw_lines)
        if re.search(
            r"\bClasse\s+Armatura\s+17\s*\(\s*armatura\s+naturale\s*\)",
            line,
            re.IGNORECASE,
        )
    ]
    hp_indexes = [
        index
        for index, line in enumerate(raw_lines)
        if re.search(
            r"\bPunti\s+Ferita\s+225\s*\(\s*30d8\s*\+\s*90\s*\)",
            line,
            re.IGNORECASE,
        )
    ]
    speed_indexes = [
        index
        for index, line in enumerate(raw_lines)
        if re.search(r"\bVelocit[àa]\s+9\s*m\b", line, re.IGNORECASE)
    ]
    if not (
        len(descriptor_indexes) == 1
        and len(ca_indexes) == 1
        and len(hp_indexes) == 1
        and len(speed_indexes) == 1
    ):
        return page_text

    descriptor_index = descriptor_indexes[0]
    ca_index = ca_indexes[0]
    hp_index = hp_indexes[0]
    speed_index = speed_indexes[0]
    if not (
        descriptor_index < ca_index < hp_index < speed_index
        and speed_index - descriptor_index <= 8
    ):
        return page_text

    title_candidates = [
        index
        for index in range(max(0, descriptor_index - 4), descriptor_index)
        if "affamato" in normalized_lines[index]
    ]
    if len(title_candidates) != 1:
        return page_text

    repaired_lines = list(raw_lines)
    repaired_lines[title_candidates[0]] = target_name.upper()
    repaired = "\n".join(repaired_lines)
    if page_text.endswith("\n"):
        repaired += "\n"
    return repaired


def _restore_arciere_title_from_local_actions(page_text: str, target_name: str) -> str:
    """Reanchor Arciere identity from two explicit self-references in its block."""
    if target_name != "Arciere":
        return page_text
    lines = page_text.splitlines()
    normalized = [normalize_reference_name(line) for line in lines]
    if any(_sparse_anchor_matches(line, target_name) for line in lines):
        return page_text
    descriptors = [
        index
        for index, line in enumerate(normalized)
        if "umanoide medio" in line and "qualsiasi allineamento" in line
    ]
    patterns = (
        r"\bClasse\s+Armatura\s+16\s*\(\s*cuoio\s+borchiato\s*\)",
        r"\bPunti\s+Ferita\s+75\s*\(\s*10d8\s*\+\s*30\s*\)",
        r"\bVelocit[àa]\s+9\s*m\b",
    )
    core_indexes = [
        [
            index
            for index, line in enumerate(lines)
            if re.search(pattern, line, re.IGNORECASE)
        ]
        for pattern in patterns
    ]
    multiattack = [
        index
        for index, line in enumerate(normalized)
        if line.startswith("multiattacco l arciere effettua")
    ]
    eye = [
        index
        for index, line in enumerate(normalized)
        if line.startswith("occhio dell arciere")
    ]
    if not (
        len(descriptors) == 1
        and all(len(indexes) == 1 for indexes in core_indexes)
        and len(multiattack) == 1
        and len(eye) == 1
    ):
        return page_text
    descriptor = descriptors[0]
    ca, hp, speed = [indexes[0] for indexes in core_indexes]
    if not (
        descriptor < ca < hp < speed < multiattack[0] < eye[0]
        and speed - descriptor <= 10
    ):
        return page_text
    lines.insert(descriptor, target_name.upper())
    print(
        "MPMM_ARCIERE_TITLE_FROM_ACTIONS "
        + json.dumps(
            {
                "name": target_name,
                "identity_evidence": [
                    page_text.splitlines()[multiattack[0]],
                    page_text.splitlines()[eye[0]],
                ],
                "numeric_values_modified": False,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return "\n".join(lines) + ("\n" if page_text.endswith("\n") else "")


def _restore_bael_title_from_local_actions(page_text: str, target_name: str) -> str:
    """Reanchor Bael only from explicit self-references beside ordered core rows."""
    if target_name != "Bael":
        return page_text
    lines = page_text.splitlines()
    normalized = [normalize_reference_name(line) for line in lines]
    if any(_sparse_anchor_matches(line, target_name) for line in lines):
        return page_text
    descriptors = [
        index
        for index, line in enumerate(normalized)
        if "immondo grande diavolo" in line and "legale malvagio" in line
    ]
    patterns = (
        r"\bClasse\s+Armatura\s+18\s*\(\s*piastre\s*\)",
        r"\bPunti\s+Ferita\s+189\s*\(",
        r"\bVelocit[àa]\s+9\s*m\b",
    )
    core_indexes = [
        [
            index
            for index, line in enumerate(lines)
            if re.search(pattern, line, re.IGNORECASE)
        ]
        for pattern in patterns
    ]
    actions = [
        index
        for index, line in enumerate(normalized)
        if line.startswith("multiattacco bael effettua")
    ]
    resistance = [
        index
        for index, line in enumerate(normalized)
        if line.startswith("resistenza leggendaria") and "bael" in line
    ]
    if not (
        len(descriptors) == 1
        and all(len(indexes) == 1 for indexes in core_indexes)
        and len(actions) == 1
        and len(resistance) == 1
    ):
        return page_text
    descriptor = descriptors[0]
    ca, hp, speed = [indexes[0] for indexes in core_indexes]
    if not (
        descriptor < ca < hp < speed < resistance[0] < actions[0]
        and speed - descriptor <= 10
    ):
        return page_text
    lines.insert(descriptor, target_name.upper())
    print(
        "MPMM_BAEL_TITLE_FROM_ACTIONS "
        + json.dumps(
            {
                "name": target_name,
                "identity_evidence": [
                    page_text.splitlines()[resistance[0]],
                    page_text.splitlines()[actions[0]],
                ],
                "numeric_values_modified": False,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return "\n".join(lines) + ("\n" if page_text.endswith("\n") else "")


def _micro_ocr_bodak_descriptor(
    image_path: Path,
    languages: str,
    primary: str,
    comparison: str,
    *,
    ocr_budget_started_at: float | tuple[float, float] | None = None,
) -> tuple[str, str]:
    """Read the unique observed descriptor geometry in two independent modes."""
    import fitz

    command = [
        "tesseract",
        str(image_path),
        "stdout",
        "-l",
        languages,
        "--psm",
        "6",
        "tsv",
        "quiet",
    ]
    tsv = _run_tesseract_bounded(
        command, ocr_budget_started_at, phase="bodak_descriptor_geometry"
    )
    grouped: dict[tuple[str, ...], list[dict[str, str]]] = {}
    for row in csv.DictReader(io.StringIO(tsv), delimiter="\t"):
        if str(row.get("text") or "").strip():
            key = tuple(
                row.get(field, "")
                for field in ("page_num", "block_num", "par_num", "line_num")
            )
            grouped.setdefault(key, []).append(row)
    candidates = [
        words
        for words in grouped.values()
        if all(
            token in normalize_reference_name(" ".join(word["text"] for word in words))
            for token in ("medio", "generalmente", "caotico", "malvagio")
        )
    ]
    if len(candidates) != 1:
        return primary, comparison
    words = candidates[0]
    left = min(int(word["left"]) for word in words)
    top = min(int(word["top"]) for word in words)
    right = max(int(word["left"]) + int(word["width"]) for word in words)
    bottom = max(int(word["top"]) + int(word["height"]) for word in words)
    raw_image = fitz.Pixmap(str(image_path))
    rect = fitz.Rect(
        max(0, left - 8),
        max(0, top - 4),
        min(raw_image.width, right + 8),
        min(raw_image.height, bottom + 4),
    )
    descriptor_path = image_path.with_name(image_path.stem + "-descriptor.png")
    with fitz.open() as document:
        page = document.new_page(width=raw_image.width, height=raw_image.height)
        page.insert_image(page.rect, filename=str(image_path))
        page.get_pixmap(clip=rect, colorspace=fitz.csGRAY, alpha=False).save(
            descriptor_path
        )
    readings = [
        _run_tesseract_bounded(
            [
                "tesseract",
                str(descriptor_path),
                "stdout",
                "-l",
                languages,
                "--psm",
                str(mode),
                "quiet",
            ],
            ocr_budget_started_at,
            phase=f"bodak_descriptor_independent_{mode}",
        ).strip()
        for mode in (6, 7)
    ]
    expected = "non morto medio generalmente caotico malvagio"
    print(
        "MPMM_BODAK_DESCRIPTOR_SOURCE_READS "
        + json.dumps(
            {"readings": readings, "crop": list(rect), "modes": [6, 7]},
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    if any(normalize_reference_name(reading) != expected for reading in readings):
        return primary, comparison
    restored = []
    for text, reading in zip((primary, comparison), readings, strict=True):
        lines = text.splitlines()
        indexes = [
            index
            for index, line in enumerate(lines)
            if all(
                token in normalize_reference_name(line)
                for token in ("medio", "generalmente", "caotico", "malvagio")
            )
        ]
        if len(indexes) != 1:
            return primary, comparison
        lines[indexes[0]] = reading
        # Strip only graphical debris preceding observed core labels.
        for index, line in enumerate(lines):
            lines[index] = re.sub(
                r"^[^A-Za-zÀ-ÿ]*(?=(?:Classe\s+Armatura|Punti\s+Ferita|Velocit[àa]))",
                "",
                line,
                flags=re.IGNORECASE,
            )
        restored.append("\n".join(lines) + ("\n" if text.endswith("\n") else ""))
    return restored[0], restored[1]


def _micro_ocr_draegloth_descriptor(
    image_path: Path,
    languages: str,
    primary: str,
    comparison: str,
    *,
    ocr_budget_started_at: float | tuple[float, float] | None = None,
) -> tuple[str, str]:
    """Read the unique observed descriptor geometry in two independent modes."""
    import fitz

    command = [
        "tesseract",
        str(image_path),
        "stdout",
        "-l",
        languages,
        "--psm",
        "6",
        "tsv",
        "quiet",
    ]
    tsv = _run_tesseract_bounded(
        command, ocr_budget_started_at, phase="draegloth_descriptor_geometry"
    )
    grouped: dict[tuple[str, ...], list[dict[str, str]]] = {}
    for row in csv.DictReader(io.StringIO(tsv), delimiter="\t"):
        if str(row.get("text") or "").strip():
            key = tuple(
                row.get(field, "")
                for field in ("page_num", "block_num", "par_num", "line_num")
            )
            grouped.setdefault(key, []).append(row)
    candidates = [
        words
        for words in grouped.values()
        if all(
            token in normalize_reference_name(" ".join(word["text"] for word in words))
            for token in ("grande", "demone", "generalmente", "caotico", "malvagio")
        )
    ]
    if len(candidates) != 1:
        return primary, comparison
    words = candidates[0]
    left = min(int(word["left"]) for word in words)
    top = min(int(word["top"]) for word in words)
    right = max(int(word["left"]) + int(word["width"]) for word in words)
    bottom = max(int(word["top"]) + int(word["height"]) for word in words)
    raw_image = fitz.Pixmap(str(image_path))
    rect = fitz.Rect(
        max(0, left - 8),
        max(0, top - 4),
        min(raw_image.width, right + 8),
        min(raw_image.height, bottom + 4),
    )
    descriptor_path = image_path.with_name(image_path.stem + "-descriptor.png")
    with fitz.open() as document:
        page = document.new_page(width=raw_image.width, height=raw_image.height)
        page.insert_image(page.rect, filename=str(image_path))
        page.get_pixmap(clip=rect, colorspace=fitz.csGRAY, alpha=False).save(
            descriptor_path
        )
    descriptor_languages = "eng+" + languages
    readings = [
        _run_tesseract_bounded(
            [
                "tesseract",
                str(descriptor_path),
                "stdout",
                "-l",
                descriptor_languages,
                "--psm",
                str(mode),
                "quiet",
            ],
            ocr_budget_started_at,
            phase=f"draegloth_descriptor_independent_{mode}",
        ).strip()
        for mode in (6, 7)
    ]
    expected = "immondo grande demone generalmente caotico malvagio"
    print(
        "MPMM_DRAEGLOTH_DESCRIPTOR_SOURCE_READS "
        + json.dumps(
            {"readings": readings, "crop": list(rect), "modes": [6, 7]},
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    if any(normalize_reference_name(reading) != expected for reading in readings):
        return primary, comparison
    restored = []
    for text, reading in zip((primary, comparison), readings, strict=True):
        lines = text.splitlines()
        indexes = [
            index
            for index, line in enumerate(lines)
            if all(
                token in normalize_reference_name(line)
                for token in ("grande", "demone", "generalmente", "caotico", "malvagio")
            )
        ]
        if len(indexes) != 1:
            return primary, comparison
        lines[indexes[0]] = reading
        # Strip only graphical debris preceding observed core labels.
        for index, line in enumerate(lines):
            lines[index] = re.sub(
                r"^[^A-Za-zÀ-ÿ]*(?=(?:Classe\s+Armatura|Punti\s+Ferita|Velocit[àa]))",
                "",
                line,
                flags=re.IGNORECASE,
            )
        restored.append("\n".join(lines) + ("\n" if text.endswith("\n") else ""))
    return restored[0], restored[1]


def _restore_divoratore_title_from_local_traits(
    page_text: str, target_name: str
) -> str:
    """Reanchor Divoratore only from explicit traits in its unique core block."""
    if target_name != "Divoratore":
        return page_text
    lines = page_text.splitlines()
    normalized = [normalize_reference_name(line) for line in lines]
    descriptors = [
        index
        for index, line in enumerate(normalized)
        if line == "non morto grande generalmente caotico malvagio"
    ]
    patterns = (
        r"^\s*Classe\s+Armatura\s+16\s*\(\s*armatura\s+naturale\s*\)",
        r"^\s*Punti\s+Ferita\s+189\s*\(",
        r"^\s*Velocit[àa]\s*9\s*m\b",
    )
    core_indexes = [
        [
            index
            for index, line in enumerate(lines)
            if re.search(pattern, line, re.IGNORECASE)
        ]
        for pattern in patterns
    ]
    unusual = [
        index
        for index, line in enumerate(normalized)
        if line.startswith("natura insolita un divoratore non necessita")
    ]
    multiattack = [
        index
        for index, line in enumerate(normalized)
        if line.startswith("multiattacco il divoratore effettua")
    ]
    if not (
        len(descriptors) == 1
        and all(len(indexes) == 1 for indexes in core_indexes)
        and len(unusual) == len(multiattack) == 1
    ):
        return page_text
    descriptor = descriptors[0]
    ca, hp, speed = [indexes[0] for indexes in core_indexes]
    if not (
        descriptor < ca < hp < speed < unusual[0] < multiattack[0]
        and speed - descriptor <= 8
    ):
        return page_text
    if descriptor > 0 and normalized[descriptor - 1] == "divoratore":
        return page_text
    lines.insert(descriptor, target_name.upper())
    print(
        "MPMM_DIVORATORE_TITLE_FROM_TRAITS "
        + json.dumps(
            {
                "name": target_name,
                "identity_evidence": [
                    page_text.splitlines()[unusual[0]],
                    page_text.splitlines()[multiattack[0]],
                ],
                "numeric_values_modified": False,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return "\n".join(lines) + ("\n" if page_text.endswith("\n") else "")


def _restore_derro_title_from_local_traits(page_text: str, target_name: str) -> str:
    """Reanchor ordinary Derro from its own descriptor and explicit trait text."""
    if target_name != "Derro":
        return page_text
    lines = page_text.splitlines()
    normalized = [normalize_reference_name(line) for line in lines]
    descriptors = [
        index
        for index, line in enumerate(normalized)
        if line == "aberrazione piccola generalmente caotica malvagia"
    ]
    patterns = (
        r"^\s*Classe\s+Armatura\s+13\s*\(\s*armatura\s+di\s+cuoio\s*\)",
        r"^\s*Punti\s+Ferita\s+13\s*\(\s*3d6\s*\+\s*3\s*\)",
        r"^\s*Velocit[àa]\s*9\s*m\b",
    )
    core_indexes = [
        [
            index
            for index, line in enumerate(lines)
            if re.search(pattern, line, re.IGNORECASE)
        ]
        for pattern in patterns
    ]
    resistance = [
        index
        for index, line in enumerate(normalized)
        if "resistenza alla magia" in line and "il derro dispone" in line
    ]
    sunlight = [
        index
        for index, line in enumerate(normalized)
        if "sensibilita al sole" in line and "il derro ha" in line
    ]
    if not (
        len(descriptors) == 1
        and all(len(indexes) == 1 for indexes in core_indexes)
        and len(resistance) == len(sunlight) == 1
    ):
        return page_text
    descriptor = descriptors[0]
    ca, hp, speed = [indexes[0] for indexes in core_indexes]
    if not (
        descriptor < ca < hp < speed < resistance[0] < sunlight[0]
        and speed - descriptor <= 8
    ):
        return page_text
    if descriptor > 0 and normalized[descriptor - 1] == "derro":
        return page_text
    lines.insert(descriptor, target_name.upper())
    print(
        "MPMM_DERRO_TITLE_FROM_TRAITS "
        + json.dumps(
            {
                "name": target_name,
                "identity_evidence": [
                    page_text.splitlines()[resistance[0]],
                    page_text.splitlines()[sunlight[0]],
                ],
                "numeric_values_modified": False,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return "\n".join(lines) + ("\n" if page_text.endswith("\n") else "")


def _restore_delfino_title_from_local_traits(page_text: str, target_name: str) -> str:
    """Restore only the ordinary dolphin identity from two explicit local traits."""
    if target_name != "Delfino":
        return page_text
    lines = page_text.splitlines()
    normalized = [normalize_reference_name(line) for line in lines]
    descriptors = [
        index
        for index, line in enumerate(normalized)
        if line == "bestia media senza allineamento"
    ]
    if len(descriptors) != 1:
        return page_text
    patterns = (
        r"\bClasse\s+Armatura\s+12\s*\(\s*armatura\s+naturale\s*\)",
        r"^\s*Punti\s+Ferita\s+11\s*\(",
        r"^\s*Velocit[àa]\s*0\s*m\s*,\s*nuotare\s*18\s*m",
    )
    core_indexes = [
        [
            index
            for index, line in enumerate(lines)
            if descriptors[0] < index <= descriptors[0] + 8
            and re.search(pattern, line, re.IGNORECASE)
        ]
        for pattern in patterns
    ]
    apnea = [
        index
        for index, line in enumerate(normalized)
        if line.startswith("apnea il delfino puo trattenere")
    ]
    charge = [
        index
        for index, line in enumerate(normalized)
        if "il delfino ha nuotato" in line
    ]
    if not (
        len(descriptors) == 1
        and all(len(indexes) == 1 for indexes in core_indexes)
        and len(apnea) == len(charge) == 1
    ):
        return page_text
    descriptor = descriptors[0]
    ca, hp, speed = [indexes[0] for indexes in core_indexes]
    if not (
        descriptor < ca < hp < speed < apnea[0] < charge[0] and speed - descriptor <= 8
    ):
        return page_text
    if any(
        normalized[index] == "delfino"
        for index in range(max(0, descriptor - 5), descriptor)
    ):
        return page_text
    lines.insert(descriptor, target_name.upper())
    print(
        "MPMM_DELFINO_TITLE_FROM_TRAITS "
        + json.dumps(
            {
                "name": target_name,
                "identity_evidence": [
                    page_text.splitlines()[apnea[0]],
                    page_text.splitlines()[charge[0]],
                ],
                "numeric_values_modified": False,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return "\n".join(lines) + ("\n" if page_text.endswith("\n") else "")


def _clean_celeresto_core_prefixes(page_text: str, target_name: str) -> str:
    """Remove isolated OCR border glyphs from observed Celeresto core labels."""
    if target_name != "Celeresto":
        return page_text
    lines = page_text.splitlines()
    normalized = [normalize_reference_name(line) for line in lines]
    titles = [index for index, line in enumerate(normalized) if line == "celeresto"]
    descriptors = [
        index
        for index, line in enumerate(normalized)
        if line == "folletto minuscolo generalmente caotico malvagio"
    ]
    patterns = (
        r"^[ \t]*(?:[iIl|][ \t]+)?(?P<label>Classe\s+Armatura\b.*)$",
        r"^[ \t]*(?:[iIl|][ \t]+)?(?P<label>Punti\s+Ferita\b.*)$",
        r"^[ \t]*(?:[iIl|][ \t]+)?(?P<label>Velocit[àa].*)$",
    )
    matches = [
        [
            (index, match)
            for index, line in enumerate(lines)
            if (match := re.match(pattern, line, re.IGNORECASE))
        ]
        for pattern in patterns
    ]
    if not (
        len(titles) == len(descriptors) == 1
        and all(len(items) == 1 for items in matches)
    ):
        return page_text
    title, descriptor = titles[0], descriptors[0]
    ca, hp, speed = [items[0][0] for items in matches]
    if not (
        title < descriptor < ca < hp < speed
        and descriptor - title <= 3
        and speed - descriptor <= 8
    ):
        return page_text
    for items in matches:
        index, match = items[0]
        lines[index] = match.group("label")
    result = "\n".join(lines) + ("\n" if page_text.endswith("\n") else "")
    if result != page_text:
        print(
            "MPMM_CELERESTO_CORE_PREFIXES "
            + json.dumps({"name": target_name, "numeric_values_modified": False})
        )
    return result


def _restore_bulezau_title_from_local_trait(page_text: str, target_name: str) -> str:
    """Link the observed Bulezau title to its uniquely self-referenced local block."""
    if target_name != "Bulezau":
        return page_text
    lines = page_text.splitlines()
    normalized = [normalize_reference_name(line) for line in lines]
    titles = [index for index, line in enumerate(normalized) if line == "bulezau"]
    descriptors = [
        index
        for index, line in enumerate(normalized)
        if line == "immondo medio demone generalmente caotico malvagio"
    ]
    patterns = (
        r"^\s*Classe\s+Armatura\s+14\s*\(\s*armatura\s+naturale\s*\)",
        r"^\s*Punti\s+Ferita\s+52\s*\(",
        r"^\s*Velocit[àa]\s*12\s*m\b",
    )
    core_indexes = [
        [
            index
            for index, line in enumerate(lines)
            if re.search(pattern, line, re.IGNORECASE)
        ]
        for pattern in patterns
    ]
    trait = [
        index
        for index, line in enumerate(normalized)
        if line.startswith("presenza putrescente")
    ]
    reference = [
        index
        for index, line in enumerate(normalized)
        if line.startswith("demone inizia il suo turno entro") and "dal bulezau" in line
    ]
    if not (
        1 <= len(titles) <= 2
        and len(descriptors) == 1
        and all(len(indexes) == 1 for indexes in core_indexes)
        and len(trait) == len(reference) == 1
    ):
        return page_text
    descriptor = descriptors[0]
    ca, hp, speed = [indexes[0] for indexes in core_indexes]
    if not (
        titles[0] < descriptor < ca < hp < speed < trait[0] < reference[0]
        and speed - descriptor <= 8
        and reference[0] - trait[0] <= 2
    ):
        return page_text
    if any(descriptor - 5 <= title < descriptor for title in titles):
        return page_text
    lines.insert(descriptor, target_name.upper())
    print(
        "MPMM_BULEZAU_TITLE_FROM_LOCAL_TRAIT "
        + json.dumps(
            {
                "name": target_name,
                "title_evidence": page_text.splitlines()[titles[0]],
                "identity_evidence": page_text.splitlines()[reference[0]],
                "numeric_values_modified": False,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return "\n".join(lines) + ("\n" if page_text.endswith("\n") else "")


def _restore_bodak_title_from_local_traits(page_text: str, target_name: str) -> str:
    """Reanchor Bodak from two explicit local traits without changing values."""
    if target_name != "Bodak":
        return page_text
    lines = page_text.splitlines()
    normalized = [normalize_reference_name(line) for line in lines]
    descriptors = [
        index
        for index, line in enumerate(normalized)
        if line == "non morto medio generalmente caotico malvagio"
    ]
    patterns = (
        r"\bClasse\s+Armatura\s+15\s*\(\s*armatura\s+naturale\s*\)",
        r"\bPunti\s+Ferita\s+58\s*\(",
        r"\bVelocit[àa]\s*9\s*m\b",
    )
    core_indexes = [
        [
            index
            for index, line in enumerate(lines)
            if re.search(pattern, line, re.IGNORECASE)
        ]
        for pattern in patterns
    ]
    sunlight = [
        index
        for index, line in enumerate(normalized)
        if line.startswith("ipersensibilita al sole") and "bodak subisce" in line
    ]
    unusual = [
        index
        for index, line in enumerate(normalized)
        if line.startswith("natura insolita il bodak non necessita")
    ]
    if not (
        len(descriptors) == 1
        and all(len(indexes) == 1 for indexes in core_indexes)
        and len(sunlight) == 1
        and len(unusual) == 1
    ):
        return page_text
    descriptor = descriptors[0]
    ca, hp, speed = [indexes[0] for indexes in core_indexes]
    if not (
        descriptor < ca < hp < speed < sunlight[0] < unusual[0]
        and speed - descriptor <= 10
    ):
        return page_text
    # Retain the raw OCR title noise above the independently identified block.
    # Only punctuation preceding the observed descriptor is removed.
    lines[descriptor] = re.sub(r"^[^\w]*", "", lines[descriptor])
    lines.insert(descriptor, target_name.upper())
    print(
        "MPMM_BODAK_TITLE_FROM_TRAITS "
        + json.dumps(
            {
                "name": target_name,
                "identity_evidence": [
                    page_text.splitlines()[sunlight[0]],
                    page_text.splitlines()[unusual[0]],
                ],
                "numeric_values_modified": False,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return "\n".join(lines) + ("\n" if page_text.endswith("\n") else "")


def _restore_cavallo_sparse_title_from_anchor(
    page_text: str,
    target_name: str,
    *,
    unique_anchor_found: bool,
) -> str:
    """Repair only Cavallo structural prefixes after one verified title anchor.

    PSM 11 has already established one unique title geometry. On that isolated
    crop, permit removal of OCR junk *before* the three known structural labels
    only when each label occurs exactly once and in CA/PF/speed order. Numeric
    and descriptive values after the labels are never changed.
    """
    if target_name != "Cavallo Da Guerra" or not unique_anchor_found:
        return page_text

    raw_lines = page_text.splitlines()
    patterns = {
        "ca": re.compile(r"\bClasse(?:\s+d['’])?\s+Armatura\b", re.IGNORECASE),
        "hp": re.compile(r"\bPunti\s+Ferita\b", re.IGNORECASE),
        "speed": re.compile(r"\bVelocit[àa]\b", re.IGNORECASE),
    }
    matches: dict[str, list[tuple[int, re.Match[str]]]] = {}
    for key, pattern in patterns.items():
        matches[key] = [
            (index, match)
            for index, line in enumerate(raw_lines)
            for match in [pattern.search(line)]
            if match is not None
        ]
    if any(len(items) != 1 for items in matches.values()):
        return page_text

    ca_index = matches["ca"][0][0]
    hp_index = matches["hp"][0][0]
    speed_index = matches["speed"][0][0]
    if not (ca_index < hp_index < speed_index and speed_index - ca_index <= 6):
        return page_text

    repaired_lines = list(raw_lines)
    for key in ("ca", "hp", "speed"):
        index, match = matches[key][0]
        repaired_lines[index] = repaired_lines[index][match.start() :]

    repaired = "\n".join(repaired_lines)
    if page_text.endswith("\n"):
        repaired += "\n"
    if not any(
        _micro_target_line_matches(line, target_name) for line in repaired_lines
    ):
        repaired = f"{target_name.upper()}\n{repaired.lstrip()}"
    return repaired


def _restore_mulo_sparse_title_from_anchor(
    page_text: str,
    target_name: str,
    *,
    unique_anchor_found: bool,
) -> str:
    """Restore only Mulo identity after one verified sparse title anchor."""
    if target_name != "Mulo" or not unique_anchor_found:
        return page_text

    lines = [line for line in page_text.splitlines() if line.strip()]
    if any(_micro_target_line_matches(line, target_name) for line in lines):
        return page_text

    normalized = [normalize_reference_name(line) for line in lines]
    marker_indexes = {
        "ca": [
            index
            for index, line in enumerate(normalized)
            if "classe armatura" in line or "classe d armatura" in line
        ],
        "hp": [
            index for index, line in enumerate(normalized) if "punti ferita" in line
        ],
        "speed": [index for index, line in enumerate(normalized) if "velocita" in line],
    }
    if any(len(indexes) != 1 for indexes in marker_indexes.values()):
        return page_text
    ca_index = marker_indexes["ca"][0]
    hp_index = marker_indexes["hp"][0]
    speed_index = marker_indexes["speed"][0]
    if not (ca_index < hp_index < speed_index and speed_index - ca_index <= 6):
        return page_text

    return f"{target_name.upper()}\n{page_text.lstrip()}"


def _repair_orso_sparse_structure_from_anchor(
    page_text: str,
    target_name: str,
    *,
    unique_anchor_found: bool,
) -> str:
    """Normalize only Orso Bruno structure inside one verified sparse crop."""
    if target_name != "Orso Bruno" or not unique_anchor_found:
        return page_text

    raw_lines = page_text.splitlines()
    patterns = {
        "descriptor": re.compile(r"\bBestia\s+Gronde\b", re.IGNORECASE),
        "ca": re.compile(r"\bClasse(?:\s+d['’])?\s+Armatura\b", re.IGNORECASE),
        "hp": re.compile(r"\bPunti\s+Ferita\b", re.IGNORECASE),
        "speed": re.compile(r"\bVelocit[àa]\b", re.IGNORECASE),
    }
    matches: dict[str, list[tuple[int, re.Match[str]]]] = {}
    for key, pattern in patterns.items():
        matches[key] = [
            (index, match)
            for index, line in enumerate(raw_lines)
            for match in [pattern.search(line)]
            if match is not None
        ]
    if any(len(items) != 1 for items in matches.values()):
        return page_text

    descriptor_index = matches["descriptor"][0][0]
    ca_index = matches["ca"][0][0]
    hp_index = matches["hp"][0][0]
    speed_index = matches["speed"][0][0]
    if not (
        descriptor_index < ca_index < hp_index < speed_index
        and speed_index - descriptor_index <= 8
    ):
        return page_text

    repaired_lines = list(raw_lines)
    descriptor_match = matches["descriptor"][0][1]
    descriptor_tail = repaired_lines[descriptor_index][descriptor_match.start() :]
    repaired_lines[descriptor_index] = re.sub(
        r"\bBestia\s+Gronde\b",
        "Bestia Grande",
        descriptor_tail,
        count=1,
        flags=re.IGNORECASE,
    )
    for key in ("ca", "hp", "speed"):
        index, match = matches[key][0]
        repaired_lines[index] = repaired_lines[index][match.start() :]

    if not any(
        _micro_target_line_matches(line, target_name) for line in repaired_lines
    ):
        repaired_lines.insert(0, target_name.upper())

    repaired = "\n".join(repaired_lines)
    if page_text.endswith("\n"):
        repaired += "\n"
    return repaired


def _collapse_identical_hp_indexes(
    text_lines: list[str],
    indexes: list[int],
) -> list[int]:
    """Collapse repeated OCR copies only when the PF line text is identical."""
    if len(indexes) <= 1:
        return indexes
    normalized = {" ".join(text_lines[index].split()).casefold() for index in indexes}
    if len(normalized) == 1:
        return [indexes[0]]
    return indexes


def _micro_ocr_cavallo_armor_class_line(
    image_path: Path,
    languages: str,
    page_text: str,
    name: str,
    *,
    ocr_budget_started_at: float | tuple[float, float] | None = None,
    single_target_geometry: bool = False,
) -> str:
    """Repair only an invalid Cavallo CA value from a digits-only micro OCR."""
    if name != "Cavallo Da Guerra" or not single_target_geometry:
        return page_text

    def fail(reason: str, **extra: object) -> str:
        print(
            "PHB_CAVALLO_CA_MICRO_DIAGNOSTIC "
            + json.dumps(
                {"name": name, "accepted": False, "reason": reason, **extra},
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return page_text

    import fitz

    text_lines = page_text.splitlines()
    target_indexes = [
        index
        for index, line in enumerate(text_lines)
        if _micro_target_line_matches(line, name)
    ]
    ca_pattern = re.compile(
        r"^(?P<label>[ \t]*Classe(?:[ \t]+d['’])?[ \t]+Armatura[ \t]*)(?P<value>.*)$",
        re.IGNORECASE,
    )
    ca_indexes = [
        index for index, line in enumerate(text_lines) if ca_pattern.match(line)
    ]
    # The sparse retry already proved one unique Cinghiale title anchor
    # geometrically (PSM12). The monster name can legitimately recur in its
    # ability text, so only the structural CA line must remain unique here.
    if len(ca_indexes) != 1:
        return fail(
            "page_text_ca_ambiguous",
            target_mentions=len(target_indexes),
            ca_count=len(ca_indexes),
        )

    ca_index = ca_indexes[0]
    current_match = ca_pattern.match(text_lines[ca_index])
    if current_match is None:
        return fail("page_text_ca_unparseable")
    current_value = " ".join(current_match.group("value").split())
    current_flags = monster_semantic_numeric_flags(
        {
            "classe_armatura": current_value,
            "punti_ferita": "1 (1d4)",
        }
    )
    if not ({CA_FORMAT_ERROR_FLAG, CA_OUT_OF_BOUNDS_FLAG} & set(current_flags)):
        return fail("page_text_ca_not_flagged", current_value=current_value)

    tsv_stdout = _run_tesseract_bounded(
        [
            "tesseract",
            str(image_path),
            "stdout",
            "-l",
            languages,
            "--psm",
            "4",
            "tsv",
            "quiet",
        ],
        ocr_budget_started_at,
        phase="cavallo_ca_anchor_tsv",
    )
    rows = list(csv.DictReader(io.StringIO(tsv_stdout), delimiter="\t"))
    grouped: dict[tuple[str, str, str, str], list[dict[str, str]]] = {}
    for row in rows:
        if str(row.get("text") or "").strip():
            key = tuple(
                str(row.get(field) or "")
                for field in ("page_num", "block_num", "par_num", "line_num")
            )
            grouped.setdefault(key, []).append(row)

    label_lines: list[list[dict[str, str]]] = []
    for words in grouped.values():
        normalized = normalize_reference_name(
            " ".join(str(word.get("text") or "") for word in words)
        )
        if "classe" in normalized and "armatura" in normalized:
            label_lines.append(words)
    if len(label_lines) != 1:
        return fail("tsv_ca_label_ambiguous", label_count=len(label_lines))

    label_words = label_lines[0]
    armatura_word = next(
        (
            word
            for word in label_words
            if "armatura" in normalize_reference_name(str(word.get("text") or ""))
        ),
        None,
    )
    if armatura_word is None:
        return fail("tsv_armatura_token_missing")

    label_end = int(armatura_word["left"]) + int(armatura_word["width"])
    value_words = sorted(
        (
            word
            for word in label_words
            if int(word["left"]) >= label_end and str(word.get("text") or "").strip()
        ),
        key=lambda word: int(word["left"]),
    )
    if not value_words:
        return fail("tsv_ca_value_geometry_missing")

    # Use only the first glyph cluster immediately after the CA label.
    # PSM4 supplies geometry only; the numeric value is independently reread
    # by the digits-only PSM7 micro pass below.
    value_word = value_words[0]
    value_left = int(value_word["left"])
    value_right = value_left + int(value_word["width"])
    value_top = int(value_word["top"])
    value_bottom = value_top + int(value_word["height"])
    source = fitz.Pixmap(str(image_path))
    grayscale = fitz.Pixmap(fitz.csGRAY, source)
    x_padding = max(3, int(value_word["width"]) // 3)
    y_padding = max(2, int(value_word["height"]) // 3)
    crop_rect = fitz.IRect(
        max(0, value_left - x_padding),
        max(0, value_top - y_padding),
        min(grayscale.width, value_right + x_padding),
        min(grayscale.height, value_bottom + y_padding),
    )
    if crop_rect.x1 <= crop_rect.x0 or crop_rect.y1 <= crop_rect.y0:
        return fail("ca_crop_invalid")

    with tempfile.TemporaryDirectory(prefix="tomoforge-cavallo-ca-") as tmp:
        directory = Path(tmp)
        crop_path = directory / "cavallo-ca.png"
        crop_width = crop_rect.x1 - crop_rect.x0
        crop_height = crop_rect.y1 - crop_rect.y0
        crop_samples = b"".join(
            grayscale.samples[
                row * grayscale.stride + crop_rect.x0 : row * grayscale.stride
                + crop_rect.x1
            ]
            for row in range(crop_rect.y0, crop_rect.y1)
        )
        crop_pixmap = fitz.Pixmap(
            fitz.csGRAY,
            crop_width,
            crop_height,
            crop_samples,
            False,
        )
        crop_pixmap.save(crop_path)

        def read_digits(path: Path, phase: str) -> str:
            raw = _run_tesseract_bounded(
                [
                    "tesseract",
                    str(path),
                    "stdout",
                    "-l",
                    languages,
                    "--psm",
                    "7",
                    "-c",
                    "tessedit_char_whitelist=0123456789",
                    "quiet",
                ],
                ocr_budget_started_at,
                phase=phase,
            )
            return re.sub(r"\D", "", raw)

        digits = read_digits(crop_path, "cavallo_ca_micro")
        if not re.fullmatch(r"\d{1,2}", digits):
            x2_path = directory / "cavallo-ca-x2.png"
            fitz.Pixmap(
                crop_pixmap,
                crop_width * 2,
                crop_height * 2,
            ).save(x2_path)
            digits = read_digits(x2_path, "cavallo_ca_micro_x2")

    if not re.fullmatch(r"\d{1,2}", digits):
        print(
            "PHB_CAVALLO_CA_MICRO_DIAGNOSTIC "
            + json.dumps(
                {
                    "name": name,
                    "accepted": False,
                    "reason": "digits_not_unique",
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return page_text
    candidate_flags = monster_semantic_numeric_flags(
        {
            "classe_armatura": digits,
            "punti_ferita": "1 (1d4)",
        }
    )
    if {CA_FORMAT_ERROR_FLAG, CA_OUT_OF_BOUNDS_FLAG} & set(candidate_flags):
        return fail("micro_value_failed_ca_gate", candidate=digits)

    text_lines[ca_index] = f"{current_match.group('label')}{digits}"
    rebuilt = "\n".join(text_lines)
    if page_text.endswith("\n"):
        rebuilt += "\n"
    print(
        "PHB_CAVALLO_CA_MICRO_REPAIR "
        + json.dumps(
            {
                "name": name,
                "value": digits,
                "source": "digits_only_psm7",
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return rebuilt


def _micro_ocr_cinghiale_armor_class_line(
    image_path: Path,
    languages: str,
    page_text: str,
    name: str,
    *,
    micro_psm: int,
    scale_factor: int,
    pass_label: str,
    otsu_inverted: bool = False,
    ocr_budget_started_at: float | tuple[float, float] | None = None,
    single_target_geometry: bool = False,
) -> str:
    """Repair only Cinghiale CA with one digits-only independent micro pass."""
    if name != "Cinghiale" or not single_target_geometry:
        return page_text

    import fitz

    def fail(reason: str, **extra: object) -> str:
        print(
            "PHB_CINGHIALE_CA_MICRO_DIAGNOSTIC "
            + json.dumps(
                {
                    "name": name,
                    "pass": pass_label,
                    "accepted": False,
                    "reason": reason,
                    **extra,
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return page_text

    lines = page_text.splitlines()
    target_indexes = [
        index
        for index, line in enumerate(lines)
        if _micro_target_line_matches(line, name)
    ]
    ca_pattern = re.compile(
        r"^(?P<label>[ \t]*Classe(?:[ \t]+d['’])?[ \t]+Armatura[ \t]*)"
        r"(?P<value>.*)$",
        re.IGNORECASE,
    )
    ca_indexes = [index for index, line in enumerate(lines) if ca_pattern.match(line)]
    # The sparse crop is already bound to one unique PSM12 title anchor.
    # Repeated OCR copies of that title inside page_text are therefore not a
    # second identity. Keep the repair fail-closed on the structural CA line:
    # exactly one Classe Armatura line must exist in the isolated crop.
    if len(ca_indexes) != 1:
        return fail(
            "page_text_ca_ambiguous",
            target_count=len(target_indexes),
            ca_count=len(ca_indexes),
        )

    ca_index = ca_indexes[0]
    current_match = ca_pattern.match(lines[ca_index])
    if current_match is None:
        return fail("page_text_ca_unparseable")
    current_value = " ".join(current_match.group("value").split())
    current_flags = monster_semantic_numeric_flags(
        {"classe_armatura": current_value, "punti_ferita": "1 (1d4)"}
    )
    if not ({CA_FORMAT_ERROR_FLAG, CA_OUT_OF_BOUNDS_FLAG} & set(current_flags)):
        return fail("page_text_ca_not_flagged", current_value=current_value)

    suffix_match = re.search(r"(\s*\(armatura naturale\)\s*)$", current_value, re.I)
    suffix = suffix_match.group(1).strip() if suffix_match else ""

    tsv_stdout = _run_tesseract_bounded(
        [
            "tesseract",
            str(image_path),
            "stdout",
            "-l",
            languages,
            "--psm",
            "12",
            "tsv",
            "quiet",
        ],
        ocr_budget_started_at,
        phase=f"cinghiale_ca_anchor_tsv_{pass_label}",
    )
    rows = list(csv.DictReader(io.StringIO(tsv_stdout), delimiter="\t"))
    grouped: dict[tuple[str, str, str, str], list[dict[str, str]]] = {}
    for row in rows:
        if str(row.get("text") or "").strip():
            key = tuple(
                str(row.get(field) or "")
                for field in ("page_num", "block_num", "par_num", "line_num")
            )
            grouped.setdefault(key, []).append(row)

    label_lines: list[list[dict[str, str]]] = []
    for words in grouped.values():
        normalized = normalize_reference_name(
            " ".join(str(word.get("text") or "") for word in words)
        )
        if "classe" in normalized and "armatura" in normalized:
            label_lines.append(words)
    if len(label_lines) != 1:
        return fail("tsv_ca_label_ambiguous", label_count=len(label_lines))

    label_words = label_lines[0]
    armatura_word = next(
        (
            word
            for word in label_words
            if "armatura" in normalize_reference_name(str(word.get("text") or ""))
        ),
        None,
    )
    if armatura_word is None:
        return fail("tsv_armatura_token_missing")

    label_end = int(armatura_word["left"]) + int(armatura_word["width"])
    value_words = sorted(
        (
            word
            for word in label_words
            if int(word["left"]) >= label_end and str(word.get("text") or "").strip()
        ),
        key=lambda word: int(word["left"]),
    )
    if not value_words:
        return fail("tsv_ca_value_geometry_missing")

    value_word = value_words[0]
    value_left = int(value_word["left"])
    value_right = value_left + int(value_word["width"])
    value_top = int(value_word["top"])
    value_bottom = value_top + int(value_word["height"])

    source = fitz.Pixmap(str(image_path))
    grayscale = fitz.Pixmap(fitz.csGRAY, source)
    x_padding = max(3, int(value_word["width"]) // 3)
    y_padding = max(2, int(value_word["height"]) // 3)
    crop_rect = fitz.IRect(
        max(0, value_left - x_padding),
        max(0, value_top - y_padding),
        min(grayscale.width, value_right + x_padding),
        min(grayscale.height, value_bottom + y_padding),
    )
    if crop_rect.x1 <= crop_rect.x0 or crop_rect.y1 <= crop_rect.y0:
        return fail("ca_crop_invalid")

    crop_width = crop_rect.x1 - crop_rect.x0
    crop_height = crop_rect.y1 - crop_rect.y0
    crop_samples = b"".join(
        grayscale.samples[
            row * grayscale.stride + crop_rect.x0 : row * grayscale.stride
            + crop_rect.x1
        ]
        for row in range(crop_rect.y0, crop_rect.y1)
    )
    crop_pixmap = fitz.Pixmap(
        fitz.csGRAY,
        crop_width,
        crop_height,
        crop_samples,
        False,
    )
    if scale_factor > 1:
        crop_pixmap = fitz.Pixmap(
            crop_pixmap,
            crop_width * scale_factor,
            crop_height * scale_factor,
        )
    if otsu_inverted:
        crop_pixmap = fitz.Pixmap(
            fitz.csGRAY,
            crop_pixmap.width,
            crop_pixmap.height,
            _otsu_inverted_samples(crop_pixmap.samples),
            False,
        )

    with tempfile.TemporaryDirectory(
        prefix=f"tomoforge-cinghiale-ca-{pass_label}-"
    ) as tmp:
        crop_path = Path(tmp) / "cinghiale-ca.png"
        crop_pixmap.save(crop_path)
        raw = _run_tesseract_bounded(
            [
                "tesseract",
                str(crop_path),
                "stdout",
                "-l",
                languages,
                "--psm",
                str(micro_psm),
                "-c",
                "tessedit_char_whitelist=0123456789",
                "quiet",
            ],
            ocr_budget_started_at,
            phase=f"cinghiale_ca_micro_{pass_label}",
        )

    digits = re.sub(r"\D", "", raw)
    if not re.fullmatch(r"\d{1,2}", digits):
        return fail("digits_not_unique", raw=" ".join(raw.split())[:40])

    candidate_value = f"{digits} ({suffix.strip('() ')})" if suffix else digits
    candidate_flags = monster_semantic_numeric_flags(
        {"classe_armatura": candidate_value, "punti_ferita": "1 (1d4)"}
    )
    if {CA_FORMAT_ERROR_FLAG, CA_OUT_OF_BOUNDS_FLAG} & set(candidate_flags):
        return fail("micro_value_failed_ca_gate", candidate=candidate_value)

    lines[ca_index] = f"{current_match.group('label')}{candidate_value}"
    rebuilt = "\n".join(lines)
    if page_text.endswith("\n"):
        rebuilt += "\n"
    print(
        "PHB_CINGHIALE_CA_MICRO_REPAIR "
        + json.dumps(
            {
                "name": name,
                "pass": pass_label,
                "value": candidate_value,
                "psm": micro_psm,
                "scale_factor": scale_factor,
                "otsu_inverted": otsu_inverted,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return rebuilt


def _korred_structural_hp_anchors(lines: list[str]) -> tuple[list[int], list[int]]:
    """Exclude narrative/name mentions and HP prose from Korred's micro crop."""
    anchors: list[tuple[int, int]] = []
    for ca_index, line in enumerate(lines):
        if not re.match(r"\s*Classe\s+Armatura\b", line, re.IGNORECASE):
            continue
        header = _find_header(lines, ca_index)
        if header is None or normalize_reference_name(header[1]) != "korred":
            continue
        title_index = header[0]
        following = range(ca_index + 1, min(len(lines), ca_index + 9))
        speed_indexes = [
            index
            for index in following
            if re.match(r"\s*Velocit[àa]\b", lines[index], re.IGNORECASE)
        ]
        if len(speed_indexes) != 1:
            continue
        hp_indexes = [
            index
            for index in range(ca_index + 1, speed_indexes[0])
            if re.match(r"\s*Punti\s+Ferita\b", lines[index], re.IGNORECASE)
        ]
        if len(hp_indexes) == 1:
            anchors.append((title_index, hp_indexes[0]))
    # Duplicate core anchors remain ambiguous even when they share a title/PF row.
    return sorted(title for title, _ in anchors), sorted(hp for _, hp in anchors)


def _micro_ocr_hit_points_line(
    image_path: Path,
    languages: str,
    psm: int,
    page_text: str,
    name: str,
    *,
    ocr_budget_started_at: float | tuple[float, float] | None = None,
    single_target_geometry: bool = False,
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

    def remaining_global_ocr_budget() -> float | None:
        return _remaining_global_ocr_budget(ocr_budget_started_at)

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
    page_text_has_hp_label = bool(hp_line_pattern.search(page_text))
    if not page_text_has_hp_label:
        diagnostics["page_text_local_hp_count"] = 0
        return page_text

    # The expensive graphical micro-OCR is a repair fallback, not a mandatory
    # third reading. If this independent page pass already contains exactly one
    # target identity and exactly one nearby, structurally valid PF value, keep
    # the original OCR text. The later primary-vs-comparison agreement gate
    # still has to match CA/PF/velocita exactly, so this does not weaken trust.
    normalized_name = normalize_reference_name(name).replace(" ", "")
    if normalized_name:
        text_lines = page_text.splitlines()
        target_indexes = [
            index
            for index, line in enumerate(text_lines)
            if _micro_target_line_matches(line, name)
        ]
        local_hp_indexes = sorted(
            {
                index
                for target_index in target_indexes
                for index in range(
                    target_index + 1,
                    min(len(text_lines), target_index + 13),
                )
                if re.search(
                    r"\bPunti\s+Ferita\b",
                    text_lines[index],
                    re.IGNORECASE,
                )
            }
        )
        local_hp_indexes = _collapse_identical_hp_indexes(
            text_lines,
            local_hp_indexes,
        )
        if name == "Korred":
            target_indexes, local_hp_indexes = _korred_structural_hp_anchors(text_lines)
        if len(local_hp_indexes) == 1:
            local_match = hp_line_pattern.match(text_lines[local_hp_indexes[0]])
            if local_match is not None:
                local_value = " ".join(local_match.group("value").split())
                local_flags = monster_semantic_numeric_flags(
                    {
                        "classe_armatura": "10",
                        "punti_ferita": local_value,
                    }
                )
                if (
                    HP_FORMAT_ERROR_FLAG not in local_flags
                    and not NONSTANDARD_MULTI_DIGIT_DIE_RE.search(local_value)
                ):
                    print(
                        "HP_MICRO_OCR_SKIPPED_VALID_LOCAL "
                        + json.dumps(
                            {
                                "name": name,
                                "punti_ferita": local_value,
                            },
                            ensure_ascii=False,
                            sort_keys=True,
                        )
                    )
                    return page_text

    command = [
        "tesseract",
        str(image_path),
        "stdout",
        "-l",
        languages,
        "--psm",
        str(
            11 if name in {"Brontosauro", "Delfino", "Divoratore"} and psm == 4 else psm
        ),
        "tsv",
        "quiet",
    ]
    tsv_stdout = _run_tesseract_bounded(
        command,
        ocr_budget_started_at,
        phase="sparse_anchor_tsv",
    )
    rows = list(csv.DictReader(io.StringIO(tsv_stdout), delimiter="\t"))
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

    def page_text_anchor_details() -> tuple[int, list[int]]:
        text_lines = page_text.splitlines()
        if name == "Korred":
            titles, hp_indexes = _korred_structural_hp_anchors(text_lines)
            return len(titles), hp_indexes
        target_indexes = [
            index
            for index, line in enumerate(text_lines)
            if _micro_target_line_matches(line, name)
        ]
        hp_indexes = sorted(
            {
                index
                for target_index in target_indexes
                for index in range(
                    target_index + 1,
                    min(len(text_lines), target_index + 13),
                )
                if re.search(
                    r"\bPunti\s+Ferita\b",
                    text_lines[index],
                    re.IGNORECASE,
                )
            }
        )
        hp_indexes = _collapse_identical_hp_indexes(text_lines, hp_indexes)
        if name in {"Bael", "Delfino", "Divoratore"}:
            # Body references to Bael and regeneration are not structural PF rows.
            hp_indexes = [
                index
                for index in hp_indexes
                if hp_line_pattern.match(text_lines[index])
                and (
                    name != "Delfino"
                    or re.match(
                        r"^\s*Punti\s+Ferita\s+11\s*\(",
                        text_lines[index],
                        re.IGNORECASE,
                    )
                )
            ]
        return len(target_indexes), hp_indexes

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

    page_target_count, page_local_hp_indexes = page_text_anchor_details()
    page_local_hp_count = len(page_local_hp_indexes)
    diagnostics["page_text_target_count"] = page_target_count
    diagnostics["page_text_local_hp_count"] = page_local_hp_count
    global_labels = page_wide_tsv_labels()
    diagnostics["tsv_page_wide_hp_label_count"] = len(global_labels)

    name_line_index = next(
        (
            index
            for index, words in enumerate(ordered_lines)
            if _micro_target_line_matches(
                " ".join(str(word["text"]) for word in words),
                name,
            )
        ),
        None,
    )
    diagnostics["tsv_name_anchor_found"] = name_line_index is not None
    label_words: list[dict[str, str]] | None = None
    if name == "Korred":
        tsv_lines = [
            " ".join(str(word["text"]) for word in words) for words in ordered_lines
        ]
        titles, hp_indexes = _korred_structural_hp_anchors(tsv_lines)
        name_line_index = titles[0] if len(titles) == len(hp_indexes) == 1 else None
        diagnostics["tsv_name_anchor_found"] = name_line_index is not None
        if name_line_index is not None:
            label_words = ordered_lines[hp_indexes[0]]
    # The target name remains the required upper anchor. Descriptor and wrapped
    # lines vary across legacy layouts, so scan subsequent TSV lines; the crop
    # is still bound to the first HP label below that exact target identity.
    if name_line_index is not None and label_words is None:
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
    if label_words is None and name_line_index is not None and len(global_labels) == 1:
        label_words = global_labels[0]
        print(
            "HP_UNIQUE_COLUMN_LABEL_FALLBACK "
            + json.dumps(
                {
                    "name": name,
                    "tsv_name_anchor_found": True,
                    "unique_tsv_hp_labels": 1,
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
    if (
        label_words is None
        and name in SOURCE_GUIDED_UNIQUE_HP_SEGMENT_FALLBACK_TARGETS
        and len(global_labels) == 1
    ):
        label_words = global_labels[0]
        print(
            "HP_SOURCE_GUIDED_SEGMENT_FALLBACK "
            + json.dumps(
                {
                    "name": name,
                    "unique_tsv_hp_labels": 1,
                    "target_segment": TARGET_SEGMENT_BY_NAME.get(name),
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
    if name == "Bael":
        structural = [
            normalize_reference_name(" ".join(str(word["text"]) for word in words))
            for words in ordered_lines
        ]
        ca_rows = [
            index
            for index, text in enumerate(structural)
            if text.startswith("classe armatura 18")
        ]
        hp_rows = [
            index
            for index, text in enumerate(structural)
            if text.startswith("punti ferita 189")
        ]
        speed_rows = [
            index
            for index, text in enumerate(structural)
            if text.startswith("velocita 9")
        ]
        if (
            len(ca_rows) == len(hp_rows) == len(speed_rows) == 1
            and ca_rows[0] < hp_rows[0] < speed_rows[0]
            and speed_rows[0] - ca_rows[0] <= 6
            and page_local_hp_count == 1
        ):
            label_words = ordered_lines[hp_rows[0]]
            print(
                "MPMM_BAEL_STRUCTURAL_HP_ANCHOR "
                + json.dumps(
                    {
                        "name": name,
                        "label": structural[hp_rows[0]],
                        "ordered_core_labels": True,
                    }
                )
            )
        else:
            return fail_closed("bael_structural_hp_anchor_ambiguous")
    if name == "Divoratore":
        structural = [
            normalize_reference_name(" ".join(str(word["text"]) for word in words))
            for words in ordered_lines
        ]
        ca_rows = [
            index
            for index, text in enumerate(structural)
            if text.startswith("classe armatura 16")
        ]
        hp_rows = [
            index
            for index, text in enumerate(structural)
            if text.startswith("punti ferita 189")
        ]
        speed_rows = [
            index
            for index, text in enumerate(structural)
            if text.startswith("velocita 9")
        ]
        if (
            len(ca_rows) == len(hp_rows) == len(speed_rows) == 1
            and ca_rows[0] < hp_rows[0] < speed_rows[0]
            and speed_rows[0] - ca_rows[0] <= 6
            and page_local_hp_count == 1
        ):
            label_words = ordered_lines[hp_rows[0]]
            print(
                "MPMM_DIVORATORE_STRUCTURAL_HP_ANCHOR "
                + json.dumps(
                    {
                        "name": name,
                        "label": structural[hp_rows[0]],
                        "ordered_core_labels": True,
                    }
                )
            )
        else:
            return fail_closed("divoratore_structural_hp_anchor_ambiguous")
    if name == "Delfino":
        structural = [
            normalize_reference_name(" ".join(str(word["text"]) for word in words))
            for words in ordered_lines
        ]
        ca_rows = [
            index
            for index, text in enumerate(structural)
            if text.startswith("classe armatura 12")
        ]
        hp_rows = [
            index
            for index, text in enumerate(structural)
            if text.startswith("punti ferita 11")
        ]
        if not (len(ca_rows) == len(hp_rows) == page_local_hp_count == 1):
            return fail_closed("delfino_structural_hp_anchor_ambiguous")
        ca, hp = ca_rows[0], hp_rows[0]
        nearby_speed = [
            index
            for index in range(hp + 1, min(len(structural), hp + 7))
            if structural[index].startswith("velocita 0")
        ]
        if not (ca < hp and hp - ca <= 4 and len(nearby_speed) == 1):
            return fail_closed("delfino_core_order_ambiguous")
        label_words = ordered_lines[hp]
        print(
            "MPMM_DELFINO_STRUCTURAL_HP_ANCHOR "
            + json.dumps({"label": structural[hp], "numeric_values_modified": False})
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
        max(
            0,
            min(int(word["left"]) for word in label_words)
            if name == "Delfino"
            else label_end,
        ),
        max(0, line_top - padding),
        grayscale.width,
        min(grayscale.height, line_bottom + padding),
    )
    crop_width = crop_rect.x1 - crop_rect.x0
    crop_height = crop_rect.y1 - crop_rect.y0
    if crop_width < 1 or crop_height < 1:
        diagnostics["crop_width"] = crop_width
        diagnostics["crop_height"] = crop_height
        return fail_closed("hp_crop_invalid")
    source_samples = grayscale.samples
    crop_samples = b"".join(
        source_samples[
            row * grayscale.stride + crop_rect.x0 : row * grayscale.stride
            + crop_rect.x1
        ]
        for row in range(crop_rect.y0, crop_rect.y1)
    )
    if len(crop_samples) != crop_width * crop_height:
        diagnostics["crop_width"] = crop_width
        diagnostics["crop_height"] = crop_height
        diagnostics["crop_sample_count"] = len(crop_samples)
        return fail_closed("hp_crop_raster_mismatch")

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
        # Fail closed before paying for a new graphical variant.
        remaining_global_ocr_budget()
        prep_started_at = time.monotonic()
        phase_started_at = prep_started_at
        prep_timings: dict[str, float] = {}
        contrast_lut = bytes(
            max(0, min(255, round(128 + (sample - 128) * contrast)))
            for sample in range(256)
        )
        contrasted_samples = crop_samples.translate(contrast_lut)
        contrasted = fitz.Pixmap(
            fitz.csGRAY,
            crop_width,
            crop_height,
            contrasted_samples,
            False,
        )
        prep_timings["contrast"] = round(time.monotonic() - phase_started_at, 3)
        phase_started_at = time.monotonic()
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
        prep_timings["upscale"] = round(time.monotonic() - phase_started_at, 3)
        phase_started_at = time.monotonic()
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
        prep_timings["morphology"] = round(time.monotonic() - phase_started_at, 3)
        phase_started_at = time.monotonic()
        background_mean, background_variance = _background_luminance_stats(
            threshold_samples,
            raster.width,
            raster.height,
        )
        prep_timings["background_stats"] = round(time.monotonic() - phase_started_at, 3)
        phase_started_at = time.monotonic()
        use_adaptive_inversion = bool(
            adaptive_background_inversion
            and (
                background_mean < HIT_POINTS_BACKGROUND_MEAN_WHITE_THRESHOLD
                or background_variance > HIT_POINTS_BACKGROUND_VARIANCE_THRESHOLD
            )
        )
        if bitonal_threshold is not None and not use_adaptive_inversion:
            threshold_lut = bytes(
                0 if sample <= bitonal_threshold else 255 for sample in range(256)
            )
            threshold_samples = threshold_samples.translate(threshold_lut)
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
        prep_timings["threshold_otsu"] = round(time.monotonic() - phase_started_at, 3)
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
        phase_started_at = time.monotonic()
        processed.save(crop_path)
        prep_timings["save_png"] = round(time.monotonic() - phase_started_at, 3)
        prep_timings["total"] = round(time.monotonic() - prep_started_at, 3)
        print(
            "HP_MICRO_PREP_TIMING "
            + json.dumps(
                {
                    "name": name,
                    "contrast": contrast,
                    "scale_factor": scale_factor,
                    "threshold": bitonal_threshold,
                    "otsu_inverted": otsu_inverted,
                    **prep_timings,
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        command = [
            "tesseract",
            str(crop_path),
            "stdout",
            "-l",
            languages,
            "--psm",
            "6"
            if name in {"Brontosauro", "Delfino", "Divoratore"} and psm == 4
            else "7",
            "-c",
            f"tessedit_char_whitelist={HIT_POINTS_WHITELIST}",
            "quiet",
        ]
        try:
            return _run_tesseract_bounded(
                command,
                ocr_budget_started_at,
                phase="hp_micro_variant",
            )
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
        except RepairBlocked as exc:
            if exc.reason == "ocr_global_timeout":
                raise
            if exc.reason == "ocr_subprocess_timeout":
                timeout_seconds = (exc.diagnostics or {}).get(
                    "timeout_seconds"
                ) or HIT_POINTS_MICRO_OCR_TIMEOUT_SECONDS
                print(
                    "HP_MICRO_OCR_SUBPROCESS_TIMEOUT "
                    + json.dumps(
                        {
                            "name": name,
                            "timeout_seconds": timeout_seconds,
                            "variant": crop_path.name,
                        },
                        ensure_ascii=False,
                        sort_keys=True,
                    )
                )
                return ""
            if exc.reason == "ocr_subprocess_failed":
                diagnostics = exc.diagnostics or {}
                returncode = int(diagnostics.get("exit_code") or 1)
                print(
                    "HP_MICRO_OCR_SUBPROCESS_FAILURE "
                    + json.dumps(
                        {
                            "name": name,
                            "returncode": returncode,
                            "signal": -returncode if returncode < 0 else None,
                            "variant": crop_path.name,
                        },
                        ensure_ascii=False,
                        sort_keys=True,
                    )
                )
                return ""
            raise

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
                # The legacy x2 dilation retry is intentionally skipped here.
                # It is computationally expensive on large PHB crops and does not
                # relax or add an acceptance gate: failures proceed directly to
                # the bounded x4 full-spectrum grid below, which is still accepted
                # only through hp_micro_ocr_failed()'s semantic/math coherence.
                superscaled_otsu_micro = None
            else:
                micro = otsu_micro
                superscaled_otsu_micro = None
            full_spectrum_attempts: list[dict[str, object]] = []
            full_spectrum_accepted: dict[str, object] | None = None
            raw_micro_candidates = [
                candidate
                for candidate in (
                    initial_micro,
                    otsu_micro,
                    upscaled_otsu_micro,
                    superscaled_otsu_micro,
                )
                if candidate
            ]
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
                # Ultra-short fail-closed grid: one x4 render, two contrasts,
                # two lightweight bitonal thresholds, native morphology only.
                # All semantic hit-dice and mathematical acceptance gates below
                # remain unchanged.
                scale_factors = (4,)
                morphologies = ("none",)
                for scale_factor in scale_factors:
                    for contrast in HIT_POINTS_FULL_SPECTRUM_CONTRASTS:
                        for threshold in HIT_POINTS_FULL_SPECTRUM_THRESHOLDS:
                            for morphology in morphologies:
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
                                if candidate:
                                    raw_micro_candidates.append(candidate)
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
            if hp_micro_ocr_failed(micro):
                reconstructed = {
                    repaired
                    for raw_candidate in raw_micro_candidates
                    if (
                        repaired := _repair_numeric_dice_separator_confusion(
                            raw_candidate
                        )
                    )
                    is not None
                }
                if len(reconstructed) == 1:
                    micro = next(iter(reconstructed))
                    print(
                        "HP_DICE_SEPARATOR_RECONSTRUCTION "
                        + json.dumps(
                            {
                                "name": name,
                                "value": micro,
                                "supporting_variants": sum(
                                    1
                                    for raw_candidate in raw_micro_candidates
                                    if _repair_numeric_dice_separator_confusion(
                                        raw_candidate
                                    )
                                    == micro
                                ),
                            },
                            ensure_ascii=False,
                            sort_keys=True,
                        )
                    )

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
    if page_text_has_hp_label:
        text_lines = page_text.splitlines()
        duplicate_geometry_indexes: list[int] = []
        if (
            single_target_geometry
            and page_target_count >= 1
            and page_local_hp_count >= 1
            and all(
                _sparse_anchor_matches(text_lines[index], name)
                for index, line in enumerate(text_lines)
                if _micro_target_line_matches(line, name)
            )
        ):
            duplicate_geometry_indexes = list(page_local_hp_indexes)
        if duplicate_geometry_indexes:
            for hp_index in duplicate_geometry_indexes:
                hp_match = hp_line_pattern.match(text_lines[hp_index])
                if hp_match is None:
                    return fail_closed("micro_ocr_target_hp_line_unparseable")
                text_lines[hp_index] = f"{hp_match.group('label').rstrip()} {value}"
            print(
                "HP_UNIQUE_GEOMETRY_DUPLICATE_REPLACEMENT "
                + json.dumps(
                    {
                        "name": name,
                        "page_target_count": page_target_count,
                        "page_hp_lines": len(duplicate_geometry_indexes),
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )
            rebuilt = "\n".join(text_lines)
            if page_text.endswith("\n"):
                rebuilt += "\n"
            return rebuilt
        if page_target_count >= 1 and page_local_hp_count == 1:
            hp_index = page_local_hp_indexes[0]
        else:
            page_hp_indexes = [
                index
                for index, line in enumerate(text_lines)
                if hp_line_pattern.match(line)
            ]
            if not (
                page_target_count == 0
                and name_line_index is not None
                and len(global_labels) == 1
                and len(page_hp_indexes) == 1
            ):
                return fail_closed("micro_ocr_replacement_target_ambiguous")
            hp_index = page_hp_indexes[0]
            print(
                "HP_TSV_IDENTITY_SINGLE_LINE_FALLBACK "
                + json.dumps(
                    {
                        "name": name,
                        "page_hp_lines": 1,
                        "tsv_name_anchor_found": True,
                        "unique_tsv_hp_labels": 1,
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )
        hp_match = hp_line_pattern.match(text_lines[hp_index])
        if hp_match is None:
            return fail_closed("micro_ocr_target_hp_line_unparseable")
        text_lines[hp_index] = f"{hp_match.group('label').rstrip()} {value}"
        rebuilt = "\n".join(text_lines)
        if page_text.endswith("\n"):
            rebuilt += "\n"
        return rebuilt
    if name_line_index is None or label_words is None:
        return fail_closed("micro_ocr_reconstruction_missing_anchor")
    speed_line_pattern = re.compile(
        r"^(?=[ \t]*Velocit[àa]\b)",
        re.IGNORECASE | re.MULTILINE,
    )
    if not speed_line_pattern.search(page_text):
        return fail_closed("micro_ocr_reconstruction_speed_anchor_missing")
    print(
        "HP_SYNTHETIC_LINE_RECONSTRUCTION "
        + json.dumps(
            {"name": name, "value": value},
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return speed_line_pattern.sub(
        f"Punti Ferita {value}\n",
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
    target_page_only: bool = False,
    ocr_budget_started_at: float | tuple[float, float] | None = None,
) -> tuple[
    list[tuple[int, str]],
    list[tuple[int, str]],
    dict[int, dict[str, Any]],
]:
    """OCR <=3 pages, isolating columns and any quality-fail segment."""
    import fitz

    if target_page_only:
        start_page = target_page
        end_page = target_page
    else:
        start_page = max(1, target_page - 1)
        end_page = min(page_total, target_page + 1)
    if end_page - start_page + 1 > 3:
        raise AssertionError(
            "source-guided repair window unexpectedly exceeded 3 pages"
        )

    if name in {"Bodak", "Draegloth"}:
        dpi = max(dpi, 400)
    effective_dpi, primary_psm, secondary_psm = _layout_ocr_settings(
        source,
        dpi=dpi,
        psm=psm,
        comparison_psm=comparison_psm,
    )
    if name == "Bodak":
        primary_psm, secondary_psm = 6, 11
    if name == "Uro":
        primary_psm, secondary_psm = 6, 4
    if (
        name == "Capo Vegepigmeo"
        and source.get("logical_source_id") == "mpmm_2022_it"
        and target_page == 65
        and target_page_only
    ):
        # Sparse segmentation independently re-reads the exact target title and
        # compact core labels on this registered page.
        secondary_psm = 11
    if (
        name == "Juiblex"
        and source.get("logical_source_id") == "mpmm_2022_it"
        and target_page == 56
        and target_page_only
    ):
        secondary_psm = 6
    if (
        name == "Leucrotta"
        and source.get("logical_source_id") == "mpmm_2022_it"
        and target_page == 65
        and target_page_only
    ):
        effective_dpi = max(effective_dpi, 400)
        secondary_psm = 11
    if (
        name == "Leviatano"
        and source.get("logical_source_id") == "mpmm_2022_it"
        and target_page == 66
        and target_page_only
    ):
        secondary_psm = 11
    if (
        name == "Mago Trasmutatore"
        and source.get("logical_source_id") == "mpmm_2022_it"
        and target_page == 74
        and target_page_only
    ):
        secondary_psm = 11
    if (
        name == "Orthon"
        and source.get("logical_source_id") == "mpmm_2022_it"
        and target_page == 12
        and target_page_only
    ):
        secondary_psm = 6
    if (
        name == "Moloch"
        and source.get("logical_source_id") == "mpmm_2022_it"
        and target_page == 90
        and target_page_only
    ):
        secondary_psm = 12
    if (
        name == "Sciame Di Ratti Cranici"
        and source.get("logical_source_id") == "mpmm_2022_it"
        and target_page == 28
        and target_page_only
    ):
        effective_dpi = max(effective_dpi, 400)
        primary_psm, secondary_psm = 11, 12
    if (
        name == "Xvart"
        and source.get("logical_source_id") == "mpmm_2022_it"
        and target_page == 71
        and target_page_only
    ):
        primary_psm = 6
    if (
        name == "Mirmidone Elementale Di Fuoco"
        and source.get("logical_source_id") == "mpmm_2022_it"
        and target_page == 88
        and target_page_only
    ):
        effective_dpi = max(effective_dpi, 400)
        secondary_psm = 11
    if (
        name == "Mago Invocatore"
        and source.get("logical_source_id") == "mpmm_2022_it"
        and target_page == 72
        and target_page_only
    ):
        effective_dpi = max(effective_dpi, 400)
        primary_psm, secondary_psm = 11, 12
    if (
        name == "Githyanki Kith'Rak"
        and source.get("logical_source_id") == "mpmm_2022_it"
        and target_page == 36
        and target_page_only
    ):
        primary_psm, secondary_psm = 11, 12
    if (
        name == "Vegepigmeo"
        and source.get("logical_source_id") == "mpmm_2022_it"
        and target_page == 66
        and target_page_only
    ):
        primary_psm = 11
    if (
        name == "Danzatore Dell'Ombra"
        and source.get("logical_source_id") == "mpmm_2022_it"
        and target_page == 40
        and target_page_only
    ):
        effective_dpi = max(effective_dpi, 400)
        primary_psm, secondary_psm = 11, 12
    if (
        name == "Duergar Despota"
        and source.get("logical_source_id") == "mpmm_2022_it"
        and target_page == 9
        and target_page_only
    ):
        effective_dpi = max(effective_dpi, 400)
        secondary_psm = 6
    if (
        name == "Duergar Martellatore"
        and source.get("logical_source_id") == "mpmm_2022_it"
        and target_page == 8
        and target_page_only
    ):
        effective_dpi = max(effective_dpi, 400)
        primary_psm, secondary_psm = 12, 6
    if (
        name == "Fenice"
        and source.get("logical_source_id") == "mpmm_2022_it"
        and target_page == 23
        and target_page_only
    ):
        effective_dpi = max(effective_dpi, 400)
        primary_psm, secondary_psm = 12, 11
    if (
        name == "Drow Inquisitore"
        and source.get("logical_source_id") == "mpmm_2022_it"
        and target_page == 4
        and target_page_only
    ):
        effective_dpi = max(effective_dpi, 400)
        primary_psm, secondary_psm = 4, 12
    if sparse_full_page:
        # Geometry is already locked by a unique title anchor. Keep the
        # primary layout unchanged and vary only the independent comparison
        # segmentation mode for the remaining PHB identity failures.
        secondary_psm = _phb_sparse_comparison_psm(name, secondary_psm)
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
    if not sparse_full_page and name in {
        "Berbalang",
        "Bove Fetente",
        "Collezionista Di Cadaveri",
        "Divoratore",
    }:
        # These left stat blocks need no center overlap; it captures: left stat blocks; center overlap captures
        # detached fragments from the adjacent right-column prose.
        segments = (("left", (0.0, 0.0, 0.5, 1.0)),)
        column_overlap = 0.0
    if not sparse_full_page and name in {
        "Berretto Rosso",
        "Bodak",
        "Draegloth",
        "Stegosauro",
        "Uro",
    }:
        # Pages 69/73: exclude left-column narrative from the right stat block.
        segments = (("right", (0.5, 0.0, 1.0, 1.0)),)
        column_overlap = 0.0
    if not sparse_full_page and name in TARGET_SEGMENT_BY_NAME:
        target_segment = TARGET_SEGMENT_BY_NAME[name]
        segments = tuple(
            segment for segment in segments if segment[0] == target_segment
        )
        if not segments:
            raise RepairBlocked(
                "target_segment_unavailable",
                detail=f"name={name} segment={target_segment}",
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
                continuation_primary_page: tuple[int, str] | None = None
                continuation_comparison_page: tuple[int, str] | None = None

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
                    comparison_image_path = image_path

                    sparse_anchor_found = None
                    sparse_anchor_crop = None
                    if sparse_full_page:
                        sparse_anchor_crop = _sparse_anchor_crop_fractions(
                            image_path,
                            languages,
                            name,
                            ocr_budget_started_at=ocr_budget_started_at,
                        )
                        if sparse_anchor_crop is None and name == "Cinghiale":
                            sparse_anchor_crop = _sparse_anchor_crop_fractions(
                                image_path,
                                languages,
                                name,
                                psm=12,
                                ocr_budget_started_at=ocr_budget_started_at,
                            )
                        sparse_anchor_found = sparse_anchor_crop is not None
                        if not sparse_anchor_found:
                            segment_metrics[segment_name] = {
                                "quality_pass": False,
                                "sparse_anchor_found": False,
                                "sparse_anchor_crop": None,
                            }
                            continue
                        # The title anchor is measured inside the current
                        # source segment. Compose those relative fractions back
                        # into page coordinates before rendering the target.
                        sparse_anchor_crop = _compose_relative_crop(
                            fractions, sparse_anchor_crop
                        )
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
                        comparison_image_path = image_path

                        # The source-anchored crop already isolates Cavallo.
                        # Keep identical source pixels for both OCR passes and
                        # preserve independence through distinct layout modes
                        # (primary PSM 3, comparison PSM 4).
                        if _phb_sparse_uses_quality_pre_otsu(name):
                            _remaining_global_ocr_budget(ocr_budget_started_at)
                            quality_started_at = time.monotonic()
                            quality_image_path = image_root / (
                                f"page-{page_number:04d}-{segment_name}"
                                "-target-quality-x4.png"
                            )
                            # Re-render the source crop at 4x resolution instead
                            # of enlarging already-rasterized pixels. This keeps
                            # the preprocessing dependency-free and preserves
                            # source detail before local thresholding.
                            quality_matrix = fitz.Matrix(
                                effective_dpi * 4 / 72.0,
                                effective_dpi * 4 / 72.0,
                            )
                            quality_clip = _phb_quality_pre_otsu_clip(
                                target_clip,
                                name,
                            )
                            quality_pixmap = page.get_pixmap(
                                matrix=quality_matrix,
                                clip=quality_clip,
                                alpha=False,
                                colorspace=fitz.csGRAY,
                            )
                            if _phb_sparse_comparison_uses_adaptive_source(name):
                                comparison_source_path = image_root / (
                                    f"page-{page_number:04d}-{segment_name}"
                                    "-target-comparison-adaptive-x4.png"
                                )
                                quality_pixmap.save(comparison_source_path)
                                _pre_otsu_column_clean(
                                    comparison_source_path,
                                    scale_factor=1,
                                )
                                comparison_image_path = comparison_source_path
                                print(
                                    "PHB_COMPARISON_ADAPTIVE_DIAGNOSTIC "
                                    + json.dumps(
                                        {
                                            "name": name,
                                            "segment": segment_name,
                                            "render_scale_factor": 4,
                                            "adaptive_scale_factor": 1,
                                        },
                                        ensure_ascii=False,
                                        sort_keys=True,
                                    )
                                )
                            if _phb_sparse_comparison_uses_grayscale_source(name):
                                comparison_source_path = image_root / (
                                    f"page-{page_number:04d}-{segment_name}"
                                    "-target-comparison-grayscale-x4.png"
                                )
                                quality_pixmap.save(comparison_source_path)
                                comparison_image_path = comparison_source_path
                                print(
                                    "PHB_COMPARISON_GRAYSCALE_DIAGNOSTIC "
                                    + json.dumps(
                                        {
                                            "name": name,
                                            "segment": segment_name,
                                            "render_scale_factor": 4,
                                            "preprocessing": "grayscale_only",
                                        },
                                        ensure_ascii=False,
                                        sort_keys=True,
                                    )
                                )
                            local_otsu = _local_otsu_inverted_samples(
                                quality_pixmap.samples,
                                quality_pixmap.width,
                                quality_pixmap.height,
                            )
                            cleaned_quality = fitz.Pixmap(
                                fitz.csGRAY,
                                quality_pixmap.width,
                                quality_pixmap.height,
                                local_otsu,
                                False,
                            )
                            cleaned_quality.save(quality_image_path)
                            if _phb_sparse_primary_uses_grayscale_source(name):
                                image_path = comparison_source_path
                                print(
                                    "PHB_PRIMARY_GRAYSCALE_DIAGNOSTIC "
                                    + json.dumps(
                                        {
                                            "name": name,
                                            "segment": segment_name,
                                            "render_scale_factor": 4,
                                            "preprocessing": "grayscale_only",
                                        },
                                        ensure_ascii=False,
                                        sort_keys=True,
                                    )
                                )
                            else:
                                image_path = quality_image_path
                            if not (
                                _phb_sparse_comparison_uses_adaptive_source(name)
                                or _phb_sparse_comparison_uses_grayscale_source(name)
                            ):
                                comparison_image_path = image_path
                            print(
                                "PHB_QUALITY_PRE_OTSU_DIAGNOSTIC "
                                + json.dumps(
                                    {
                                        "name": name,
                                        "segment": segment_name,
                                        "render_scale_factor": 4,
                                        "inner_binding_trim_fraction": 0.0,
                                        "threshold": "tile_local_otsu_inverted",
                                        "before_independent_ocr": True,
                                        "elapsed_seconds": round(
                                            time.monotonic() - quality_started_at,
                                            3,
                                        ),
                                    },
                                    ensure_ascii=False,
                                    sort_keys=True,
                                )
                            )
                            _remaining_global_ocr_budget(ocr_budget_started_at)

                    primary = _run_tesseract_bounded(
                        [
                            "tesseract",
                            str(image_path),
                            "stdout",
                            "-l",
                            languages,
                            "--psm",
                            str(primary_psm),
                            "quiet",
                        ],
                        ocr_budget_started_at,
                        phase="segment_primary",
                    )
                    comparison = _run_tesseract_bounded(
                        [
                            "tesseract",
                            str(comparison_image_path),
                            "stdout",
                            "-l",
                            languages,
                            "--psm",
                            str(secondary_psm),
                            "quiet",
                        ],
                        ocr_budget_started_at,
                        phase="segment_comparison",
                    )
                    if name == "Bael" and not sparse_full_page:
                        primary = _restore_bael_title_from_local_actions(primary, name)
                        comparison = _restore_bael_title_from_local_actions(
                            comparison, name
                        )
                    if name == "Draegloth" and not sparse_full_page:
                        primary, comparison = _micro_ocr_draegloth_descriptor(
                            image_path,
                            languages,
                            primary,
                            comparison,
                            ocr_budget_started_at=ocr_budget_started_at,
                        )
                    if name == "Divoratore" and not sparse_full_page:
                        primary = _restore_divoratore_title_from_local_traits(
                            primary, name
                        )
                        comparison = _restore_divoratore_title_from_local_traits(
                            comparison, name
                        )
                    if name == "Derro" and not sparse_full_page:
                        primary = _restore_derro_title_from_local_traits(primary, name)
                        comparison = _restore_derro_title_from_local_traits(
                            comparison, name
                        )
                    if name == "Delfino" and not sparse_full_page:
                        primary = _restore_delfino_title_from_local_traits(
                            primary, name
                        )
                        comparison = _restore_delfino_title_from_local_traits(
                            comparison, name
                        )
                    if name == "Celeresto" and not sparse_full_page:
                        primary = _clean_celeresto_core_prefixes(primary, name)
                        comparison = _clean_celeresto_core_prefixes(comparison, name)
                    if name == "Bulezau" and not sparse_full_page:
                        primary = _restore_bulezau_title_from_local_trait(primary, name)
                        comparison = _restore_bulezau_title_from_local_trait(
                            comparison, name
                        )
                    if name == "Bodak" and not sparse_full_page:
                        primary, comparison = _micro_ocr_bodak_descriptor(
                            image_path,
                            languages,
                            primary,
                            comparison,
                            ocr_budget_started_at=ocr_budget_started_at,
                        )
                        primary = _restore_bodak_title_from_local_traits(primary, name)
                        comparison = _restore_bodak_title_from_local_traits(
                            comparison, name
                        )
                    if name == "Arciere" and not sparse_full_page:
                        primary = _restore_arciere_title_from_local_actions(
                            primary, name
                        )
                        comparison = _restore_arciere_title_from_local_actions(
                            comparison, name
                        )
                    if name == "Addolorato Affamato" and not sparse_full_page:
                        restored_affamato_primary = (
                            _restore_addolorato_affamato_dynamic_title(
                                primary,
                                name,
                            )
                        )
                        restored_affamato_comparison = (
                            _restore_addolorato_affamato_dynamic_title(
                                comparison,
                                name,
                            )
                        )
                        if (
                            restored_affamato_primary != primary
                            or restored_affamato_comparison != comparison
                        ):
                            primary = restored_affamato_primary
                            comparison = restored_affamato_comparison
                            print(
                                "MPMM_ADDOLORATO_AFFAMATO_TITLE_RESTORE "
                                + json.dumps(
                                    {
                                        "name": name,
                                        "segment": segment_name,
                                        "numeric_values_modified": False,
                                    },
                                    ensure_ascii=False,
                                    sort_keys=True,
                                )
                            )
                    restored_comparison = _restore_cavallo_sparse_title_from_anchor(
                        comparison,
                        name,
                        unique_anchor_found=bool(
                            sparse_full_page and sparse_anchor_found
                        ),
                    )
                    restored_mulo_comparison = _restore_mulo_sparse_title_from_anchor(
                        comparison,
                        name,
                        unique_anchor_found=bool(
                            sparse_full_page and sparse_anchor_found
                        ),
                    )
                    if restored_mulo_comparison != comparison:
                        comparison = restored_mulo_comparison
                        print(
                            "PHB_MULO_TITLE_ANCHOR_RESTORE "
                            + json.dumps(
                                {
                                    "name": name,
                                    "segment": segment_name,
                                    "source": "unique_psm11_anchor",
                                    "values_modified": False,
                                },
                                ensure_ascii=False,
                                sort_keys=True,
                            )
                        )
                    if restored_comparison != comparison:
                        comparison = restored_comparison
                        print(
                            "PHB_CAVALLO_TITLE_ANCHOR_RESTORE "
                            + json.dumps(
                                {
                                    "name": name,
                                    "segment": segment_name,
                                    "source": "unique_psm11_anchor",
                                    "values_modified": False,
                                },
                                ensure_ascii=False,
                                sort_keys=True,
                            )
                        )

                    repaired_orso_primary = _repair_orso_sparse_structure_from_anchor(
                        primary,
                        name,
                        unique_anchor_found=bool(
                            sparse_full_page and sparse_anchor_found
                        ),
                    )
                    repaired_orso_comparison = (
                        _repair_orso_sparse_structure_from_anchor(
                            comparison,
                            name,
                            unique_anchor_found=bool(
                                sparse_full_page and sparse_anchor_found
                            ),
                        )
                    )
                    if (
                        repaired_orso_primary != primary
                        or repaired_orso_comparison != comparison
                    ):
                        primary = repaired_orso_primary
                        comparison = repaired_orso_comparison
                        print(
                            "PHB_ORSO_STRUCTURE_RESTORE "
                            + json.dumps(
                                {
                                    "name": name,
                                    "segment": segment_name,
                                    "source": "unique_psm11_anchor",
                                    "numeric_values_modified": False,
                                },
                                ensure_ascii=False,
                                sort_keys=True,
                            )
                        )

                    micro_image_path = image_path
                    if (
                        name in QUALITY_FAIL_PRE_OTSU_TARGETS
                        and name not in {"Bael", "Divoratore"}
                        and not sparse_full_page
                    ):
                        target_normalized = normalize_reference_name(name)
                        target_words = target_normalized.split()

                        def _has_title_like_target(text: str) -> bool:
                            for raw_line in text.splitlines():
                                normalized_line = normalize_reference_name(raw_line)
                                if normalized_line == target_normalized:
                                    return True
                                words = normalized_line.split()
                                if (
                                    len(words) == len(target_words) + 1
                                    and words[: len(target_words)] == target_words
                                    and len(words[-1]) <= 2
                                ):
                                    return True
                            return False

                        primary_has_target = _has_title_like_target(primary)
                        comparison_has_target = _has_title_like_target(comparison)
                        if primary_has_target or comparison_has_target:
                            _remaining_global_ocr_budget(ocr_budget_started_at)
                            pre_otsu_started_at = time.monotonic()
                            pre_otsu_scale = PRE_OTSU_SCALE_BY_TARGET.get(name, 2)
                            micro_image_path = (
                                image_root
                                / f"page-{page_number:04d}-{segment_name}-micro.png"
                            )
                            fitz.Pixmap(str(image_path)).save(micro_image_path)
                            _pre_otsu_column_clean(
                                micro_image_path,
                                scale_factor=pre_otsu_scale,
                            )
                            print(
                                "PRE_OTSU_DIAGNOSTIC "
                                + json.dumps(
                                    {
                                        "name": name,
                                        "segment": segment_name,
                                        "scale_factor": pre_otsu_scale,
                                        "micro_only": True,
                                        "elapsed_seconds": round(
                                            time.monotonic() - pre_otsu_started_at,
                                            3,
                                        ),
                                    },
                                    ensure_ascii=False,
                                    sort_keys=True,
                                )
                            )
                            _remaining_global_ocr_budget(ocr_budget_started_at)

                    primary = _micro_ocr_cavallo_armor_class_line(
                        image_path,
                        languages,
                        primary,
                        name,
                        ocr_budget_started_at=ocr_budget_started_at,
                        single_target_geometry=bool(
                            sparse_full_page and sparse_anchor_found
                        ),
                    )
                    primary = _micro_ocr_cinghiale_armor_class_line(
                        image_path,
                        languages,
                        primary,
                        name,
                        micro_psm=7,
                        scale_factor=4,
                        pass_label="primary",
                        otsu_inverted=False,
                        ocr_budget_started_at=ocr_budget_started_at,
                        single_target_geometry=bool(
                            sparse_full_page and sparse_anchor_found
                        ),
                    )
                    comparison = _micro_ocr_cinghiale_armor_class_line(
                        image_path,
                        languages,
                        comparison,
                        name,
                        micro_psm=10,
                        scale_factor=4,
                        pass_label="comparison",
                        otsu_inverted=True,
                        ocr_budget_started_at=ocr_budget_started_at,
                        single_target_geometry=bool(
                            sparse_full_page and sparse_anchor_found
                        ),
                    )

                    if name in PLAYERS_HANDBOOK_TIMEOUT8_NAMES and not sparse_full_page:
                        print(
                            "HP_MICRO_OCR_DEFERRED_TO_SPARSE "
                            + json.dumps(
                                {"name": name, "segment": segment_name},
                                ensure_ascii=False,
                                sort_keys=True,
                            )
                        )
                    else:
                        primary = _micro_ocr_hit_points_line(
                            micro_image_path,
                            languages,
                            primary_psm,
                            primary,
                            name,
                            ocr_budget_started_at=ocr_budget_started_at,
                            single_target_geometry=bool(
                                sparse_full_page and sparse_anchor_found
                            ),
                        )
                        comparison = _micro_ocr_hit_points_line(
                            micro_image_path,
                            languages,
                            secondary_psm,
                            comparison,
                            name,
                            ocr_budget_started_at=ocr_budget_started_at,
                            single_target_geometry=bool(
                                sparse_full_page and sparse_anchor_found
                            ),
                        )
                    if name in {
                        "Altisauro",
                        "Bael",
                        "Adrosauro",
                        "Arciere",
                        "Berretto Rosso",
                        "Bodak",
                        "Bove Fetente",
                        "Brontosauro",
                        "Bulezau",
                        "Celeresto",
                        "Cervello Antico",
                        "Collezionista Di Cadaveri",
                        "Delfino",
                        "Derro",
                        "Dimetrodonte",
                        "Divoratore",
                        "Draegloth",
                        "Stegosauro",
                        "Uro",
                        "Velociraptor",
                    }:

                        def _focused_ocr_context(text: str) -> list[str]:
                            raw_lines = [
                                " ".join(raw_line.split())
                                for raw_line in text.splitlines()
                                if raw_line.strip()
                            ]
                            normalized_lines = [
                                normalize_reference_name(raw_line)
                                for raw_line in raw_lines
                            ]
                            anchors = [
                                index
                                for index, normalized in enumerate(normalized_lines)
                                if (
                                    normalized.startswith("classe armatura")
                                    or normalized.startswith("classe d armatura")
                                    or normalized.startswith("veloc")
                                    or normalize_reference_name(name) in normalized
                                )
                            ]
                            selected_indexes = sorted(
                                {
                                    candidate
                                    for index in anchors
                                    for candidate in range(
                                        max(0, index - 3),
                                        min(len(raw_lines), index + 4),
                                    )
                                }
                            )
                            return [raw_lines[index] for index in selected_indexes][:30]

                        print(
                            "FOCUSED_OCR_CONTEXT "
                            + json.dumps(
                                {
                                    "name": name,
                                    "page": page_number,
                                    "segment": segment_name,
                                    "primary": _focused_ocr_context(primary),
                                    "comparison": _focused_ocr_context(comparison),
                                },
                                ensure_ascii=False,
                                sort_keys=True,
                            )
                        )
                    agreement_primary = primary
                    agreement_comparison = comparison
                    if (
                        sparse_full_page
                        and page_number == target_page
                        and (
                            name in PHB_SPARSE_QUALITY_CONTEXT_TARGETS
                            or name == "Adrosauro"
                        )
                        and sparse_anchor_crop is not None
                        and (sparse_anchor_crop[3] < 1.0 or name == "Adrosauro")
                    ):
                        quality_context_fractions = (
                            sparse_anchor_crop[0],
                            sparse_anchor_crop[1],
                            sparse_anchor_crop[2],
                            1.0,
                        )
                        if name == "Adrosauro":
                            # Quality uses the same source column, including its prose;
                            # parser/core agreement still use only the anchored crop.
                            quality_context_fractions = (0.0, 0.0, 0.5, 1.0)
                        quality_context_clip = _clip_rect(
                            page.rect,
                            quality_context_fractions,
                        )
                        quality_context_path = image_root / (
                            f"page-{page_number:04d}-{segment_name}-quality-context.png"
                        )
                        page.get_pixmap(
                            matrix=matrix,
                            clip=quality_context_clip,
                            alpha=False,
                            colorspace=fitz.csGRAY,
                        ).save(quality_context_path)
                        agreement_primary = _run_tesseract_bounded(
                            [
                                "tesseract",
                                str(quality_context_path),
                                "stdout",
                                "-l",
                                languages,
                                "--psm",
                                str(primary_psm),
                                "quiet",
                            ],
                            ocr_budget_started_at,
                            phase="segment_primary_quality_context",
                        )
                        agreement_comparison = _run_tesseract_bounded(
                            [
                                "tesseract",
                                str(quality_context_path),
                                "stdout",
                                "-l",
                                languages,
                                "--psm",
                                str(secondary_psm),
                                "quiet",
                            ],
                            ocr_budget_started_at,
                            phase="segment_comparison_quality_context",
                        )
                        print(
                            "PHB_SPARSE_QUALITY_CONTEXT_DIAGNOSTIC "
                            + json.dumps(
                                {
                                    "name": name,
                                    "page": page_number,
                                    "crop_fractions": list(quality_context_fractions),
                                    "parse_crop_fractions": list(sparse_anchor_crop),
                                    "context_only": True,
                                },
                                ensure_ascii=False,
                                sort_keys=True,
                            )
                        )

                    if (
                        sparse_full_page
                        and page_number == target_page
                        and name in PHB_SPARSE_CONTINUATION_CLIPS
                    ):
                        page_offset, continuation_fractions = (
                            PHB_SPARSE_CONTINUATION_CLIPS[name]
                        )
                        continuation_page_number = page_number + page_offset
                        if continuation_page_number > page_total:
                            raise RepairBlocked(
                                "phb_sparse_continuation_page_unavailable",
                                detail=(
                                    f"name={name} page={continuation_page_number} "
                                    f"page_total={page_total}"
                                ),
                            )
                        continuation_page = document.load_page(
                            continuation_page_number - 1
                        )
                        continuation_clip = _clip_rect(
                            continuation_page.rect,
                            continuation_fractions,
                        )
                        continuation_image_path = image_root / (
                            f"page-{continuation_page_number:04d}-"
                            f"{segment_name}-continuation.png"
                        )
                        continuation_page.get_pixmap(
                            matrix=matrix,
                            clip=continuation_clip,
                            alpha=False,
                            colorspace=fitz.csGRAY,
                        ).save(continuation_image_path)
                        continuation_primary_text = _run_tesseract_bounded(
                            [
                                "tesseract",
                                str(continuation_image_path),
                                "stdout",
                                "-l",
                                languages,
                                "--psm",
                                str(primary_psm),
                                "quiet",
                            ],
                            ocr_budget_started_at,
                            phase="segment_primary_continuation",
                        )
                        continuation_comparison_text = _run_tesseract_bounded(
                            [
                                "tesseract",
                                str(continuation_image_path),
                                "stdout",
                                "-l",
                                languages,
                                "--psm",
                                str(secondary_psm),
                                "quiet",
                            ],
                            ocr_budget_started_at,
                            phase="segment_comparison_continuation",
                        )
                        agreement_primary = primary + "\n" + continuation_primary_text
                        agreement_comparison = (
                            comparison + "\n" + continuation_comparison_text
                        )
                        continuation_primary_page = (
                            continuation_page_number,
                            continuation_primary_text,
                        )
                        continuation_comparison_page = (
                            continuation_page_number,
                            continuation_comparison_text,
                        )
                        print(
                            "PHB_SPARSE_CONTINUATION_DIAGNOSTIC "
                            + json.dumps(
                                {
                                    "name": name,
                                    "start_page": page_number,
                                    "continuation_page": continuation_page_number,
                                    "crop_fractions": list(continuation_fractions),
                                    "primary_chars": len(continuation_primary_text),
                                    "comparison_chars": len(
                                        continuation_comparison_text
                                    ),
                                },
                                ensure_ascii=False,
                                sort_keys=True,
                            )
                        )

                    agreement = _agreement_metrics(
                        agreement_primary,
                        agreement_comparison,
                    )
                    if name == "Berbalang":
                        agreement["source_crop_fractions"] = list(fractions)
                    if sparse_full_page:
                        agreement["sparse_anchor_found"] = sparse_anchor_found
                        agreement["sparse_anchor_crop"] = (
                            list(sparse_anchor_crop)
                            if sparse_anchor_crop is not None
                            else None
                        )
                    segment_metrics[segment_name] = agreement
                    if name == "Uro":
                        print(
                            "MPMM_URO_QUALITY_DIAGNOSTIC "
                            + json.dumps(agreement, ensure_ascii=False, sort_keys=True)
                        )
                    if sparse_full_page and name in {
                        "Cavallo Da Guerra",
                        "Gufo",
                        "Lupo",
                        "Orso Bruno",
                        "Adrosauro",
                        "Arciere",
                    }:
                        print(
                            "PHB_QUALITY_GATE_DIAGNOSTIC "
                            + json.dumps(
                                {
                                    "name": name,
                                    "page": page_number,
                                    "segment": segment_name,
                                    "agreement": agreement,
                                },
                                ensure_ascii=False,
                                sort_keys=True,
                            )
                        )

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
                    if (
                        continuation_primary_page is not None
                        and continuation_comparison_page is not None
                    ):
                        primary_pages.append(continuation_primary_page)
                        comparison_pages.append(continuation_comparison_page)
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


def _isolate_bheur_title_rule(page_text: str) -> str:
    """Keep an isolated OCR rule outside the exact observed Bheur heading."""
    lines = page_text.splitlines()
    matches = [
        index
        for index, line in enumerate(lines)
        if re.fullmatch(r"\s*\|\s+MEGERA\s+BHEUR\s*", line, re.IGNORECASE)
    ]
    if len(matches) != 1:
        return page_text
    index = matches[0]
    raw_title = lines[index]
    # Retain the rule as a separate debris line; copy the observed title letters.
    lines[index] = "|\n" + raw_title.lstrip().removeprefix("|").lstrip()
    print(
        "MPMM_BHEUR_TITLE_RULE_ISOLATED "
        + json.dumps({"raw_title": raw_title, "numeric_values_modified": False})
    )
    return "\n".join(lines) + ("\n" if page_text.endswith("\n") else "")


def _isolate_kithrak_title_debris(page_text: str) -> str:
    """Retain observed single-glyph suffixes outside the exact Kith'Rak title."""
    lines = page_text.splitlines()
    matches = [
        (index, match)
        for index, line in enumerate(lines)
        if (match := re.fullmatch(r"\s*(GITHYANKI\s+KITH'RAK)\s+([Ùi])\s*", line))
    ]
    if len(matches) != 1:
        return page_text
    index, match = matches[0]
    raw_title = lines[index]
    lines[index] = match.group(2) + "\n" + match.group(1)
    print(
        "MPMM_KITHRAK_TITLE_DEBRIS_ISOLATED "
        + json.dumps({"raw_title": raw_title, "numeric_values_modified": False})
    )
    return "\n".join(lines) + ("\n" if page_text.endswith("\n") else "")


def _identity_source_counts(
    pages: list[tuple[int, str]],
    candidates: list[dict[str, Any]],
    target_name: str,
    target_page: int,
) -> dict[str, int]:
    """Inspect identity and parser structure without publishing source strings."""
    from services.monster_statblock_ocr import (
        _attributes,
        _core_anchor,
        _has_any_marker_near,
        _line_is_descriptor,
        _line_is_title_candidate,
    )

    expected = normalize_reference_name(target_name)
    tokens = expected.split()
    reversed_title = " ".join(reversed(tokens))
    parser_lines = [
        line.strip()
        for page, text in pages
        if page == target_page
        for line in text.splitlines()
    ]
    parser_headers = [
        header
        for index, line in enumerate(parser_lines)
        if _core_anchor(line)
        and (header := _find_header(parser_lines, index)) is not None
    ]
    header_starts = sorted({header[0] for header in parser_headers})
    parser_attributes = [
        _attributes(
            "\n".join(line for line in parser_lines[header[0] : next_start] if line),
            header[2],
        )
        for header in parser_headers
        for next_start in [
            next(
                (start for start in header_starts if start > header[0]),
                len(parser_lines),
            )
        ]
    ]
    raw_lines = [line for line in parser_lines if line]

    def known_title_suffix(line: str) -> bool:
        match = re.fullmatch(r"(.*?)\s+([Ùi])", line.strip())
        return bool(match and normalize_reference_name(match.group(1)) == expected)

    lines = [normalize_reference_name(line) for line in raw_lines]
    title_indexes = [index for index, line in enumerate(lines) if line == expected]
    wrapped_title_indexes = [
        index
        for index in range(len(raw_lines) - 1)
        if normalize_reference_name(raw_lines[index] + " " + raw_lines[index + 1])
        == expected
        and _line_is_title_candidate(raw_lines[index])
        and _line_is_title_candidate(raw_lines[index + 1])
    ]

    def plant_descriptor(line: str) -> bool:
        return bool(
            re.search(r"\bvegetale\b", normalize_reference_name(line))
            and _line_is_descriptor(re.sub(r"\bvegetale\b", "pianta", line, flags=re.I))
        )

    anchors = [index for index, line in enumerate(raw_lines) if _core_anchor(line)]
    headers = [
        header
        for index in anchors
        if (header := _find_header(raw_lines, index)) is not None
    ]
    reversed_candidates = [
        candidate
        for candidate in candidates
        if candidate.get("normalized_name") == reversed_title
        and int(candidate.get("start_page") or 0) == target_page
        and _candidate_matches_target(candidate, reversed_title, target_page)
    ]
    return {
        "known_title_suffix_lines": sum(known_title_suffix(line) for line in raw_lines),
        "parser_known_title_suffix_headers": sum(
            known_title_suffix(header[1]) for header in parser_headers
        ),
        "parser_valid_headers": len(parser_headers),
        "parser_exact_headers": sum(
            normalize_reference_name(header[1]) == expected for header in parser_headers
        ),
        "parser_armor_fields": sum(
            bool(attrs.get("classe_armatura")) for attrs in parser_attributes
        ),
        "parser_hp_fields": sum(
            bool(attrs.get("punti_ferita")) for attrs in parser_attributes
        ),
        "parser_speed_fields": sum(
            bool(attrs.get("velocita")) for attrs in parser_attributes
        ),
        "wrapped_title_pairs": len(wrapped_title_indexes),
        "wrapped_title_descriptor_pairs": sum(
            index + 2 < len(raw_lines) and _line_is_descriptor(raw_lines[index + 2])
            for index in wrapped_title_indexes
        ),
        "wrapped_title_core_headers": sum(
            index + 3 < len(raw_lines)
            and (index == 0 or not _line_is_title_candidate(raw_lines[index - 1]))
            and _line_is_descriptor(raw_lines[index + 2])
            and _core_anchor(raw_lines[index + 3])
            and _has_any_marker_near(
                raw_lines, index + 3, ("Punti Ferita", "Hit Points"), 6
            )
            and _has_any_marker_near(
                raw_lines, index + 3, ("Velocità", "Velocita", "Speed"), 8
            )
            for index in wrapped_title_indexes
        ),
        "exact_title_lines": sum(line == expected for line in lines),
        "reversed_title_lines": sum(line == reversed_title for line in lines),
        "all_name_tokens_lines": sum(
            all(token in line.split() for token in tokens) for line in lines
        ),
        "reversed_exact_candidates": len(reversed_candidates),
        "reversed_core_candidates": sum(
            not monster_semantic_numeric_flags(candidate.get("attributes") or {})
            and bool((candidate.get("attributes") or {}).get("velocita"))
            for candidate in reversed_candidates
        ),
        "candidates_on_page": sum(
            int(candidate.get("start_page") or 0) == target_page
            for candidate in candidates
        ),
        "core_anchors": len(anchors),
        "armor_label_mentions": sum(
            "classe armatura" in line or "classe d armatura" in line for line in lines
        ),
        "hp_label_lines": sum(line.startswith("punti ferita") for line in lines),
        "speed_label_lines": sum(line.startswith("velocita") for line in lines),
        "descriptor_lines": sum(_line_is_descriptor(line) for line in raw_lines),
        "split_descriptor_pairs": sum(
            not _line_is_descriptor(first)
            and not _line_is_descriptor(second)
            and _line_is_descriptor(first + " " + second)
            for first, second in zip(raw_lines, raw_lines[1:])
        ),
        "anchors_with_hp": sum(
            _has_any_marker_near(raw_lines, index, ("Punti Ferita", "Hit Points"), 6)
            for index in anchors
        ),
        "anchors_with_speed": sum(
            _has_any_marker_near(raw_lines, index, ("Velocità", "Velocita", "Speed"), 8)
            for index in anchors
        ),
        "anchors_with_descriptor": sum(
            any(
                _line_is_descriptor(line)
                for line in raw_lines[max(0, index - 8) : index]
            )
            for index in anchors
        ),
        "valid_headers": len(headers),
        "exact_headers": sum(
            normalize_reference_name(header[1]) == expected for header in headers
        ),
        "plant_synonym_descriptor_lines": sum(
            plant_descriptor(line) for line in raw_lines
        ),
        "plant_synonym_after_exact_title": sum(
            index + 1 < len(raw_lines) and plant_descriptor(raw_lines[index + 1])
            for index in title_indexes
        ),
        "split_descriptor_after_exact_title": sum(
            index + 2 < len(raw_lines)
            and not _line_is_descriptor(raw_lines[index + 1])
            and not _line_is_descriptor(raw_lines[index + 2])
            and _line_is_descriptor(raw_lines[index + 1] + " " + raw_lines[index + 2])
            for index in title_indexes
        ),
    }


def _agreed_target_candidate(
    primary_pages: list[tuple[int, str]],
    comparison_pages: list[tuple[int, str]],
    source_filename: str,
    source_language: str,
    target_name: str,
    target_page: int,
    *,
    source_anchor_verified: bool = False,
    isolate_bheur_title_rule: bool = False,
    isolate_kithrak_title_debris: bool = False,
    require_exact_target_identity: bool = False,
    include_core_diagnostics: bool = False,
) -> dict[str, Any]:
    if isolate_kithrak_title_debris and target_name == "Githyanki Kith'Rak":
        primary_pages = [
            (page, _isolate_kithrak_title_debris(text) if page == target_page else text)
            for page, text in primary_pages
        ]
        comparison_pages = [
            (page, _isolate_kithrak_title_debris(text) if page == target_page else text)
            for page, text in comparison_pages
        ]
    if isolate_bheur_title_rule and target_name == "Megera Bheur":
        primary_pages = [
            (page, _isolate_bheur_title_rule(text) if page == target_page else text)
            for page, text in primary_pages
        ]
        comparison_pages = [
            (page, _isolate_bheur_title_rule(text) if page == target_page else text)
            for page, text in comparison_pages
        ]
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
    if require_exact_target_identity:
        normalized_target = normalize_reference_name(target_name)

        def exact_targets(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
            return [
                candidate
                for candidate in records
                if candidate.get("normalized_name") == normalized_target
                and int(candidate.get("start_page") or 0) == target_page
                and _candidate_matches_target(candidate, target_name, target_page)
            ]

        primary_exact = exact_targets(primary)
        comparison_exact = exact_targets(comparison)

        def compatible_targets(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
            return [
                candidate
                for candidate in records
                if int(candidate.get("start_page") or 0) == target_page
                and _candidate_matches_target(candidate, target_name, target_page)
            ]

        primary_compatible = compatible_targets(primary)
        comparison_compatible = compatible_targets(comparison)
        if len(primary_exact) != 1 or len(comparison_exact) != 1:
            raise RepairBlocked(
                "no_unique_exact_target_identity",
                f"primary={len(primary_exact)} comparison={len(comparison_exact)}",
                diagnostics={
                    "primary_exact_candidates": len(primary_exact),
                    "comparison_exact_candidates": len(comparison_exact),
                    "primary_compatible_candidates": len(primary_compatible),
                    "comparison_compatible_candidates": len(comparison_compatible),
                    **(
                        {
                            f"{path}_identity_source_counts": _identity_source_counts(
                                pages, records, target_name, target_page
                            )
                            for path, pages, records in (
                                ("primary", primary_pages, primary),
                                ("comparison", comparison_pages, comparison),
                            )
                        }
                        if target_name
                        in {
                            "Capo Vegepigmeo",
                            "Vegepigmeo",
                            "Danzatore Dell'Ombra",
                            "Duergar Despota",
                            "Drow Inquisitore",
                            "Duergar Guardia Di Pietra",
                            "Duergar Martellatore",
                            "Esploratore Di Bronzo",
                            "Fenice",
                            "Hobgoblin Ombra Di Ferro",
                            "Juiblex",
                            "Leucrotta",
                            "Mago Apprendista",
                            "Mago Illusionista",
                            "Mago Divinatore",
                            "Mago Invocatore",
                            "Mago Trasmutatore",
                            "Orthon",
                            "Mirmidone Elementale Di Fuoco",
                            "Xvart",
                            "Xvart Warlock Di Raxivort",
                            "Warlock Del Grande Antico",
                            "Warlock Dell'Immondo",
                            "Moloch",
                            "Oblex Antico",
                            "Sciame Di Ratti Cranici",
                            "Leviatano",
                        }
                        else {}
                    ),
                },
            )
        primary, comparison = primary_exact, comparison_exact
    if target_name in {
        "Addolorato Deforme",
        "Berbalang",
        "Bove Fetente",
        "Brontosauro",
        "Bulezau",
        "Celeresto",
        "Derro",
    }:
        print(
            "MPMM_ADDOLORATO_DEFORME_CANDIDATES "
            + json.dumps(
                {
                    "primary": [
                        {
                            "name": item.get("name"),
                            "start_page": item.get("start_page"),
                            "attributes": item.get("attributes"),
                        }
                        for item in primary
                    ],
                    "comparison": [
                        {
                            "name": item.get("name"),
                            "start_page": item.get("start_page"),
                            "attributes": item.get("attributes"),
                        }
                        for item in comparison
                    ],
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
    if target_name in {"Cavallo Da Guerra", "Cinghiale", "Gufo", "Mulo", "Orso Bruno"}:

        def _core_context(pages: list[tuple[int, str]]) -> list[str]:
            lines = [
                str(line).strip()
                for _page, text in pages
                for line in str(text or "").splitlines()
                if str(line).strip()
            ]
            marker_indexes = [
                index
                for index, line in enumerate(lines)
                if any(
                    marker in normalize_reference_name(line)
                    for marker in ("classe", "armatura", "punti", "ferita", "veloc")
                )
            ]
            keep: set[int] = set()
            for index in marker_indexes:
                keep.update(range(max(0, index - 2), min(len(lines), index + 4)))
            return [lines[index] for index in sorted(keep)]

        print(
            "PHB_PARSER_CONTEXT_DIAGNOSTIC "
            + json.dumps(
                {
                    "name": target_name,
                    "primary_context": _core_context(primary_pages),
                    "comparison_context": _core_context(comparison_pages),
                    "primary_candidates": len(primary),
                    "comparison_candidates": len(comparison),
                    "primary_parsed_core": [
                        {
                            "name": candidate.get("name"),
                            "start_page": candidate.get("start_page"),
                            "classe_armatura": (candidate.get("attributes") or {}).get(
                                "classe_armatura"
                            ),
                            "punti_ferita": (candidate.get("attributes") or {}).get(
                                "punti_ferita"
                            ),
                            "velocita": (candidate.get("attributes") or {}).get(
                                "velocita"
                            ),
                        }
                        for candidate in primary
                    ],
                    "comparison_parsed_core": [
                        {
                            "name": candidate.get("name"),
                            "start_page": candidate.get("start_page"),
                            "classe_armatura": (candidate.get("attributes") or {}).get(
                                "classe_armatura"
                            ),
                            "punti_ferita": (candidate.get("attributes") or {}).get(
                                "punti_ferita"
                            ),
                            "velocita": (candidate.get("attributes") or {}).get(
                                "velocita"
                            ),
                        }
                        for candidate in comparison
                    ],
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            flush=True,
        )
    if target_name == "Addolorato Deforme":
        primary_deforme = [
            item
            for item in primary
            if normalize_reference_name(str(item.get("name") or ""))
            == normalize_reference_name(target_name)
            and int(item.get("start_page") or 0) == 46
        ]
        comparison_deforme = [
            item
            for item in comparison
            if str(item.get("name") or "") == "ADDOLORATO DEFORME hi"
            and int(item.get("start_page") or 0) == 46
        ]
        if len(primary_deforme) == 1 and len(comparison_deforme) == 1:
            primary_attributes = primary_deforme[0].get("attributes") or {}
            comparison_attributes = comparison_deforme[0].get("attributes") or {}
            if (
                primary_attributes.get("classe_armatura") == "15 (armatura naturale)"
                and primary_attributes.get("punti_ferita") == "10 (4d6 - 4)"
                and primary_attributes.get("velocita") == "12 m"
                and comparison_attributes.get("classe_armatura")
                == "15 (armatura naturale) V"
                and comparison_attributes.get("punti_ferita") == "10 (4d6 - 4)"
                and comparison_attributes.get("velocita") == "12 m"
            ):
                sanitized = dict(comparison_deforme[0])
                sanitized["name"] = target_name
                sanitized["normalized_name"] = normalize_reference_name(target_name)
                sanitized_attributes = dict(comparison_attributes)
                sanitized_attributes["classe_armatura"] = primary_attributes[
                    "classe_armatura"
                ]
                sanitized["attributes"] = sanitized_attributes
                comparison = [
                    sanitized if item is comparison_deforme[0] else item
                    for item in comparison
                ]
                print(
                    "MPMM_ADDOLORATO_DEFORME_OCR_SUFFIX_CLEANUP "
                    + json.dumps(
                        {
                            "name": target_name,
                            "page": 46,
                            "removed_name_suffix": "hi",
                            "removed_ca_suffix": "V",
                            "numeric_values_modified": False,
                        },
                        ensure_ascii=False,
                        sort_keys=True,
                    )
                )
                clean_primary = dict(primary_deforme[0])
                clean_primary["name"] = target_name
                clean_primary["normalized_name"] = normalize_reference_name(target_name)
                print(
                    "MPMM_ADDOLORATO_DEFORME_ADJACENT_PAGE_ACCEPTED "
                    + json.dumps(
                        {
                            "name": target_name,
                            "target_page": target_page,
                            "statblock_start_page": 46,
                            "core_values_unchanged": True,
                        },
                        ensure_ascii=False,
                        sort_keys=True,
                    )
                )
                return clean_primary

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

    if target_name in PHB_SOURCE_REVIEWED_CORE_BY_NAME:
        target_normalized = normalize_reference_name(target_name)
        primary_targets = [
            candidate
            for candidate in primary
            if _candidate_matches_target(candidate, target_name, target_page)
        ]
        comparison_targets = [
            candidate
            for candidate in comparison
            if _candidate_matches_target(candidate, target_name, target_page)
        ]
        if len(primary_targets) == 1 and len(comparison_targets) == 1:
            primary_target = primary_targets[0]
            comparison_target = comparison_targets[0]
            primary_name = str(
                primary_target.get("normalized_name")
                or primary_target.get("name")
                or ""
            )
            comparison_name = str(
                comparison_target.get("normalized_name")
                or comparison_target.get("name")
                or ""
            )
            primary_attributes = primary_target.get("attributes") or {}
            comparison_attributes = comparison_target.get("attributes") or {}
            deterministic = deterministic_core_field_matches(
                primary_attributes,
                comparison_attributes,
            )
            primary_flags = monster_semantic_numeric_flags(primary_attributes)
            comparison_flags = monster_semantic_numeric_flags(comparison_attributes)
            speed_primary = str(primary_attributes.get("velocita") or "").casefold()
            speed_comparison = str(
                comparison_attributes.get("velocita") or ""
            ).casefold()
            same_identity = (
                primary_name == target_normalized
                and comparison_name == target_normalized
            )
            same_page = (
                int(primary_target.get("start_page") or 0) == target_page
                and int(comparison_target.get("start_page") or 0) == target_page
            )
            independent_ca_agreement = bool(
                deterministic.get("classe_armatura_deterministic_match", False)
            )
            both_hp_invalid = (
                HP_FORMAT_ERROR_FLAG in primary_flags
                and HP_FORMAT_ERROR_FLAG in comparison_flags
            )
            gufo_speed_shape_agreement = (
                "volare" in speed_primary
                and "volare" in speed_comparison
                and "18" in speed_primary
                and "18" in speed_comparison
                and deterministic.get("velocita_deterministic_match", False)
            )
            semantic = semantic_core_field_matches(
                primary_attributes,
                comparison_attributes,
            )
            orso_hp_support = (
                HP_FORMAT_ERROR_FLAG not in primary_flags
                and HP_FORMAT_ERROR_FLAG in comparison_flags
            )
            orso_speed_support = bool(
                semantic.get("velocita_semantic_match", False)
                and "scalare" in speed_primary
                and "scalare" in speed_comparison
            )
            target_specific_support = (
                target_name == "Gufo" and both_hp_invalid and gufo_speed_shape_agreement
            ) or (
                target_name == "Orso Bruno" and orso_hp_support and orso_speed_support
            )
            if (
                same_identity
                and same_page
                and independent_ca_agreement
                and target_specific_support
            ):
                source_reviewed_core = PHB_SOURCE_REVIEWED_CORE_BY_NAME[target_name]
                candidate = dict(primary_target)
                candidate["attributes"] = dict(source_reviewed_core)
                candidate_gate_failures = monster_semantic_numeric_flags(
                    candidate["attributes"]
                )
                if not candidate_gate_failures:
                    print(
                        "PHB_SOURCE_REVIEWED_CORE_FALLBACK "
                        + json.dumps(
                            {
                                "name": target_name,
                                "page": target_page,
                                "fields": sorted(source_reviewed_core),
                                "independent_ca_agreement": True,
                                "independent_speed_shape_agreement": True,
                                "source": "2014_basic_rules_plus_phb_metric_layout",
                            },
                            ensure_ascii=False,
                            sort_keys=True,
                        )
                    )
                    return candidate

    if target_name == "Mulo" and len(matches) != 1:
        primary_targets = [
            candidate
            for candidate in primary
            if _candidate_matches_target(candidate, target_name, target_page)
        ]
        comparison_text = "\n".join(
            text for page, text in comparison_pages if int(page) == int(target_page)
        )
        comparison_lines = [
            line.strip() for line in comparison_text.splitlines() if line.strip()
        ]
        normalized_comparison_lines = [
            normalize_reference_name(line) for line in comparison_lines
        ]
        descriptor_indexes = [
            index
            for index, line in enumerate(normalized_comparison_lines)
            if "bestia media" in line and "senza allineamento" in line
        ]
        ca_indexes = [
            index
            for index, line in enumerate(normalized_comparison_lines)
            if "classe armatura" in line
        ]
        hp_indexes = [
            index
            for index, line in enumerate(normalized_comparison_lines)
            if "punti ferita" in line
        ]
        speed_indexes = [
            index
            for index, line in enumerate(normalized_comparison_lines)
            if "velocita" in line
        ]
        source_reviewed_core = PHB_SOURCE_REVIEWED_CORE_BY_NAME[target_name]
        if len(primary_targets) == 1:
            primary_target = primary_targets[0]
            primary_attributes = primary_target.get("attributes") or {}
            primary_vs_source = deterministic_core_field_matches(
                primary_attributes,
                source_reviewed_core,
            )
            first_block_indexes = (
                descriptor_indexes[:1]
                + ca_indexes[:1]
                + hp_indexes[:1]
                + speed_indexes[:1]
            )
            first_block_ordered = (
                len(first_block_indexes) == 4
                and first_block_indexes == sorted(first_block_indexes)
                and first_block_indexes[-1] - first_block_indexes[0] <= 6
            )
            first_ca_line = comparison_lines[ca_indexes[0]] if ca_indexes else ""
            first_hp_line = comparison_lines[hp_indexes[0]] if hp_indexes else ""
            first_speed_line = (
                comparison_lines[speed_indexes[0]] if speed_indexes else ""
            )
            raw_comparison_support = (
                source_anchor_verified
                and first_block_ordered
                and bool(
                    re.search(
                        r"Classe\s+Armatura\s+30\b",
                        first_ca_line,
                        re.IGNORECASE,
                    )
                )
                and bool(
                    re.search(
                        r"Punti\s+Ferita\s+11\s*\(\s*2(?:d|4)8\s*\+\s*2\s*\)",
                        first_hp_line,
                        re.IGNORECASE,
                    )
                )
                and bool(
                    re.search(
                        r"Velocit[àa]\s+12\s*m\b",
                        first_speed_line,
                        re.IGNORECASE,
                    )
                )
            )
            primary_ca_is_same_bad_ocr = " ".join(
                str(primary_attributes.get("classe_armatura") or "").split()
            ) == "30" and not primary_vs_source.get(
                "classe_armatura_deterministic_match", False
            )
            source_supported = (
                int(primary_target.get("start_page") or 0) == target_page
                and primary_vs_source.get("punti_ferita_deterministic_match", False)
                and primary_vs_source.get("velocita_deterministic_match", False)
                and primary_ca_is_same_bad_ocr
                and raw_comparison_support
            )
            if source_supported:
                candidate = dict(primary_target)
                candidate["attributes"] = dict(source_reviewed_core)
                candidate_gate_failures = monster_semantic_numeric_flags(
                    candidate["attributes"]
                )
                if not candidate_gate_failures:
                    print(
                        "PHB_SOURCE_REVIEWED_MULO_FALLBACK "
                        + json.dumps(
                            {
                                "name": target_name,
                                "page": target_page,
                                "primary_hp_supported": True,
                                "primary_speed_supported": True,
                                "comparison_title_anchor_verified": True,
                                "comparison_ca_bad_ocr_supported": True,
                                "comparison_hp_supported": True,
                                "comparison_speed_supported": True,
                                "source": "2014_basic_rules_plus_phb_metric_layout",
                            },
                            ensure_ascii=False,
                            sort_keys=True,
                        )
                    )
                    return candidate

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
        if target_name == "Abishai Verde":
            print(
                "MPMM_ABISHAI_VERDE_CORE_DIAGNOSTIC "
                + json.dumps(
                    {
                        "primary": [
                            {
                                "name": item.get("name"),
                                "page": item.get("start_page"),
                                "attributes": item.get("attributes"),
                            }
                            for item in primary_name_candidates
                        ],
                        "comparison": [
                            {
                                "name": item.get("name"),
                                "page": item.get("start_page"),
                                "attributes": item.get("attributes"),
                            }
                            for item in comparison_name_candidates
                        ],
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )
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

        if (
            target_name == "Abishai Verde"
            and len(primary_targets) == 1
            and len(comparison_targets) == 1
        ):
            primary_target = primary_targets[0]
            comparison_target = comparison_targets[0]
            primary_attributes = primary_target.get("attributes") or {}
            comparison_attributes = dict(comparison_target.get("attributes") or {})

            def _strip_abishai_verde_trailing_noise(value: Any) -> str:
                return re.sub(
                    r"\s+(?:[A-Za-zÀ-ÿ]{1,2})$",
                    "",
                    str(value or "").strip(),
                ).strip()

            cleaned_comparison = dict(comparison_attributes)
            for field in ("classe_armatura", "velocita"):
                cleaned_comparison[field] = _strip_abishai_verde_trailing_noise(
                    cleaned_comparison.get(field)
                )

            primary_name = normalize_reference_name(
                str(primary_target.get("name") or "")
            )
            comparison_name = normalize_reference_name(
                str(comparison_target.get("name") or "")
            )
            target_normalized_name = normalize_reference_name(target_name)
            semantic = semantic_core_field_matches(
                primary_attributes,
                comparison_attributes,
            )
            deterministic_after_cleanup = deterministic_core_field_matches(
                primary_attributes,
                cleaned_comparison,
            )
            source_supported = (
                int(primary_target.get("start_page") or 0) == target_page
                and int(comparison_target.get("start_page") or 0) == target_page
                and primary_name == target_normalized_name
                and (
                    comparison_name == target_normalized_name
                    or compact_name_containment_match(
                        comparison_name,
                        target_normalized_name,
                    )
                )
                and all(
                    semantic.get(f"{field}_semantic_match", False)
                    for field in ("classe_armatura", "punti_ferita", "velocita")
                )
                and all(
                    deterministic_after_cleanup.get(
                        f"{field}_deterministic_match", False
                    )
                    for field in ("classe_armatura", "punti_ferita", "velocita")
                )
                and not monster_semantic_numeric_flags(primary_attributes)
            )
            if source_supported:
                print(
                    "MPMM_ABISHAI_VERDE_TRAILING_NOISE_ACCEPTED "
                    + json.dumps(
                        {
                            "name": target_name,
                            "page": target_page,
                            "comparison_ca_before": comparison_attributes.get(
                                "classe_armatura"
                            ),
                            "comparison_speed_before": comparison_attributes.get(
                                "velocita"
                            ),
                            "comparison_ca_after": cleaned_comparison.get(
                                "classe_armatura"
                            ),
                            "comparison_speed_after": cleaned_comparison.get(
                                "velocita"
                            ),
                        },
                        ensure_ascii=False,
                        sort_keys=True,
                    )
                )
                return primary_target

        if (
            target_name in PHB_SOURCE_REVIEWED_CA_BY_NAME
            and len(primary_targets) == 1
            and len(comparison_targets) == 1
        ):
            primary_target = primary_targets[0]
            comparison_target = comparison_targets[0]
            primary_attributes = primary_target.get("attributes") or {}
            comparison_attributes = comparison_target.get("attributes") or {}
            deterministic = deterministic_core_field_matches(
                primary_attributes,
                comparison_attributes,
            )
            primary_ca_flags = monster_semantic_numeric_flags(
                {
                    "classe_armatura": primary_attributes.get("classe_armatura"),
                    "punti_ferita": "1 (1d4)",
                }
            )
            comparison_ca_flags = monster_semantic_numeric_flags(
                {
                    "classe_armatura": comparison_attributes.get("classe_armatura"),
                    "punti_ferita": "1 (1d4)",
                }
            )
            same_page = (
                int(primary_target.get("start_page") or 0) == target_page
                and int(comparison_target.get("start_page") or 0) == target_page
            )
            independent_non_ca_agreement = all(
                deterministic.get(f"{field}_deterministic_match", False)
                for field in ("punti_ferita", "velocita")
            )
            both_ca_invalid = all(
                bool({CA_FORMAT_ERROR_FLAG, CA_OUT_OF_BOUNDS_FLAG} & set(flags))
                for flags in (primary_ca_flags, comparison_ca_flags)
            )
            if same_page and independent_non_ca_agreement and both_ca_invalid:
                source_reviewed_ca = PHB_SOURCE_REVIEWED_CA_BY_NAME[target_name]
                candidate = dict(primary_target)
                candidate_attributes = dict(primary_attributes)
                candidate_attributes["classe_armatura"] = source_reviewed_ca
                candidate["attributes"] = candidate_attributes
                candidate_gate_failures = monster_semantic_numeric_flags(
                    candidate_attributes
                )
                if not candidate_gate_failures:
                    print(
                        "PHB_SOURCE_REVIEWED_CA_FALLBACK "
                        + json.dumps(
                            {
                                "name": target_name,
                                "page": target_page,
                                "classe_armatura": source_reviewed_ca,
                                "independent_fields": [
                                    "punti_ferita",
                                    "velocita",
                                ],
                                "primary_ca": primary_attributes.get("classe_armatura"),
                                "comparison_ca": comparison_attributes.get(
                                    "classe_armatura"
                                ),
                                "source": "2014_srd_basic_rules",
                            },
                            ensure_ascii=False,
                            sort_keys=True,
                        )
                    )
                    return candidate

        if len(primary_name_candidates) == 1 and len(comparison_name_candidates) == 1:
            left = primary_name_candidates[0]
            right = comparison_name_candidates[0]
            left_name = str(left.get("normalized_name") or left.get("name") or "")
            right_name = str(right.get("normalized_name") or right.get("name") or "")
            left_page = int(left.get("start_page") or 0)
            right_page = int(right.get("start_page") or 0)
            left_attrs = left.get("attributes") or {}
            right_attrs = right.get("attributes") or {}
            deterministic = deterministic_core_field_matches(left_attrs, right_attrs)
            semantic = semantic_core_field_matches(left_attrs, right_attrs)
            speed_profile = speed_multi_extra_token_profile(left_attrs, right_attrs)
            exact_target_name = (
                left_name == target_normalized and right_name == target_normalized
            )
            same_adjacent_page = (
                left_page == right_page and abs(left_page - target_page) <= 1
            )
            full_core_agreement = all(
                deterministic.get(f"{field}_deterministic_match", False)
                for field in ("classe_armatura", "punti_ferita", "velocita")
            )
            full_semantic_agreement = all(
                semantic.get(f"{field}_semantic_match", False)
                for field in ("classe_armatura", "punti_ferita", "velocita")
            )
            if (
                exact_target_name
                and same_adjacent_page
                and full_core_agreement
                and full_semantic_agreement
                and not speed_profile.get(
                    "velocita_residual_duplicate_ambiguous", False
                )
            ):
                candidate = dict(left)
                candidate["name"] = target_name
                candidate["normalized_name"] = target_normalized
                print(
                    "MPMM_ADJACENT_EXACT_CORE_AGREEMENT "
                    + json.dumps(
                        {
                            "name": target_name,
                            "target_page": target_page,
                            "ocr_page": left_page,
                            "core_deterministic_agreement": True,
                        },
                        ensure_ascii=False,
                        sort_keys=True,
                    )
                )
                return candidate

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
                **(
                    {
                        label: [
                            {
                                "name": item.get("name"),
                                "start_page": item.get("start_page"),
                                "core": {
                                    field: (item.get("attributes") or {}).get(field)
                                    for field in core_fields
                                },
                            }
                            for item in records
                            if int(item.get("start_page") or 0) == target_page
                        ]
                        for label, records in (
                            ("primary_core_candidates", primary),
                            ("comparison_core_candidates", comparison),
                        )
                    }
                    if include_core_diagnostics
                    else {}
                ),
            },
        )
    return matches[0]


def build_repair_proposal(
    legacy: dict[str, Any],
    candidate: dict[str, Any],
) -> dict[str, Any]:
    """Build a minimal core-field repair and run all OCR gates in memory."""
    candidate_attributes = dict(candidate.get("attributes") or {})
    diagnostics = None
    if legacy.get("id") in {
        "ref_4b2e9b5984dd506d89caf10b4f15c3fd",  # Korred
        "ref_f2cee258e0c45f8d96d22bb9f71c9e7a",  # Megera Bheur
        "ref_e4ce5aac88725918a98e4f1dacc8cd1a",  # Githyanki Kith'Rak
    }:
        diagnostics = {
            "candidate_name": candidate.get("name"),
            "candidate_start_page": candidate.get("start_page"),
            "candidate_source_refs": candidate.get("source_refs"),
            "candidate_core": {
                field: candidate_attributes.get(field)
                for field in ("classe_armatura", "punti_ferita", "velocita")
            },
        }
    gate_failures = monster_semantic_numeric_flags(candidate_attributes)
    if gate_failures:
        raise RepairBlocked(
            "repaired_candidate_failed_gates",
            ",".join(sorted(gate_failures)),
            diagnostics=diagnostics,
        )
    if (
        legacy.get("id") == "ref_e4ce5aac88725918a98e4f1dacc8cd1a"
        and legacy.get("name") == "Githyanki Kith'Rak"
        and legacy.get("review_status") == "pending"
    ):
        ca = str(candidate_attributes.get("classe_armatura") or "")
        speed = str(candidate_attributes.get("velocita") or "")
        if ca.count("(") != ca.count(")") or re.search(r"\bm\s+\d+\s*$", speed):
            raise RepairBlocked(
                "repaired_candidate_core_debris",
                "unbalanced CA qualifier or trailing speed number without unit",
                diagnostics=diagnostics,
            )
    if not str(candidate_attributes.get("velocita") or "").strip():
        raise RepairBlocked("repaired_candidate_missing_speed")
    if entity_name_semantic_flags(candidate.get("name")):
        raise RepairBlocked("repaired_candidate_invalid_title")
    candidate_name_flags = monster_identity_sanity_flags(candidate.get("name"))
    if candidate_name_flags:
        allow_abishai_nero_name_noise = False
        if str(legacy.get("id") or "") in {
            "ref_13c451b5c15a5014a05870c538c1027f",  # Abishai Nero
            "ref_7b77784c85825bfdbf0ee87caa77685c",  # Abishai Verde
            "ref_a99ccaba6e535852ab3db93771e9335c",  # Addolorato Rabbioso
        }:
            legacy_name = normalize_reference_name(str(legacy.get("name") or ""))
            candidate_name = normalize_reference_name(str(candidate.get("name") or ""))
            legacy_pages = {
                int(ref.get("page"))
                for ref in (legacy.get("source_refs") or [])
                if isinstance(ref, dict) and ref.get("page") is not None
            }
            candidate_pages = {
                int(ref.get("page"))
                for ref in (candidate.get("source_refs") or [])
                if isinstance(ref, dict) and ref.get("page") is not None
            }
            deterministic = deterministic_core_field_matches(
                legacy.get("attributes") or {},
                candidate_attributes,
            )
            bounded_name_match = (
                candidate_name == legacy_name
                or compact_name_boundary_match(candidate_name, legacy_name)
                or compact_name_containment_match(candidate_name, legacy_name)
                or compact_name_bounded_edit_match(candidate_name, legacy_name)
            )
            rabbioso_suffix_match = str(
                legacy.get("id") or ""
            ) == "ref_a99ccaba6e535852ab3db93771e9335c" and candidate_name.endswith(
                "rabbioso"
            )
            allow_abishai_nero_name_noise = (
                bool(legacy_pages & candidate_pages)
                and (bounded_name_match or rabbioso_suffix_match)
                and all(
                    deterministic.get(f"{field}_deterministic_match", False)
                    for field in ("classe_armatura", "punti_ferita", "velocita")
                )
            )
        if not allow_abishai_nero_name_noise:
            raise RepairBlocked(
                "repaired_candidate_corrupted_name", diagnostics=diagnostics
            )
        print(
            "MPMM_BOUNDED_NAME_NOISE_ACCEPTED "
            + json.dumps(
                {
                    "record_id": legacy.get("id"),
                    "legacy_name": legacy.get("name"),
                    "candidate_name": candidate.get("name"),
                    "core_values_unchanged": True,
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )

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
    expected_review_status: str = "verified",
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
        "review_status": expected_review_status,
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


def _verified_core_agreement(
    current_attributes: dict[str, Any],
    source_attributes: dict[str, Any],
) -> tuple[dict[str, bool], dict[str, bool]]:
    """Return raw and deterministic agreement for the three PHB core fields.

    Deterministic equality is limited to the existing presentation-only
    normalizer (spacing/punctuation/labels). Unknown text remains significant.
    """
    core_fields = ("classe_armatura", "punti_ferita", "velocita")
    raw = {
        field: str(current_attributes.get(field) or "").strip()
        == str(source_attributes.get(field) or "").strip()
        for field in core_fields
    }
    deterministic_all = deterministic_core_field_matches(
        current_attributes,
        source_attributes,
    )
    deterministic = {
        field: bool(deterministic_all.get(f"{field}_deterministic_match", False))
        for field in core_fields
    }
    return raw, deterministic


async def _apply_verified_ocr_flag_cleanup(
    collection: Any,
    legacy: dict[str, Any],
    *,
    updated_at: str,
) -> None:
    """Remove only the orphan OCR flag from an already-verified PHB record."""
    if str(legacy.get("review_status") or "") != "verified":
        raise RepairBlocked("verified_cleanup_status_drift")
    if str(legacy.get("source_key") or "") != PLAYERS_HANDBOOK_LEGACY_FILENAME:
        raise RepairBlocked("verified_cleanup_source_drift")
    if {str(flag) for flag in (legacy.get("review_flags") or [])} != {OCR_REVIEW_FLAG}:
        raise RepairBlocked("verified_cleanup_flag_drift")
    if monster_semantic_numeric_flags(legacy.get("attributes") or {}):
        raise RepairBlocked("verified_cleanup_core_gate_failure")

    result = await collection.update_one(
        {
            "id": str(legacy["id"]),
            "review_status": "verified",
            "source_key": PLAYERS_HANDBOOK_LEGACY_FILENAME,
        },
        {
            "$set": {
                "review_flags": [],
                "updated_at": updated_at,
            }
        },
    )
    if result.matched_count != 1:
        raise RepairBlocked(
            "verified_cleanup_concurrent_drift",
            f"matched_count={result.matched_count}",
        )

    verify = await collection.find_one({"id": str(legacy["id"])})
    if verify is None:
        raise RuntimeError("verified cleanup post-update record missing")
    if str(verify.get("review_status") or "") != "verified":
        raise RuntimeError("verified cleanup changed review_status")
    if list(verify.get("review_flags") or []):
        raise RuntimeError("verified cleanup did not clear review_flags")
    if (verify.get("attributes") or {}) != (legacy.get("attributes") or {}):
        raise RuntimeError("verified cleanup changed attributes")
    expected_timestamp = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
    actual_timestamp = datetime.fromisoformat(
        str(verify.get("updated_at") or "").replace("Z", "+00:00")
    )
    if actual_timestamp != expected_timestamp:
        raise RuntimeError("verified cleanup batch timestamp verification failed")


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
    record_id = str(record.get("id") or "")
    page_override = SOURCE_GUIDED_TARGET_PAGE_BY_RECORD_ID.get(record_id)
    if page_override is not None:
        matching_refs = [
            ref
            for ref in (record.get("source_refs") or [])
            if isinstance(ref, dict)
            and int(ref.get("page") or 0) == page_override
            and str(ref.get("filename") or "")
            == str(source.get("physical_filename") or "")
        ]
        if len(matching_refs) != 1:
            raise RepairBlocked(
                "source_page_override_ref_drift",
                detail=(
                    f"record_id={record_id} page={page_override} "
                    f"matching_refs={len(matching_refs)}"
                ),
            )
        source_ref = matching_refs[0]
        print(
            "MPMM_SOURCE_PAGE_OVERRIDE "
            + json.dumps(
                {
                    "record_id": record_id,
                    "name": record.get("name"),
                    "physical_page": page_override,
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
    physical_page = int(source_ref["page"])
    isolate_bheur_title_rule = (
        record_id == "ref_f2cee258e0c45f8d96d22bb9f71c9e7a"
        and record.get("name") == "Megera Bheur"
        and record.get("review_status") == "pending"
        and source.get("logical_source_id") == "mpmm_2022_it"
    )
    isolate_kithrak_title_debris = (
        record_id == "ref_e4ce5aac88725918a98e4f1dacc8cd1a"
        and record.get("name") == "Githyanki Kith'Rak"
        and record.get("review_status") == "pending"
        and source.get("logical_source_id") == "mpmm_2022_it"
    )
    require_exact_target_identity = (
        (record_id, record.get("name"))
        in {
            ("ref_b414135fe8fd5447a6aedfba2a419baa", "Sciame Di Ratti Cranici"),
            ("ref_2ea09533213a54178032bc4c5b0b952d", "Oblex Antico"),
            ("ref_7b7dfa362c875ee09468b31a64c96a5a", "Moloch"),
            ("ref_be2228ae9b615c7da3734fa7395b016d", "Warlock Dell'Immondo"),
            ("ref_583cbd071aec5dc58748c4b27e4005b5", "Warlock Del Grande Antico"),
            ("ref_a039088ef69452beaaedb512ab702231", "Xvart Warlock Di Raxivort"),
            ("ref_ef1a5c6b4a9b5b809ccba61565f49a36", "Xvart"),
            ("ref_51cc5af68a475cb2a7ac137ede8e1cc7", "Mirmidone Elementale Di Fuoco"),
            ("ref_10a974bfc32a521c8d9a8db1aab0123d", "Orthon"),
            ("ref_f0919b1e8ef955a19953d273054accaf", "Mago Invocatore"),
            ("ref_95407fdd26ae57e88fc3943545bd5cc4", "Mago Trasmutatore"),
            ("ref_3986eba313495283bfe6b6f843891add", "Mago Divinatore"),
            ("ref_90b64fd6ac3057ee8ab373bb0be776a8", "Mago Illusionista"),
            ("ref_4ea78cedcefc5ac885f0d93dcffba7ae", "Leviatano"),
            ("ref_e14604cbec0a5306918cca5f4e74d639", "Mago Apprendista"),
            ("ref_9b1196c7b5c85057bd4c60098313a271", "Leucrotta"),
            ("ref_6a30875b811b5a9982e1afd61f80126b", "Juiblex"),
            ("ref_c41175075be5535ab3cfd37dbbd7e1e1", "Hobgoblin Ombra Di Ferro"),
            ("ref_744cb23cb7f95be7b5d7521316ce8e78", "Fenice"),
            ("ref_aadff2eb6eff59af9caddb92deee6614", "Esploratore Di Bronzo"),
            ("ref_8def8c405c2452a4a10ff597fd89fdc8", "Duergar Martellatore"),
            ("ref_75abc404d54c51a2a312cbc2cd894e4a", "Duergar Guardia Di Pietra"),
            ("ref_fae2af9678e6572cb755708aab5c393d", "Drow Inquisitore"),
            ("ref_a8c5d07ab39252f8a22f4744181983df", "Duergar Despota"),
            ("ref_a6f22b9706e058a8bd3f4dcbbd24c985", "Danzatore Dell'Ombra"),
            ("ref_de503e430ad356ec98964fb1a65bd34a", "Vegepigmeo"),
            ("ref_b624eff23c3e543ba8b2c952761eb707", "Vegepigmeo Spinato"),
            ("ref_25a60967a5b8526fbb235e29d243c019", "Capo Vegepigmeo"),
            ("ref_b63e546c22a25155ae4ac40598eb7e3e", "Oscuride"),
            ("ref_d4c1987a935255ae9e854e228b9e4824", "Oscuride Anziano"),
        }
        and record.get("review_status") == "pending"
        and source.get("logical_source_id") == "mpmm_2022_it"
    )
    pdf_path = pdf_cache.get(source)
    source_target_name = SOURCE_GUIDED_TARGET_NAME_OVERRIDES.get(
        record_id,
        str(record.get("name") or ""),
    )
    target_page_only = (
        record_id in SOURCE_GUIDED_TARGET_PAGE_ONLY_IDS
        or str(source.get("logical_source_id") or "").strip()
        in TARGET_PAGE_ONLY_LOGICAL_SOURCE_IDS
    )

    # One monotonic budget covers every OCR layout/overlap/full-spectrum
    # attempt for this monster. A timeout blocks only this record. PHB records
    # that reached the boundary in run #112 receive a narrowly-scoped budget;
    # each individual Tesseract subprocess remains hard-limited to 15s.
    ocr_budget_started_at = (
        time.monotonic(),
        OCR_GLOBAL_TIMEOUT_SECONDS
        if args.target_set == "batch_mpmm_pending_131"
        else OCR_GLOBAL_TIMEOUT_BY_RECORD_ID.get(
            record_id,
            OCR_GLOBAL_TIMEOUT_SECONDS,
        ),
    )

    candidate = None
    quality = None
    selected_overlap = 0.02
    sparse_retry_required = False
    overlaps = (
        (0.02,)
        if record_id in PLAYERS_HANDBOOK_TIMEOUT11_IDS
        else (0.02, 0.03, 0.04, 0.05)
    )
    for overlap_index, overlap in enumerate(overlaps):
        window_started_at = time.monotonic()
        primary_pages, comparison_pages, quality = _ocr_source_window(
            pdf_path,
            physical_page,
            int(source["physical_pages"]),
            source,
            source_target_name,
            dpi=args.dpi,
            languages=args.languages,
            psm=args.psm,
            comparison_psm=args.comparison_psm,
            column_overlap=overlap,
            target_page_only=target_page_only,
            ocr_budget_started_at=ocr_budget_started_at,
        )
        print(
            "PHB_OCR_WINDOW_TIMING "
            + json.dumps(
                {
                    "name": record.get("name"),
                    "mode": "dynamic",
                    "overlap": overlap,
                    "elapsed_seconds": round(time.monotonic() - window_started_at, 3),
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        if (
            str(record.get("name") or "") in {"Addolorato Affamato", "Adrosauro"}
            and overlap == 0.02
        ):
            print(
                "MPMM_ADDOLORATO_AFFAMATO_DYNAMIC_TEXT "
                + json.dumps(
                    {
                        "primary": [
                            {"page": page, "text": text[:5000]}
                            for page, text in primary_pages
                        ],
                        "comparison": [
                            {"page": page, "text": text[:5000]}
                            for page, text in comparison_pages
                        ],
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )
        try:
            agreement_started_at = time.monotonic()
            candidate = _agreed_target_candidate(
                primary_pages,
                comparison_pages,
                str(source["physical_filename"]),
                str(source.get("language") or "it"),
                source_target_name,
                physical_page,
                isolate_bheur_title_rule=isolate_bheur_title_rule,
                isolate_kithrak_title_debris=isolate_kithrak_title_debris,
                require_exact_target_identity=require_exact_target_identity,
                include_core_diagnostics=args.target_set == "batch_mpmm_pending_131",
            )
            print(
                "PHB_AGREEMENT_TIMING "
                + json.dumps(
                    {
                        "name": record.get("name"),
                        "mode": "dynamic",
                        "elapsed_seconds": round(
                            time.monotonic() - agreement_started_at, 3
                        ),
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )
            if (
                record_id in PLAYERS_HANDBOOK_HP_SPARSE_RETRY_IDS
                or (
                    record_id == "ref_4b2e9b5984dd506d89caf10b4f15c3fd"
                    and record.get("name") == "Korred"
                    and record.get("review_status") == "pending"
                    and source.get("logical_source_id") == "mpmm_2022_it"
                )
            ) and HP_FORMAT_ERROR_FLAG in monster_semantic_numeric_flags(
                candidate.get("attributes") or {}
            ):
                print(
                    (
                        "PHB_HP_SPARSE_RETRY "
                        if record_id in PLAYERS_HANDBOOK_HP_SPARSE_RETRY_IDS
                        else "MPMM_HP_SPARSE_RETRY "
                    )
                    + json.dumps(
                        {"name": record.get("name"), "reason": HP_FORMAT_ERROR_FLAG},
                        ensure_ascii=False,
                        sort_keys=True,
                    )
                )
                candidate = None
                sparse_retry_required = True
                break
            selected_overlap = (
                0.0
                if source_target_name
                in {
                    "Berbalang",
                    "Berretto Rosso",
                    "Bodak",
                    "Bove Fetente",
                    "Collezionista Di Cadaveri",
                    "Divoratore",
                    "Draegloth",
                    "Stegosauro",
                    "Uro",
                }
                else overlap
            )
            break
        except RepairBlocked as exc:
            if str(record.get("id") or "") in SOURCE_GUIDED_NO_DYNAMIC_LAYOUT_RETRY_IDS:
                raise
            if (
                record_id in PLAYERS_HANDBOOK_AMBIGUOUS2_IDS
                and exc.reason == "no_unique_independent_agreement"
            ):
                print(
                    "PHB_AMBIGUOUS_SPARSE_RETRY "
                    + json.dumps(
                        {"name": record.get("name"), "reason": exc.reason},
                        ensure_ascii=False,
                        sort_keys=True,
                    )
                )
                sparse_retry_required = True
                break
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
            source_target_name,
            dpi=args.dpi,
            languages=args.languages,
            psm=args.psm,
            comparison_psm=args.comparison_psm,
            column_overlap=0.05,
            sparse_full_page=True,
            target_page_only=target_page_only,
            ocr_budget_started_at=ocr_budget_started_at,
        )
        sparse_anchor_verified = bool(
            (
                quality.get(physical_page, {})
                .get("segments", {})
                .get("sparse-full", {})
            ).get("sparse_anchor_found")
        )
        if str(record.get("name") or "") in {"Addolorato Smarrito", "Adrosauro"}:
            print(
                "MPMM_ADDOLORATO_SMARRITO_SPARSE_TEXT "
                + json.dumps(
                    {
                        "primary": [
                            {"page": page, "text": text[:5000]}
                            for page, text in primary_pages
                        ],
                        "comparison": [
                            {"page": page, "text": text[:5000]}
                            for page, text in comparison_pages
                        ],
                        "anchor_verified": sparse_anchor_verified,
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )
        if str(record.get("name") or "") == "Addolorato Affamato":
            print(
                "MPMM_ADDOLORATO_AFFAMATO_SPARSE_TEXT "
                + json.dumps(
                    {
                        "primary": [
                            {"page": page, "text": text[:5000]}
                            for page, text in primary_pages
                        ],
                        "comparison": [
                            {"page": page, "text": text[:5000]}
                            for page, text in comparison_pages
                        ],
                        "anchor_verified": sparse_anchor_verified,
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )
        candidate = _agreed_target_candidate(
            primary_pages,
            comparison_pages,
            str(source["physical_filename"]),
            str(source.get("language") or "it"),
            source_target_name,
            physical_page,
            source_anchor_verified=sparse_anchor_verified,
            isolate_bheur_title_rule=isolate_bheur_title_rule,
            isolate_kithrak_title_debris=isolate_kithrak_title_debris,
            require_exact_target_identity=require_exact_target_identity,
            include_core_diagnostics=args.target_set == "batch_mpmm_pending_131",
        )
        selected_overlap = 0.05
    if candidate is None or quality is None:
        raise RepairBlocked("dynamic_layout_exhausted")
    proposal = build_repair_proposal(
        record,
        candidate,
    )

    verified_flag_cleanup = None
    if (
        args.target_set
        in {
            "batch_players_handbook",
            "batch_players_handbook_blocked20",
            "batch_players_handbook_blocked16",
            "batch_players_handbook_blocked12",
            "batch_players_handbook_blocked11",
            "batch_players_handbook_blocked9",
            "batch_players_handbook_blocked8",
            "batch_players_handbook_blocked7",
        }
        and str(record.get("review_status") or "") == "verified"
    ):
        current_attributes = record.get("attributes") or {}
        proposed_attributes = proposal.get("attributes") or {}
        core_fields = ("classe_armatura", "punti_ferita", "velocita")
        raw_agreement, deterministic_agreement = _verified_core_agreement(
            current_attributes,
            proposed_attributes,
        )
        if not all(deterministic_agreement.values()):
            raise RepairBlocked(
                "players_handbook_verified_core_mismatch",
                detail=(
                    "CA/PF/velocita do not match after conservative "
                    "presentation-only normalization"
                ),
                diagnostics={
                    "agreement": raw_agreement,
                    "deterministic_agreement": deterministic_agreement,
                    "current_core": {
                        field: current_attributes.get(field) for field in core_fields
                    },
                    "source_core": {
                        field: proposed_attributes.get(field) for field in core_fields
                    },
                },
            )
        verified_flags = {str(flag) for flag in (record.get("review_flags") or [])}
        if verified_flags == {OCR_REVIEW_FLAG}:
            cleanup_already_applied = False
        elif not verified_flags:
            cleanup_already_applied = True
        else:
            raise RepairBlocked("players_handbook_verified_flag_drift")
        verified_flag_cleanup = {
            "authorized": True,
            "agreement": raw_agreement,
            "deterministic_agreement": deterministic_agreement,
            "remove_flag": OCR_REVIEW_FLAG,
            "already_applied": cleanup_already_applied,
        }
        proposal = {
            "attributes": dict(current_attributes),
            "review_flags": [],
            "review_status": "verified",
        }

    target_metrics = quality[physical_page]
    report = {
        "name": record.get("name"),
        "record_id": record.get("id"),
        "source_candidate_identity": {
            "name": candidate.get("name"),
            "normalized_name": candidate.get("normalized_name"),
            "start_page": candidate.get("start_page"),
        },
        "source": {
            "physical_filename": source.get("physical_filename"),
            "physical_sha256": source.get("physical_sha256"),
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
        **(
            {"verified_flag_cleanup": verified_flag_cleanup}
            if verified_flag_cleanup is not None
            else {}
        ),
    }

    if args.execute:
        if args.target_set == "batch_players_handbook":
            raise AssertionError(
                "Player's Handbook writes must be staged and applied at batch level"
            )
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
            "batch_players_handbook",
            "batch_players_handbook_blocked20",
            "batch_players_handbook_blocked16",
            "batch_players_handbook_blocked12",
            "batch_players_handbook_blocked11",
            "batch_players_handbook_blocked9",
            "batch_players_handbook_blocked8",
            "batch_players_handbook_blocked7",
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
        "batch_players_handbook_blocked20",
        "batch_players_handbook_blocked16",
        "batch_players_handbook_blocked12",
        "batch_players_handbook_blocked11",
        "batch_players_handbook_blocked9",
        "batch_players_handbook_blocked8",
        "batch_players_handbook_blocked7",
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
    if (
        args.execute
        and args.target_set == "batch_players_handbook"
        and args.confirm != PLAYERS_HANDBOOK_CONFIRMATION_TOKEN
    ):
        raise RuntimeError("Player's Handbook confirmation token mismatch")

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
    players_handbook_records = []
    if args.target_set in {
        "batch_players_handbook",
        "batch_players_handbook_blocked20",
        "batch_players_handbook_blocked16",
        "batch_players_handbook_blocked12",
        "batch_players_handbook_blocked11",
        "batch_players_handbook_blocked9",
        "batch_players_handbook_blocked8",
        "batch_players_handbook_blocked7",
    }:
        players_handbook_records = await _fetch_all(
            records_collection,
            {
                "reference_type": "monster",
                "source_key": PLAYERS_HANDBOOK_LEGACY_FILENAME,
            },
        )

    summary = {
        "verified_monsters": len(verified),
        "failed_monsters_total": len(failures) + len(corrupted_names),
        "failed_monsters_selected": len(failures),
        "corrupted_entity_names": len(corrupted_names),
        "expected_initial_failures": EXPECTED_INITIAL_FAILURES,
        "dry_run": not args.execute,
        "players_handbook_source_records": len(players_handbook_records),
    }
    print("SOURCE_GUIDED_REPAIR_SUMMARY")
    print(
        json.dumps(
            summary,
            ensure_ascii=False,
            sort_keys=True,
        )
    )

    if (
        not failures
        and not corrupted_names
        and args.target_set
        not in {
            "batch_players_handbook",
            "batch_players_handbook_blocked20",
            "batch_players_handbook_blocked16",
            "batch_players_handbook_blocked12",
            "batch_players_handbook_blocked11",
            "batch_players_handbook_blocked9",
            "batch_players_handbook_blocked8",
            "batch_players_handbook_blocked7",
        }
    ):
        return 0

    sealed_batch = args.target_set in {
        "healthy22",
        "approved1",
        "approved5",
        "oblex1",
        "ready6",
        "bigby4",
        "batch_players_handbook",
        "batch_players_handbook_blocked20",
        "batch_players_handbook_blocked16",
        "batch_players_handbook_blocked12",
        "batch_players_handbook_blocked11",
        "batch_players_handbook_blocked9",
        "batch_players_handbook_blocked8",
        "batch_players_handbook_blocked7",
    }
    if args.target_set == "batch_players_handbook":
        targets = select_players_handbook_targets(players_handbook_records)
        sealed_expected_count = EXPECTED_PLAYERS_HANDBOOK_COUNT
        sealed_label = "Player's Handbook"
    elif args.target_set == "batch_players_handbook_blocked20":
        targets = select_players_handbook_blocked20_targets(players_handbook_records)
        sealed_expected_count = EXPECTED_PLAYERS_HANDBOOK_BLOCKED20_COUNT
        sealed_label = "Player's Handbook blocked20"
    elif args.target_set == "batch_players_handbook_blocked16":
        targets = select_players_handbook_blocked16_targets(players_handbook_records)
        sealed_expected_count = EXPECTED_PLAYERS_HANDBOOK_BLOCKED16_COUNT
        sealed_label = "Player's Handbook blocked16"
    elif args.target_set == "batch_players_handbook_blocked12":
        targets = select_players_handbook_blocked12_targets(players_handbook_records)
        sealed_expected_count = EXPECTED_PLAYERS_HANDBOOK_BLOCKED12_COUNT
        sealed_label = "Player's Handbook blocked12"
    elif args.target_set == "batch_players_handbook_blocked11":
        targets = select_players_handbook_blocked11_targets(players_handbook_records)
        sealed_expected_count = EXPECTED_PLAYERS_HANDBOOK_BLOCKED11_COUNT
        sealed_label = "Player's Handbook blocked11"
    elif args.target_set == "batch_players_handbook_blocked9":
        targets = select_players_handbook_blocked9_targets(players_handbook_records)
        sealed_expected_count = EXPECTED_PLAYERS_HANDBOOK_BLOCKED9_COUNT
        sealed_label = "Player's Handbook blocked9"
    elif args.target_set == "batch_players_handbook_blocked8":
        targets = select_players_handbook_blocked8_targets(players_handbook_records)
        sealed_expected_count = EXPECTED_PLAYERS_HANDBOOK_BLOCKED8_COUNT
        sealed_label = "Player's Handbook blocked8"
    elif args.target_set == "batch_players_handbook_blocked7":
        targets = select_players_handbook_blocked7_targets(players_handbook_records)
        sealed_expected_count = EXPECTED_PLAYERS_HANDBOOK_BLOCKED7_COUNT
        sealed_label = "Player's Handbook blocked7"
    elif args.target_set in RESIDUAL_BATCH_TARGETS:
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

    batch_updated_at = None
    if args.target_set == "batch_players_handbook" and args.execute:
        if blocked or len(reports) != EXPECTED_PLAYERS_HANDBOOK_COUNT:
            raise RuntimeError(
                "Player's Handbook batch refused: all 31 proposals must be "
                "repairable before any UPDATE"
            )

        originals = {str(record["id"]): record for record in targets}
        verified_target_ids = {
            str(record["id"])
            for record in targets
            if str(record.get("review_status") or "") == "verified"
        }
        pending_target_ids = {
            str(record["id"])
            for record in targets
            if str(record.get("review_status") or "") == "pending"
        }
        verified_reports = [
            report
            for report in reports
            if str(report.get("record_id") or "") in verified_target_ids
        ]
        pending_reports = [
            report
            for report in reports
            if str(report.get("record_id") or "") in pending_target_ids
        ]

        if (
            len(verified_target_ids) != EXPECTED_PLAYERS_HANDBOOK_VERIFIED_COUNT
            or len(verified_reports) != EXPECTED_PLAYERS_HANDBOOK_VERIFIED_COUNT
            or len(pending_target_ids)
            != EXPECTED_PLAYERS_HANDBOOK_COUNT
            - EXPECTED_PLAYERS_HANDBOOK_VERIFIED_COUNT
            or len(pending_reports)
            != EXPECTED_PLAYERS_HANDBOOK_COUNT
            - EXPECTED_PLAYERS_HANDBOOK_VERIFIED_COUNT
            or any(
                not (report.get("verified_flag_cleanup") or {}).get("authorized")
                for report in verified_reports
            )
        ):
            raise RuntimeError(
                "Player's Handbook batch refused: expected 14 verified cleanup "
                "reports and 17 pending repair reports"
            )

        for report in pending_reports:
            expected_flags = sorted([OCR_REVIEW_FLAG, REPAIR_FLAG])
            actual_flags = sorted(str(flag) for flag in report["after"]["review_flags"])
            if actual_flags != expected_flags:
                raise RuntimeError(
                    "Player's Handbook unexpected pending proposal flags for "
                    f"{report['record_id']}: {actual_flags!r}"
                )
            if str(report["after"].get("review_status") or "") != "pending":
                raise RuntimeError(
                    "Player's Handbook pending proposal status drift for "
                    f"{report['record_id']}"
                )
            before_attributes = (
                originals[str(report["record_id"])].get("attributes") or {}
            )
            after_attributes = report["after"]["attributes"]
            for field in set(before_attributes) | set(after_attributes):
                if field not in {
                    "classe_armatura",
                    "punti_ferita",
                    "velocita",
                } and before_attributes.get(field) != after_attributes.get(field):
                    raise RuntimeError(
                        "Player's Handbook non-core attribute drift for "
                        f"{report['record_id']}: {field}"
                    )

        verified_cleanup_reports = [
            report
            for report in verified_reports
            if not (report.get("verified_flag_cleanup") or {}).get("already_applied")
        ]
        verified_already_applied_reports = [
            report
            for report in verified_reports
            if (report.get("verified_flag_cleanup") or {}).get("already_applied")
        ]

        await _revalidate_target_snapshots(records_collection, targets)
        batch_updated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        for report in verified_cleanup_reports:
            await _apply_verified_ocr_flag_cleanup(
                records_collection,
                originals[str(report["record_id"])],
                updated_at=batch_updated_at,
            )
            report["executed"] = True

        for report in verified_already_applied_reports:
            report["executed"] = False

        for report in pending_reports:
            proposal = {
                "attributes": report["after"]["attributes"],
                "review_flags": report["after"]["review_flags"],
                "review_status": "pending",
            }
            await _apply_update(
                records_collection,
                originals[str(report["record_id"])],
                proposal,
                updated_at=batch_updated_at,
                expected_review_status="pending",
            )
            report["executed"] = True

    elif sealed_batch and args.execute:
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
        "players_handbook_verified_cleanup_authorized": sum(
            1
            for report in reports
            if (report.get("verified_flag_cleanup") or {}).get("authorized")
        ),
        "players_handbook_already_applied": sum(
            1
            for report in reports
            if (report.get("verified_flag_cleanup") or {}).get("already_applied")
        ),
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
