import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64
import json

# --- CONFIGURATION ---
st.set_page_config(page_title="DELTA OS", page_icon="⚡", layout="wide")

# --- INITIALISATION FIREBASE ---
if not firebase_admin._apps:
    try:
        encoded = st.secrets["firebase_key"]["encoded_key"].strip()
        decoded_json = base64.b64decode(encoded).decode("utf-8")
        creds_dict = json.loads(decoded_json)
        cred = credentials.Certificate(creds_dict)
        firebase_admin.initialize_app(cred)
    except Exception:
        st.error("⚠️ Connexion Mémoire interrompue.")

db = firestore.client()
doc_profil = db.collection("memoire").document("profil_monsieur")

# --- CONNEXION GROQ ---
client = Groq(api_key="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")

# --- CHARGEMENT DU PROFIL (MÉMOIRE LONGUE) ---
# On ne charge plus le chat_history ici pour qu'il s'efface à la fermeture
res_profil = doc_profil.get()
faits_connus = res_profil.to_dict().get("faits", []) if res_profil.exists else []

# --- INTERFACE ---
st.title("⚡ DELTA SYSTEM")

# Initialisation de l'historique local uniquement (s'efface à la fermeture)
if "messages" not in st.session_state:
    st.session_state.messages = []

# Sidebar pour voir ce que DELTA a jugé important
with st.sidebar:
    st.title("🧠 Archives")
    st.write("Informations extraites automatiquement :")
    for f in faits_connus:
        st.info(f"🔹 {f}")

# Affichage des messages
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# --- LOGIQUE DE RÉPONSE ---
if p := st.chat_input("Vos ordres, Monsieur ?"):
    # 1. Ajouter au chat local
    st.session_state.messages.append({"role": "user", "content": p})
    with st.chat_message("user"):
        st.markdown(p)

    # 2. Réponse de DELTA avec tri intelligent
    with st.chat_message("assistant"):
        contexte_faits = "Infos importantes sur Monsieur Boran : " + ", ".join(faits_connus)
        
        # Instructions pour le tri des infos
        instructions = {
            "role": "system", 
            "content": f"""Tu es DELTA, créé par Monsieur Boran. {contexte_faits}. 
            Tu es son majordome fidèle. 
            MISSION SPÉCIALE : Analyse chaque message de Monsieur. 
            Si tu détectes une information importante (goûts, noms, codes, habitudes), 
            réponds normalement MAIS commence ta réponse par le tag [MEMO: l'info à retenir] 
            pour que je puisse l'extraire."""
        }
        
        full_history = [instructions] + st.session_state.messages
        
        r = client.chat.completions.create(
            model="llama-3.3-70b-versatile", 
            messages=full_history
        )
        rep_brute = r.choices[0].message.content
        
        # Traitement du tag de mémoire
        if "[MEMO:" in rep_brute:
            # On extrait l'info entre [MEMO: et ]
            partie_memo = rep_brute.split("[MEMO:")[1].split("]")[0].strip()
            if partie_memo not in faits_connus:
                faits_connus.append(partie_memo)
                doc_profil.set({"faits": faits_connus})
            # On nettoie la réponse pour ne pas afficher le tag à Monsieur
            rep_finale = rep_brute.split("]")[1].strip() if "]" in rep_brute else rep_brute
        else:
            rep_finale = rep_brute

        st.markdown(rep_finale)
        st.session_state.messages.append({"role": "assistant", "content": rep_finale})
