import streamlit as st
import pandas as pd
import pdfplumber
import re

# Configuration de l'interface
st.set_page_config(page_title="Hako-Toro : Optimisation Chargement", layout="wide")

st.title("🚚 Calculateur de Métrage & Hauteur Camion")
st.markdown("Analyse automatique des bons de commande Hako.")

# --- BARRE LATÉRALE : CONFIGURATION ---
st.sidebar.header("1. Configuration")
# On accepte tous les types d'Excel pour éviter les blocages
uploaded_excel = st.sidebar.file_uploader("Charger la base Excel (Palettes)", type=None)

# Paramètre de hauteur du camion (standard 2600mm)
hauteur_camion = st.sidebar.number_input("Hauteur utile du camion (mm)", value=2600)

# --- ZONE PRINCIPALE : DOCUMENTS ---
st.subheader("2. Chargement des documents")
uploaded_pdfs = st.file_uploader("Glissez vos Bons de Commande (PDF) ici", type="pdf", accept_multiple_files=True)

if uploaded_excel and uploaded_pdfs:
    try:
        # Lecture de l'Excel
        df_articles = pd.read_excel(uploaded_excel, sheet_name='Palettes')
        st.sidebar.success("✅ Base articles connectée")
        
        if st.button("🚀 LANCER LE CALCUL ANALYTIQUE"):
            total_mm_sol = 0
            details = []
            alertes_hauteur = []

            for pdf_file in uploaded_pdfs:
                with pdfplumber.open(pdf_file) as pdf:
                    texte_pdf = "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()])
                    lignes = texte_pdf.split('\n')

                    for ligne in lignes:
                        for _, row in df_articles.iterrows():
                            # Nettoyage des références (gestion du "/" dans l'Excel)
                            refs = [r.strip() for r in str(row['Référence']).split('/')]
                            long_art = float(row['Longueur (mm)'])
                            haut_art = float(row.get('Hauteur (mm)', 0))
                            
                            for ref in refs:
                                if ref in ligne and len(ref) > 3:
                                    # Extraction de la quantité sur la ligne du PDF
                                    nombres = re.findall(r'\b\d+\b', ligne)
                                    qte = 1
                                    if len(nombres) >= 2:
                                        autres = [n for n in nombres if n != ref]
                                        if autres: qte = int(autres[0])
                                    
                                    # Calculs
                                    sous_total_long = long_art * qte
                                    total_mm_sol += sous_total_long
                                    
                                    # Analyse de gerbage (empilage)
                                    peut_gerber = "Non"
                                    if haut_art * 2 <= hauteur_camion:
                                        peut_gerber = "Oui (x2)"
                                    
                                    details.append({
                                        "Document": pdf_file.name,
                                        "Référence": ref,
                                        "Qté": qte,
                                        "Longueur (mm)": long_art,
                                        "Ha
