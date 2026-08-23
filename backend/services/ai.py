import json

TYPE_LABELS = {
    "spell": "Magia/Incantesimo", "class": "Classe", "race": "Razza", "weapon": "Arma",
    "armor": "Armatura/Scudo", "item": "Oggetto/Equipaggiamento",
    "feat": "Talento", "feature": "Privilegio di classe", "subclass": "Sottoclasse",
    "monster": "Mostro/Nemico", "character": "Personaggio", "custom": "Tipo personalizzato",
}
TYPE_SCHEMAS = {
    "spell": '"attributes": {"livello": "", "scuola": "", "azione": "", "tempo_lancio": "", "gittata": "", "area": "", "componenti": "", "durata": "", "concentrazione": "", "danno": "", "effetto": ""}',
    "class": '"attributes": {"dado_vita": "", "abilita_primaria": "", "tiri_salvezza": "", "competenze": "", "caratteristiche": []}',
    "subclass": '"attributes": {"dado_vita": "", "abilita_primaria": "", "tiri_salvezza": "", "competenze": "", "caratteristiche": []}',
    "feature": '"attributes": {"livello": "", "benefici": []}',
    "race": '"attributes": {"bonus_caratteristiche": "", "velocita": "", "taglia": "", "linguaggi": "", "tratti": []}',
    "weapon": '"attributes": {"danno": "", "tipo_danno": "", "proprieta": "", "peso": "", "costo": "", "categoria": ""}',
    "armor": '"attributes": {"classe_armatura": "", "forza_minima": "", "svantaggio_furtivita": "", "peso": "", "costo": "", "categoria": ""}',
    "item": '"attributes": {"categoria": "", "costo": "", "peso": "", "proprieta": "", "rarita": "", "sintonia": ""}',
    "feat": '"attributes": {"prerequisito": "", "benefici": []}',
    "monster": '"attributes": {"classe_armatura": "", "punti_ferita": "", "velocita": "", "for": "", "des": "", "cos": "", "int": "", "sag": "", "car": "", "azioni": [{"nome": "", "descrizione": ""}]}',
    "character": '"attributes": {"classe": "", "razza": "", "livello": "", "for": "", "des": "", "cos": "", "int": "", "sag": "", "car": "", "slot_incantesimi": []}',
    "custom": '"attributes": {}',
}
LANGUAGES = {"it": "Italiano", "en": "English", "es": "Spanish", "de": "German"}


def parse_ai_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`").removeprefix("json").strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("OpenAI did not return JSON")
    return json.loads(text[start:end + 1])
