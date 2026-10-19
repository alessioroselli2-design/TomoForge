"""Original Italian Monster Manual source census, physical pages 305–353.

A direct page-by-page visual inventory of independently boxed statblocks,
including Appendix A creatures and Appendix B NPCs, not just main bestiary.
Licensed page scans and passages are deliberately NOT committed.
Names and source locations alone cannot justify a verified database record:
individual CA/HP/six stats/actions and collision checks are still required.

Source PDF physically inspected: 353 pages, SHA256 authority matched.
"""
from __future__ import annotations
from copy import deepcopy
import json

SOURCE_ID = "mm_2014_it"
FILENAME = "847921086-Manuale-Dei-Mostri-5e.pdf"
SHA256 = "b33eb72e5eb78fe3e3dcbde5315f5b9afbe42e4a457a518cc93f7766979a381c"
PAGES = 353
START_PAGE = 305
END_PAGE = 353
COMPLETE_STATISTICS_VERIFIED = False
REVIEW_STATUS = "source_page_identity_only_pending_full_fields_and_cross_source_match"
WRITES = 0
_PAGE_NAMES = json.loads(r'''{"305":["Yeti"],"306":["Yeti Abominevole"],"307":[],"308":["Yuan-Ti Abominio"],"309":["Yuan-Ti Nefasto"],"310":["Yuan-Ti Sanguepuro"],"311":[],"312":[],"313":["Arcanaloth","Mezzoloth"],"314":["Nycaloth","Ultroloth"],"315":[],"316":["Zombi","Zombi Ogre","Zombi Beholder"],"317":["Albero Risvegliato","Alce","Alce Gigante","Aquila"],"318":["Aquila Gigante","Avvoltoio","Avvoltoio Gigante","Babbuino"],"319":["Beccoaguzzo","Cammello","Cane della Morte"],"320":["Cane Intermittente","Capra","Capra Gigante","Cavallo da Galoppo"],"321":["Cavallo da Guerra","Cavallo da Tiro","Cavalluccio Marino","Cavalluccio Marino Gigante"],"322":["Cespuglio Risvegliato","Cinghiale","Cinghiale Gigante","Coccodrillo"],"323":["Coccodrillo Gigante","Corvo","Daino","Elefante"],"324":["Faina","Faina Gigante","Falco","Falco di Sangue","Gatto"],"325":["Gorilla","Granchio","Granchio Gigante","Gufo","Gufo Gigante"],"326":["Iena","Iena Gigante","Leone"],"327":["Lucertola","Lucertola Gigante","Lupo","Lupo Feroce"],"328":["Lupo Invernale","Mammut","Mastino"],"329":["Millepiedi Gigante","Mulo","Orca Assassina","Orso Bruno"],"330":["Orso Nero","Orso Polare","Pantera","Piovra"],"331":["Piovra Gigante","Pipistrello","Pipistrello Gigante","Pony"],"332":["Quipper","Ragno","Ragno Gigante"],"333":["Ragno Lupo Gigante","Ragno-Fase"],"334":["Rana","Rana Gigante","Rinoceronte","Rospo Gigante"],"335":["Scarabeo di Fuoco Gigante","Sciacallo","Sciame di Corvi","Sciame di Insetti"],"336":["Sciame di Pipistrelli","Sciame di Quipper","Sciame di Serpenti Velenosi"],"337":["Sciame di Topi","Scorpione","Scorpione Gigante","Serpente Stritolatore"],"338":["Serpente Stritolatore Gigante","Serpente Velenoso","Serpente Velenoso Gigante","Serpente Volante","Squalo Cacciatore"],"339":["Squalo Gigante","Squalo Tropicale","Tasso","Tasso Gigante"],"340":["Tigre","Tigre dai Denti a Sciabola","Topo","Topo Gigante"],"341":["Vespa Gigante","Worg"],"342":["Accolito","Arcimago"],"343":["Assassino","Bandito"],"344":["Berserker","Capo dei Banditi","Cavaliere"],"345":["Combattente Tribale","Cultista"],"346":["Cultista Fanatico","Druido"],"347":["Esploratore","Gladiatore"],"348":["Guardia","Mago","Malvivente"],"349":["Nobile","Popolano"],"350":["Sacerdote","Spia","Veterano"],"351":[],"352":[],"353":[]}''')
_PAGE_NAMES = {int(page): tuple(names) for page, names in _PAGE_NAMES.items()}
SOURCE_PAGE_NAMES = deepcopy(_PAGE_NAMES)


def inventory(catalog: dict) -> dict[int, tuple[str, ...]]:
    expected = {
        "logical_source_id": SOURCE_ID,
        "physical_filename": FILENAME,
        "physical_sha256": SHA256,
        "physical_pages": PAGES,
        "source_status": "active",
        "source_role": "authority",
        "authority_class": "licensed_translation",
        "text_mode": "vision_required",
    }
    if not isinstance(catalog, dict) or any(catalog.get(k) != v for k, v in expected.items()):
        raise ValueError("original_source_mismatch")
    if SOURCE_PAGE_NAMES != _PAGE_NAMES:
        raise ValueError("census_modified")
    if sorted(SOURCE_PAGE_NAMES) != list(range(START_PAGE, END_PAGE + 1)):
        raise ValueError("source_page_gap")
    names = [name for values in SOURCE_PAGE_NAMES.values() for name in values]
    if len(names) != len(set(names)):
        raise ValueError("duplicate_source_statblock")
    return deepcopy(SOURCE_PAGE_NAMES)
