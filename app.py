import streamlit as st
import pandas as pd
import pdfplumber
import re

# Configuration de la page
st.set_page_config(page_title="Hako-Toro : Métrage Camion", layout="centered")

st.title("🚚 Calculateur de Métrage Camion")
st.markdown("Calculez instantanément l'encombrement de vos commandes.")

# --- SECTION 1 : BASE DE DONNÉES ---
st.sidebar.header("Configuration")
uploaded_excel = st.sidebar.file_uploader("1. Charger la base Excel (Palettes)", type=None)

# --- SECTION 2 : DOCUMENTS PDF ---
uploaded_pdfs = st.file_uploader("2. Glissez vos Bons de Commande (PDF) ici", type="pdf", accept_multiple_files=True)

if uploaded_excel and uploaded_pdfs:
    try:
        # Lecture de l'Excel (onglet Palettes)
        df_articles = pd.read_excel(uploaded_excel, sheet_name='Palettes')
        st.sidebar.success("✅ Base articles connectée")
        
        if st.button("🚀 LANCER LE CALCUL"):
            total_mm = 0
            results = []

            for pdf_file in uploaded_pdfs:
                with pdfplumber.open(pdf_file) as pdf:
                    texte_pdf = "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()])
                    lignes = texte_pdf.split('\n')

                    for ligne in lignes:
                        for _, row in df_articles.iterrows():
                            refs = [r.strip() for r in str(row['Référence']).split('/')]
                            longueur = float(row['Longueur (mm)'])
                            
                            for ref in refs:
                                if ref in ligne:
                                    # Extraction de la quantité
                                    nombres = re.findall(r'\b\d+\b', ligne)
                                    qte = 1
                                    if len(nombres) >= 2:
                                        autres = [n for n in nombres if n != ref]
                                        if autres: qte = int(autres[0])
                                    
                                    calcul = longueur * qte
                                    total_mm += calcul
                                    results.append({"Fichier": pdf_file.name, "Réf": ref, "Qté": qte, "Longueur": f"{longueur}mm", "Sous-total": f"{calcul}mm"})
                                    break
            
            # --- AFFICHAGE DES RÉSULTATS ---
            st.divider()
            st.subheader(f"Métrage Total : {total_mm / 1000:.2f} mètres")
            
            # Affichage du tableau de détail
            if results:
                st.table(pd.DataFrame(results))
                
            # Conseil camion
            metrage = total_mm / 1000
            if metrage > 8: st.warning("🚛 Type de camion suggéré : Semi-remorque (13.6m)")
            elif metrage > 4: st.info("🚚 Type de camion suggéré : Porteur (7-8m)")
            else: st.success("🚐 Type de camion suggéré : Petit Porteur")

    except Exception as e:
        st.error(f"Erreur lors de la lecture de l'Excel : {e}")
else:
    st.info("Veuillez charger le fichier Excel dans la barre latérale et au moins un PDF pour commencer.")
