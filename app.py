import streamlit as st
import pandas as pd
import pdfplumber
import re
import math

# Configuration de l'interface
st.set_page_config(page_title="Hako-Toro : Optimisation", layout="wide")

st.title("🚚 Calculateur de Métrage (Calcul Gerbage Précis)")

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
        
        if st.button("🚀 LANCER LE CALCUL"):
            total_mm_brut = 0
            total_mm_optimise = 0
            details = []

            for pdf_file in uploaded_pdfs:
                with pdfplumber.open(pdf_file) as pdf:
                    texte = "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()])
                    lignes = texte.split('\n')

                    for ligne in lignes:
                        for _, row in df_articles.iterrows():
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
                                    
                                    # 1. Calcul Brut (Tout au sol)
                                    brut_ligne = l_art * qte
                                    total_mm_brut += brut_ligne
                                    
                                    # 2. Calcul Optimisé (Vrai calcul de gerbage)
                                    if h_art > 0 and (h_art * 2) <= h_camion:
                                        gerbable = "✅ Oui (x2)"
                                        # On divise la quantité par 2 et on arrondit au-dessus
                                        # Ex: 3 machines = 2 places au sol (une pile de 2 + une seule)
                                        nb_piles = math.ceil(qte / 2)
                                        opti_ligne = nb_piles * l_art
                                    else:
                                        gerbable = "❌ Non"
                                        opti_ligne = l_art * qte
                                    
                                    total_mm_optimise += opti_ligne
                                    
                                    details.append({
                                        "Document": pdf_file.name,
                                        "Référence": ref,
                                        "Qté": qte,
                                        "L (mm)": l_art,
                                        "H (mm)": h_art,
                                        "Gerbable": gerbable,
                                        "Métrage Sol (mm)": opti_ligne
                                    })
                                    break

            # --- AFFICHAGE DES RÉSULTATS ---
            st.divider()
            c1, c2 = st.columns(2)
            
            with c1:
                st.metric("Métrage TOTAL (Brut)", f"{total_mm_brut / 1000:.2f} m")
                st.caption("Si tout est posé au sol sans empiler.")
            
            with c2:
                gain = (total_mm_brut - total_mm_optimise) / 1000
                st.metric("Métrage RÉEL (Optimisé)", f"{total_mm_optimise / 1000:.2f} m", delta=f"-{gain:.2f}m gagnés")
                st.caption("Prend en compte l'empilage par paires.")

            st.subheader("Détail des articles détectés")
            st.dataframe(pd.DataFrame(details), use_container_width=True)
            
            m_final = total_mm_optimise / 1000
            if m_final > 8:
                st.warning(f"Prévoir une Semi-remorque (Besoin : {m_final:.1f}m)")
            elif m_final > 4:
                st.info(f"Un porteur de 8m suffit (Besoin : {m_final:.1f}m)")
            else:
                st.success(f"Un petit porteur suffit (Besoin : {m_final:.1f}m)")

    except Exception as e:
        st.error(f"Erreur technique : {e}")
