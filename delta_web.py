import streamlit as st

st.title("⚡ TEST SÉCURITÉ DELTA")

if "step" not in st.session_state: st.session_state.step = "NORMAL"

# Affichage de l'état actuel pour comprendre ce qui se passe
st.sidebar.write(f"État actuel : {st.session_state.step}")

p = st.chat_input("Dites 'test' pour bloquer ou entrez le code '20082008'")

if p:
    with st.chat_message("user"): st.markdown(p)
    
    with st.chat_message("assistant"):
        # ÉTAPE 1 : DÉTECTION DU MOT "test"
        if p.lower() == "test":
            st.session_state.step = "VERROU"
            st.warning("🔒 SYSTÈME VERROUILLÉ. Entrez le code.")
        
        # ÉTAPE 2 : VÉRIFICATION DU CODE
        elif st.session_state.step == "VERROU":
            if p == "20082008":
                st.session_state.step = "NORMAL"
                st.success("✅ CODE CORRECT. Système déverrouillé.")
            else:
                st.error("❌ MAUVAIS CODE. Réessayez.")
        
        # ÉTAPE 3 : RÉPONSE NORMALE
        else:
            st.write("Je vous écoute, Monsieur. Dites 'test' pour voir si je me verrouille.")
