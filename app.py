import streamlit as st
import pandas as pd
import pdfplumber
import re

# Configuration de l'interface
st.set_page_config(page_title="Hako-Toro : Optimisation", layout="wide")

st.title("🚚 Calculateur de Métrage (Optimisation Réelle)")

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
                                    
                                    # Calcul Brut (File indienne)
                                    brut_ligne = l_art * qte
                                    total_mm_brut += brut_ligne
                                    
                                    # Calcul Optimisé (Gerbage)
                                    # Si deux palettes tiennent en hauteur, on divise la longueur par 2
                                    if h_art > 0 and (h_art * 2) <= h_camion:
                                        opti_ligne = brut_ligne / 2
                                        gerbable = "✅ Oui (x2)"
                                    else:
                                        opti_ligne = brut_ligne
                                        gerbable = "❌ Non"
                                    
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
                st.caption("Si aucune palette n'est empilée.")
            
            with c2:
                st.status = st.metric("Métrage OPTIMISÉ", f"{total_mm_optimise / 1000:.2f} m", delta=f"-{(total_mm_brut - total_mm_optimise)/1000:.2f}m gagnés", delta_color="normal")
                st.caption("Prend en compte l'empilage des palettes basses.")

            st.subheader("Détail des articles détectés")
            st.dataframe(pd.DataFrame(details), use_container_width=True)
            
            # Conseil final
            m_final = total_mm_optimise / 1000
            if m_final > 8:
                st.warning(f"Prévoir une Semi-remorque (Besoin : {m_final:.1f}m)")
            elif m_final > 4:
                st.info(f"Un porteur de 8m devrait suffire (Besoin : {m_final:.1f}m)")
            else:
                st.success(f"Un petit porteur ou fourgon suffit (Besoin : {m_final:.1f}m)")

    except Exception as e:
        st.error(f"Erreur technique : {e}")
else:
    st.info("Veuillez charger l'Excel à gauche et les PDF au centre.")
