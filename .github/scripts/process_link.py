import os
import json
import re
import urllib.request
from datetime import datetime, timezone

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
ISSUE_BODY = os.environ.get("ISSUE_BODY", "").strip()
MODS_FILE = "data/mods.json"

url_match = re.search(r'https?://[^\s<>"\']+', ISSUE_BODY)
if not url_match:
    raise ValueError("Aucun lien valide trouvé dans l'Issue.")
target_url = url_match.group(0)

page_text = ""
try:
    req = urllib.request.Request(
        target_url,
        headers={"User-Agent": "Mozilla/5.0 (VaztoodixBot/1.0)"}
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        html = resp.read().decode("utf-8", errors="ignore")
        clean = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.I)
        clean = re.sub(r"<style[\s\S]*?</style>", " ", clean, flags=re.I)
        clean = re.sub(r"<[^>]+>", " ", clean)
        clean = re.sub(r"\s+", " ", clean).strip()
        page_text = clean[:12000]
except Exception as e:
    page_text = f"(Impossible de lire directement la page HTML : {e}. Analyse à partir de l'URL et de tes connaissances.)"

if os.path.exists(MODS_FILE):
    with open(MODS_FILE, "r", encoding="utf-8") as f:
        db = json.load(f)
else:
    db = {"mods": []}

existing_categories = sorted(list({m.get("categorie", "") for m in db["mods"] if m.get("categorie")}))
existing_games = sorted(list({m.get("jeu", "") for m in db["mods"] if m.get("jeu")}))
today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

prompt = f"""
Tu es l'assistant d'indexation automatique du site Vaztoodix RE Studio.
L'utilisateur t'envoie uniquement un lien. Tu dois analyser ce lien et générer UNE entrée JSON complète.

RÈGLE FONDAMENTALE :
- L'exemple "Switch > Jeux > Mario Kart 8 Deluxe" est UNIQUEMENT un exemple de structure logique.
- Tu dois déduire dynamiquement la vraie catégorie, sous-catégorie et le vrai jeu/projet à partir du lien fourni (ex: PC, Android, iOS, Switch, Outils, Émulation, Reverse Engineering, etc.).
- Si la catégorie ou le jeu n'existe pas encore dans la liste existante, CRÉE-LE librement avec un nom clair et propre.
- Si une catégorie ou un jeu similaire existe déjà dans la liste ci-dessous, réutilise exactement le même nom pour éviter les doublons :
  Catégories existantes : {existing_categories}
  Jeux/Projets existants : {existing_games}

Chaque entrée représente un mod, outil ou ressource composé de :
- "publication" : titre précis, lien exact, type (Mod, Outil, APK, Tutoriel, Ressource...), date du jour ({today}).
- "explication" : explication claire en français de ce que fait le mod/outil et comment il fonctionne/s'installe.
- "wiki" : fiche wiki synthétique en français (contexte du jeu ou de l'outil, compatibilité, versions, astuces/références).

Réponds UNIQUEMENT avec un objet JSON valide sans bloc markdown autour, respectant exactement ce schéma :
{{
  "id": "slug-unique-en-minuscules",
  "categorie": "Nom de la catégorie",
  "sous_categorie": "Nom de la sous-catégorie",
  "jeu": "Nom du jeu ou du logiciel concerné",
  "publication": {{
    "titre": "Titre du mod ou de la publication",
    "lien": "{target_url}",
    "type": "Mod",
    "date_ajout": "{today}"
  }},
  "explication": "Explication détaillée et claire en français",
  "wiki": "Informations wiki, compatibilité et contexte en français"
}}

URL à analyser : {target_url}
Contenu extrait de la page :
{page_text}
"""

api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
payload = json.dumps({
    "contents": [{"parts": [{"text": prompt}]}],
    "generationConfig": {"responseMimeType": "application/json"}
}).encode("utf-8")

api_req = urllib.request.Request(
    api_url,
    data=payload,
    headers={"Content-Type": "application/json"},
    method="POST"
)

with urllib.request.urlopen(api_req, timeout=30) as api_resp:
    result = json.loads(api_resp.read().decode("utf-8"))

raw_json_text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
new_entry = json.loads(raw_json_text)

db["mods"] = [m for m in db["mods"] if m.get("publication", {}).get("lien") != target_url]
db["mods"].append(new_entry)

with open(MODS_FILE, "w", encoding="utf-8") as f:
    json.dump(db, f, ensure_ascii=False, indent=2)

print("Entrée ajoutée :", new_entry["categorie"], ">", new_entry["jeu"], ">", new_entry["publication"]["titre"])
