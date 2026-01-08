import streamlit as st
import pandas as pd
import pdfplumber
import re

# Configuration de l'interface
st.set_page_config(page_title="Hako-Toro : Optimisation", layout="wide")

st.title("🚚 Calculateur de Métrage & Hauteur Camion")

# --- CONFIGURATION ---
st.sidebar.header("1. Configuration")
uploaded_excel = st.sidebar.file_uploader("Charger la base Excel (Palettes)", type=None)
h_camion = st.sidebar.number_input("Hauteur utile du camion (mm)", value=2600)

# --- ZONE DOCUMENTS ---
st.subheader("2. Chargement des documents")
uploaded_pdfs = st.file_uploader("Glissez vos PDF ici", type="pdf", accept_multiple_files=True)

if uploaded_excel and uploaded_pdfs:
    try:
        df_articles = pd.read_excel(uploaded_excel, sheet_name='Palettes')
        st.sidebar.success("✅ Base articles connectée")
        
        if st.button("🚀 LANCER LE CALCUL ANALYTIQUE"):
            total_mm_sol = 0
            details = []
            alertes_hauteur = []

            for pdf_file in uploaded_pdfs:
                with pdfplumber.open(pdf_file) as pdf:
                    texte = "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()])
                    lignes = texte.split('\n')

                    for ligne in lignes:
                        for _, row in df_articles.iterrows():
                            # Nettoyage références
                            refs = [r.strip() for r in str(row['Référence']).split('/')]
                            l_art = float(row['Longueur (mm)'])
                            h_art = float(row.get('Hauteur (mm)', 0))
                            
                            for ref in refs:
                                if ref in ligne and len(ref) > 3:
                                    nombres = re.findall(r'\b\d+\b', ligne)
                                    qte = 1
                                    if len(nombres) >= 2:
                                        autres = [n for n in nombres if n != ref]
                                        if autres: qte = int(autres[0])
                                    
                                    s_total_l = l_art * qte
                                    total_mm_sol += s_total_l
                                    
                                    # Analyse gerbage
                                    peut_gerber = "Oui (x2)" if h_art * 2 <= h_camion else "Non"
                                    
                                    # On crée la ligne de résultat
                                    item = {
                                        "Document": pdf_file.name,
                                        "Référence": ref,
                                        "Qté": qte,
                                        "L (mm)": l_art,
                                        "H (mm)": h_art,
                                        "Gerbable": peut_gerber,
                                        "Total Sol (mm)": s_total_l
                                    }
                                    details.append(item)
                                    
                                    if h_art > h_camion:
                                        alertes_hauteur.append(f"⚠️ {ref} TROP HAUT ({h_art}mm)")
                                    break

            # --- RÉSULTATS ---
            st.divider()
            c1, c2, c3 = st.columns(3)
            c1.metric("Métrage au sol TOTAL", f"{total_mm_sol / 1000:.2f} m")
            c2.metric("Nb articles", len(details))
            c3.metric("Métrage optimisé (est.)", f"{(total_mm_sol / 1000) * 0.7:.2f} m")

            for msg in alertes_hauteur:
                st.error(msg)

            st.subheader("Détail du chargement")
            st.dataframe(pd.DataFrame(details), use_container_width=True)

    except Exception as e:
        st.error(f"Erreur : {e}")
else:
    st.info("En attente de l'Excel et des PDF...")
