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

# --- ÉTATS DE SESSION ---
if "messages" not in st.session_state: st.session_state.messages = []
if "unlocked" not in st.session_state: st.session_state.unlocked = False
if "security_mode" not in st.session_state: st.session_state.security_mode = None
if "attempts" not in st.session_state: st.session_state.attempts = 0
if "pending_data" not in st.session_state: st.session_state.pending_data = None

# --- CHARGEMENT DU PROFIL ---
res_profil = doc_profil.get()
data = res_profil.to_dict() if res_profil.exists else {}
faits_publics = data.get("faits", [])
faits_verrouilles = data.get("faits_verrouilles", [])

# --- SIDEBAR ---
with st.sidebar:
    st.title("🧠 Archives")
    for i, f in enumerate(faits_publics):
        col1, col2 = st.columns([4, 1])
        col1.info(f)
        if col2.button("🗑️", key=f"p_{i}"):
            faits_publics.pop(i)
            doc_profil.update({"faits": faits_publics})
            st.rerun()
    if st.session_state.unlocked:
        st.subheader("🔐 Scellées")
        for i, f in enumerate(faits_verrouilles):
            col1, col2 = st.columns([4, 1])
            col1.warning(f)
            if col2.button("🗑️", key=f"s_{i}"):
                faits_verrouilles.pop(i)
                doc_profil.update({"faits_verrouilles": faits_verrouilles})
                st.rerun()

# --- AFFICHAGE CHAT ---
for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# --- LOGIQUE DE TRAITEMENT ---
if p := st.chat_input("Vos ordres, Monsieur ?"):
    st.session_state.messages.append({"role": "user", "content": p})
    with st.chat_message("user"): st.markdown(p)

    rep = ""
    # --- PHASE DE VÉRIFICATION ---
    if st.session_state.security_mode:
        code_normal = "20082008"
        code_secours = "B2008a2020@"
        
        # Déterminer quel code est requis selon le nombre d'essais déjà faits
        if st.session_state.attempts < 3:
            if p == code_normal:
                # SUCCÈS CODE NORMAL
                valide = True
            else:
                valide = False
                st.session_state.attempts += 1
        else:
            # ON EST AU 4ème ESSAI OU PLUS : CODE SECOURS REQUIS
            if p == code_secours:
                valide = True
            else:
                valide = False
                st.session_state.attempts += 1

        if valide:
            # EXÉCUTION DE L'ACTION
            mode = st.session_state.security_mode
            info = st.session_state.pending_data
            if mode == "PURGE":
                doc_profil.set({"faits": [], "faits_verrouilles": []})
                rep = "✅ **ACCÈS MAÎTRE CONFIRMÉ.** La mémoire a été effacée."
            elif mode == "LOCK":
                faits_verrouilles.append(info)
                doc_profil.update({"faits_verrouilles": faits_verrouilles})
                rep = "✅ **SCELLAGE EFFECTUÉ.**"
            elif mode == "UNLOCK":
                st.session_state.unlocked = True
                rep = "✅ **COFFRE OUVERT.**"
            elif mode == "DELETE":
                t = info.lower()
                new_pub = [f for f in faits_publics if t not in f.lower()]
                new_priv = [f for f in faits_verrouilles if t not in f.lower()]
                doc_profil.set({"faits": new_pub, "faits_verrouilles": new_priv})
                rep = f"✅ **SUPPRESSION DE '{info}' RÉUSSIE.**"
            
            # Reset complet
            st.session_state.security_mode = None
            st.session_state.attempts = 0
        else:
            # ÉCHEC DE LA SAISIE
            if st.session_state.attempts < 3:
                rep = f"❌ **CODE INCORRECT.** Essai {st.session_state.attempts}/3. Veuillez réessayer."
            elif st.session_state.attempts == 3:
                rep = "⚠️ **DERNIER ESSAI ÉCHOUÉ.** Sécurité renforcée active. Veuillez entrer le CODE DE SECOURS (B2008a2020@)."
            else:
                rep = "🚨 **SÉCURITÉ MAXIMALE.** Échec critique. Procédure annulée."
                st.session_state.security_mode = None
                st.session_state.attempts = 0

    # --- PHASE DE DÉTECTION ---
    else:
        low_p = p.lower()
        if "réinitialisation complète" in low_p:
            st.session_state.security_mode = "PURGE"
            rep = "🔒 **CONFIRMATION REQUISE.** Entrez le code pour la purge totale."
        elif "verrouille" in low_p:
            st.session_state.security_mode = "LOCK"
            st.session_state.pending_data = p.replace("verrouille", "").strip()
            rep = "🔒 **CODE REQUIS.** Pour sceller cette information."
        elif "affiche les archives verrouillées" in low_p:
            st.session_state.security_mode = "UNLOCK"
            rep = "🔒 **AUTHENTIFICATION.** Pour ouvrir les archives scellées."
        elif "supprime précisément" in low_p:
            st.session_state.security_mode = "DELETE"
            st.session_state.pending_data = p.replace("supprime précisément", "").strip()
            rep = f"🔒 **SÉCURITÉ.** Code requis pour supprimer '{st.session_state.pending_data}'."
        else:
            # IA NORMALE
            with st.chat_message("assistant"):
                instr = {"role": "system", "content": f"Tu es DELTA, créé par Monsieur Boran."}
                r = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[instr] + st.session_state.messages)
                rep = r.choices[0].message.content

    with st.chat_message("assistant"):
        st.markdown(rep)
        st.session_state.messages.append({"role": "assistant", "content": rep})
