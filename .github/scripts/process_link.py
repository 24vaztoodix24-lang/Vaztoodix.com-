import os
import json
import re
import urllib.request
import urllib.error
from datetime import datetime, timezone

GROQ_API_KEY = os.environ["GROQ_API_KEY"]
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
        page_text = clean[:3500]
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
- Si une catégorie ou un jeu similaire existe déjà dans la liste ci-dessous, réutilise exactement le même nom :
  Catégories existantes : {existing_categories}
  Jeux/Projets existants : {existing_games}

Réponds UNIQUEMENT avec un objet JSON valide respectant exactement ce schéma :
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

models_to_try = ["openai/gpt-oss-120b", "openai/gpt-oss-20b"]
result = None
last_error = None

for model_name in models_to_try:
    payload = json.dumps({
        "model": model_name,
        "messages": [
            {"role": "system", "content": "Tu réponds uniquement avec un objet JSON valide en français."},
            {"role": "user", "content": prompt}
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.2
    }).encode("utf-8")

    api_req = urllib.request.Request(
        "https://api.groq.com/openai/v1/chat/completions",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "User-Agent": "VaztoodixBot/1.0"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(api_req, timeout=30) as api_resp:
            result = json.loads(api_resp.read().decode("utf-8"))
        break
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="ignore")
        last_error = f"Erreur API Groq sur {model_name} ({e.code} {e.reason}): {error_body}"
        print(last_error)

if result is None:
    raise RuntimeError(last_error or "Aucune réponse reçue de l'API Groq.")

raw_json_text = result["choices"][0]["message"]["content"].strip()
new_entry = json.loads(raw_json_text)

db["mods"] = [m for m in db["mods"] if m.get("publication", {}).get("lien") != target_url]
db["mods"].append(new_entry)

with open(MODS_FILE, "w", encoding="utf-8") as f:
    json.dump(db, f, ensure_ascii=False, indent=2)

print("Entrée ajoutée avec succès :", new_entry["categorie"], ">", new_entry["jeu"], ">", new_entry["publication"]["titre"])
