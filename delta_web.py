import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64
import json
import time
import re

# --- 1. CONFIGURATION ---
if not firebase_admin._apps:
    try:
        encoded = st.secrets["firebase_key"]["encoded_key"].strip()
        decoded_json = base64.b64decode(encoded).decode("utf-8")
        cred = credentials.Certificate(json.loads(decoded_json))
        firebase_admin.initialize_app(cred)
    except: pass

db = firestore.client()
doc_ref = db.collection("memoire").document("profil_monsieur")
client = Groq(api_key="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")

# --- 2. ÉTATS DE SESSION ---
if "messages" not in st.session_state: 
    st.session_state.messages = [{"role": "assistant", "content": "Système DELTA paré, Monsieur Sezer. ⚡"}]

# --- 3. INTERFACE & SIDEBAR ---
st.set_page_config(page_title="DELTA", layout="wide")
st.markdown("<h1 style='color:#00d4ff;'>⚡ DELTA</h1>", unsafe_allow_html=True)

res = doc_ref.get()
archives = res.to_dict().get("archives", {}) if res.exists else {}

with st.sidebar:
    st.title("📂 Archives de Monsieur Sezer")
    if archives:
        for partie, infos in archives.items():
            with st.expander(f"📁 {partie}"):
                for i in infos:
                    st.write(f"• {i}")
    else:
        st.info("Archives vides.")

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# --- 4. LOGIQUE DE COMMANDE (FORCE BRUTE) ---
if prompt := st.chat_input("Ordres pour vos archives..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Analyse simplifiée : On demande à l'IA de ne PAS réfléchir, juste de remplir un formulaire
    analyse_prompt = (
        f"Archives : {list(archives.keys())}. "
        f"Ordre : '{prompt}'. "
        "Réponds UNIQUEMENT par ce JSON : "
        "{'action': 'add' ou 'rename' ou 'delete', 'cat_cible': 'nom', 'valeur': 'texte', 'nouveau_nom': 'texte'} "
    )
    
    try:
        check = client.chat.completions.create(
            model="llama-3.1-8b-instant", 
            messages=[{"role": "system", "content": "Tu es un convertisseur JSON strict."}, {"role": "user", "content": analyse_prompt}],
            temperature=0
        )
        cmd_text = check.choices[0].message.content.strip()
        json_match = re.search(r'\{.*\}', cmd_text, re.DOTALL)
        
        if json_match:
            data = json.loads(json_match.group(0).replace("'", '"'))
            action = data.get('action')
            modif = False

            # --- LOGIQUE DE RENOMMAGE (PRIORITÉ) ---
            if "renomme" in prompt.lower() or action == 'rename':
                old_cat = data.get('cat_cible')
                new_cat = data.get('nouveau_nom')
                # On cherche si la catégorie existe
                for k in list(archives.keys()):
                    if old_cat.lower() in k.lower():
                        archives[new_cat] = archives.pop(k)
                        modif = True
                        break

            # --- LOGIQUE D'AJOUT (VOTRE VERSION ORIGINALE) ---
            elif action == 'add' or "ajoute" in prompt.lower():
                p = data.get('cat_cible', 'Général')
                if p not in archives: archives[p] = []
                archives[p].append(data.get('valeur'))
                modif = True

            # --- LOGIQUE DE SUPPRESSION ---
            elif action == 'delete' or "supprime" in prompt.lower():
                target = data.get('cat_cible', '').lower()
                for k in list(archives.keys()):
                    if target in k.lower():
                        del archives[k]
                        modif = True
                        break

            if modif:
                doc_ref.set({"archives": archives})
                st.toast("✅ Base mise à jour.")
                time.sleep(0.4)
                st.rerun()
    except Exception as e:
        pass

    # B. RÉPONSE DE DELTA
    with st.chat_message("assistant"):
        instr = f"Tu es DELTA, l'IA de Monsieur Sezer. Archives : {archives}. Ne dis jamais 'accès autorisé'."
        try:
            resp = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "system", "content": instr}] + st.session_state.messages
            )
            full_raw = resp.choices[0].message.content
        except:
            full_raw = "C'est fait, Monsieur Sezer. ⚡"
        
        st.markdown(full_raw)
        st.session_state.messages.append({"role": "assistant", "content": full_raw})
