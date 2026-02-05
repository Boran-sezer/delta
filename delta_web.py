import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64
import json

# --- CONFIGURATION ---
st.set_page_config(page_title="DELTA OS", page_icon="⚡")

# --- ÉTATS DE SESSION ---
if "messages" not in st.session_state: st.session_state.messages = []
if "sec_mode" not in st.session_state: st.session_state.sec_mode = "OFF"
if "essais" not in st.session_state: st.session_state.essais = 0

# --- LECTURE DE L'ENTRÉE (AVANT TOUTE LOGIQUE) ---
p = st.chat_input("Vos ordres, Monsieur ?")

if p:
    user_p = p.strip()
    low_p = user_p.lower()
    
    # 🚨 DÉTECTION PRIORITAIRE DU VERROU
    # Si on est déjà en mode sécurité OU si on demande une action sensible
    if st.session_state.sec_mode == "ON" or "réinitialisation complète" in low_p:
        
        # Cas 1 : On vient de déclencher l'ordre
        if st.session_state.sec_mode == "OFF":
            st.session_state.sec_mode = "ON"
            st.session_state.essais = 0
            rep = "🔒 **ZONE SÉCURISÉE.** Veuillez entrer le code d'accès pour confirmer la purge."
        
        # Cas 2 : On attend le code
        else:
            code_1 = "20082008"
            code_2 = "B2008a2020@"
            attendu = code_1 if st.session_state.essais < 3 else code_2
            
            if user_p == attendu:
                # ACTION (On ne charge Firebase qu'ici pour la purge)
                try:
                    if not firebase_admin._apps:
                        encoded = st.secrets["firebase_key"]["encoded_key"].strip()
                        cred = credentials.Certificate(json.loads(base64.b64decode(encoded).decode("utf-8")))
                        firebase_admin.initialize_app(cred)
                    db = firestore.client()
                    db.collection("memoire").document("profil_monsieur").set({"faits": [], "faits_verrouilles": []})
                    rep = "✅ **SYSTÈME PURGÉ.** Retour au mode normal."
                except:
                    rep = "⚠️ Erreur de connexion mémoire, mais l'ordre est validé."
                
                st.session_state.sec_mode = "OFF"
                st.session_state.essais = 0
            else:
                st.session_state.essais += 1
                if st.session_state.essais < 3:
                    rep = f"❌ **CODE INCORRECT.** Essai {st.session_state.essais}/3."
                elif st.session_state.essais == 3:
                    rep = "⚠️ **3 ÉCHECS.** Entrez le code de secours Pro Max (B2008a2020@)."
                else:
                    rep = "🚨 **ÉCHEC CRITIQUE.** Procédure annulée."
                    st.session_state.sec_mode = "OFF"
                    st.session_state.essais = 0

        # Affichage immédiat de la réponse de sécurité
        st.session_state.messages.append({"role": "user", "content": user_p})
        st.session_state.messages.append({"role": "assistant", "content": rep})
        st.rerun()

    # --- LOGIQUE NORMALE (IA) ---
    else:
        st.session_state.messages.append({"role": "user", "content": user_p})
        
        # Initialisation IA uniquement si pas en mode sécurité
        client = Groq(api_key="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")
        r = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": "Tu es DELTA."}] + st.session_state.messages
        )
        rep = r.choices[0].message.content
        st.session_state.messages.append({"role": "assistant", "content": rep})
        st.rerun()

# --- AFFICHAGE DU CHAT ---
for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])
