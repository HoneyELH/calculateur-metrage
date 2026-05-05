import streamlit as st
import pandas as pd
import pdfplumber
import re
import math

# ─────────────────────────────────────────
# CONFIG CAMION (depuis Excel "Paramètres")
# ─────────────────────────────────────────
L_UTILE  = 13600   # mm longueur
LARG_UTILE = 2460  # mm largeur
H_UTILE  = 2700    # mm hauteur
POIDS_MAX = 24000  # kg
JEU_SEQ  = 20      # mm entre rangées

# ─────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────
st.set_page_config(page_title="Chargement Camion", layout="wide", page_icon="🚛")

st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=DM+Sans:wght@300;400;600;700&display=swap');

  html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
  }
  .stApp {
    background: #F2F0EB;
  }
  .block-container {
    padding-top: 2rem !important;
    max-width: 1400px;
  }

  /* ── HEADER ── */
  .header {
    display: flex;
    align-items: baseline;
    gap: 14px;
    margin-bottom: 32px;
    border-bottom: 2px solid #1A1A1A;
    padding-bottom: 16px;
  }
  .header h1 {
    font-size: 2.2rem;
    font-weight: 700;
    color: #1A1A1A;
    margin: 0;
    letter-spacing: -1px;
  }
  .header span {
    font-family: 'DM Mono', monospace;
    font-size: 0.8rem;
    color: #888;
    letter-spacing: 2px;
    text-transform: uppercase;
  }

  /* ── CARDS ── */
  .kpi-row {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 14px;
    margin-bottom: 28px;
  }
  .kpi {
    background: #1A1A1A;
    color: #F2F0EB;
    border-radius: 12px;
    padding: 20px 22px;
  }
  .kpi .val {
    font-family: 'DM Mono', monospace;
    font-size: 2.4rem;
    font-weight: 500;
    line-height: 1;
    margin-bottom: 6px;
  }
  .kpi .lbl {
    font-size: 0.78rem;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    opacity: 0.6;
  }
  .kpi.warn  { background: #D94F2B; }
  .kpi.ok    { background: #2A7A4B; }

  /* ── RANGÉE CARDS ── */
  .rangee-card {
    background: #fff;
    border-radius: 10px;
    border: 1px solid #E0DDD7;
    padding: 14px 18px;
    margin-bottom: 8px;
    display: flex;
    align-items: stretch;
    gap: 0;
  }
  .rangee-num {
    font-family: 'DM Mono', monospace;
    font-size: 0.72rem;
    color: #aaa;
    min-width: 54px;
    padding-top: 2px;
  }
  .rangee-depth {
    font-family: 'DM Mono', monospace;
    font-size: 0.8rem;
    background: #F2F0EB;
    border-radius: 6px;
    padding: 2px 8px;
    margin-right: 14px;
    align-self: center;
    color: #555;
    min-width: 80px;
    text-align: center;
  }
  .slot {
    flex: 1;
    padding: 6px 12px;
    border-radius: 7px;
  }
  .slot-g { background: #EAF0FF; margin-right: 6px; }
  .slot-d { background: #FFF4EA; }
  .slot-vide { background: #F8F7F5; opacity: 0.6; }
  .slot .refs {
    font-family: 'DM Mono', monospace;
    font-size: 0.82rem;
    font-weight: 500;
    color: #1A1A1A;
  }
  .slot .meta {
    font-size: 0.72rem;
    color: #888;
    margin-top: 2px;
  }
  .camion-header {
    background: #1A1A1A;
    color: #F2F0EB;
    border-radius: 10px;
    padding: 10px 18px;
    font-weight: 600;
    font-size: 0.95rem;
    letter-spacing: 0.5px;
    margin: 20px 0 8px 0;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  .camion-header .mono {
    font-family: 'DM Mono', monospace;
    font-size: 0.8rem;
    opacity: 0.65;
  }

  /* ── UPLOAD ZONE ── */
  .upload-label {
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    color: #888;
    margin-bottom: 6px;
    font-weight: 600;
  }
  .section-title {
    font-size: 1.1rem;
    font-weight: 700;
    color: #1A1A1A;
    margin: 28px 0 12px;
    letter-spacing: -0.3px;
  }

  /* hide streamlit chrome */
  #MainMenu, footer, header { visibility: hidden; }
  .stFileUploader label { display: none; }

  /* btn */
  div[data-testid="stButton"] > button {
    background: #1A1A1A !important;
    color: #F2F0EB !important;
    border: none !important;
    border-radius: 8px !important;
    padding: 10px 32px !important;
    font-size: 1rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.3px !important;
    font-family: 'DM Sans', sans-serif !important;
    cursor: pointer !important;
  }
  div[data-testid="stButton"] > button:hover {
    background: #333 !important;
  }

  /* alerte */
  .alerte {
    background: #FFF3CD;
    border-left: 4px solid #D4A017;
    border-radius: 8px;
    padding: 12px 16px;
    font-size: 0.88rem;
    color: #6B4C00;
    margin-bottom: 10px;
  }
  .erreur {
    background: #FDECEA;
    border-left: 4px solid #D94F2B;
    border-radius: 8px;
    padding: 12px 16px;
    font-size: 0.88rem;
    color: #7A1E0E;
    margin-bottom: 10px;
  }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────
st.markdown("""
<div class="header">
  <h1>🚛 Chargement Camion</h1>
  <span>Optimisation de chargement · Hako France</span>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────
# UPLOAD
# ─────────────────────────────────────────
col_e, col_p, col_btn = st.columns([2, 3, 1])

with col_e:
    st.markdown("<div class='upload-label'>📊 Base articles (Excel)</div>", unsafe_allow_html=True)
    uploaded_excel = st.file_uploader("excel", type=["xlsx"], key="excel", label_visibility="collapsed")

with col_p:
    st.markdown("<div class='upload-label'>📄 Bons de préparation (PDF — plusieurs)</div>", unsafe_allow_html=True)
    uploaded_pdfs = st.file_uploader("pdfs", type=["pdf"], accept_multiple_files=True, key="pdfs", label_visibility="collapsed")

with col_btn:
    st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
    run = st.button("Calculer →", use_container_width=True)


# ─────────────────────────────────────────
# FONCTIONS MÉTIER
# ─────────────────────────────────────────

def construire_base_articles(df: pd.DataFrame) -> pd.DataFrame:
    """
    Explose les références groupées (ex: '74677 / 74679 / 74683')
    en une ligne par référence individuelle.
    """
    lignes = []
    for _, row in df.iterrows():
        refs = [r.strip() for r in str(row["Référence"]).split("/")]
        for r in refs:
            if not r:
                continue
            lignes.append({
                "Ref":         r,
                "Description": str(row["Description"]),
                "L_mm":        float(row["Longueur (mm)"]),
                "l_mm":        float(row["Largeur (mm)"]),
                "H_mm":        float(row["Hauteur (mm)"]),
                "Poids_kg":    float(row["Poids unitaire (kg)"]),
                "Empilable":   str(row["Empilable (Oui/Non)"]).strip().lower().startswith("o"),
            })
    return pd.DataFrame(lignes)


def extraire_commandes(df_refs: pd.DataFrame, pdfs) -> pd.DataFrame:
    """
    Parcourt les PDFs et extrait les quantités par référence.
    Stratégie robuste : cherche la ref en mot entier dans chaque ligne,
    prend le dernier entier de la ligne comme quantité.
    """
    commandes: dict[str, int] = {}
    alertes = []

    all_refs = set(df_refs["Ref"].tolist())

    for pdf_file in pdfs:
        with pdfplumber.open(pdf_file) as pdf:
            lignes_pdf = []
            for page in pdf.pages:
                txt = page.extract_text()
                if txt:
                    lignes_pdf.extend(txt.split("\n"))

        for ligne in lignes_pdf:
            # cherche toutes les refs connues dans la ligne
            for ref in all_refs:
                # mot entier, insensible aux espaces collés
                pattern = r'(?<!\w)' + re.escape(ref) + r'(?!\w)'
                if re.search(pattern, ligne):
                    nums = re.findall(r'\b\d+\b', ligne)
                    # on ignore les grands nombres (ex: N° commande)
                    petits = [int(n) for n in nums if int(n) <= 999]
                    if petits:
                        qte = petits[-1]
                        commandes[ref] = commandes.get(ref, 0) + qte
                    else:
                        alertes.append(f"Ref {ref} trouvée dans « {ligne[:60]}… » mais pas de quantité lisible")
                    break  # une ref par ligne

    if alertes:
        for a in alertes:
            st.markdown(f"<div class='alerte'>⚠️ {a}</div>", unsafe_allow_html=True)

    rows = [{"Ref": r, "Qte": q} for r, q in commandes.items()]
    return pd.DataFrame(rows) if rows else pd.DataFrame(columns=["Ref", "Qte"])


def construire_piles(df_full: pd.DataFrame) -> list[dict]:
    """
    Pour chaque article commandé, crée des piles physiques.
    - Non empilable ou fer → 1 pile par unité
    - Empilable → empile jusqu'à H_UTILE
    """
    piles = []
    pile_id = 0

    for _, art in df_full.iterrows():
        ref    = art["Ref"]
        qte    = int(art["Qte"])
        L, l, H = art["L_mm"], art["l_mm"], art["H_mm"]
        empilable = art["Empilable"]
        desc   = art["Description"]

        if not empilable:
            for _ in range(qte):
                pile_id += 1
                piles.append({
                    "id": pile_id, "refs": [ref], "desc": desc,
                    "L": L, "l": l, "H_totale": H, "H_unitaire": H,
                    "nb_niveaux": 1, "empilable": False
                })
        else:
            max_niveaux = max(1, int(H_UTILE // H))
            reste = qte
            while reste > 0:
                nb = min(reste, max_niveaux)
                pile_id += 1
                piles.append({
                    "id": pile_id, "refs": [ref] * nb, "desc": desc,
                    "L": L, "l": l, "H_totale": H * nb, "H_unitaire": H,
                    "nb_niveaux": nb, "empilable": True
                })
                reste -= nb

    return piles


def calc_metrage_surface(piles: list[dict]) -> float:
    """Métrage estimé = surface au sol totale / largeur utile."""
    surf = sum(p["L"] * p["l"] for p in piles)
    return surf / LARG_UTILE / 1000  # en mètres


def optimiser_rangees(piles: list[dict]) -> list[dict]:
    """
    Algorithme glouton :
    Trie par largeur décroissante, essaie de coupler chaque palette
    avec la plus grande qui rentre à côté (l_G + l_D ≤ LARG_UTILE).
    Profondeur de la rangée = max(L_G, L_D).
    """
    # Orientation : on place la palette dans le sens où la longueur va en profondeur
    # et la largeur occupe la laize. On choisit l'orientation qui minimise la largeur.
    def orient(p):
        # retourne (profondeur, largeur) dans l'orientation optimale
        if p["L"] <= p["l"]:
            return p["l"], p["L"]   # L devient laize
        return p["L"], p["l"]

    restantes = list(piles)
    # trier par largeur utile décroissante (orientation choisie)
    restantes.sort(key=lambda p: orient(p)[1], reverse=True)

    rangees = []
    while restantes:
        p_g = restantes.pop(0)
        prof_g, larg_g = orient(p_g)

        meilleureIdx = None
        for i, p2 in enumerate(restantes):
            prof_d, larg_d = orient(p2)
            if larg_g + larg_d <= LARG_UTILE:
                meilleureIdx = i
                break

        if meilleureIdx is not None:
            p_d = restantes.pop(meilleureIdx)
            prof_d, larg_d = orient(p_d)
            rangees.append({
                "gauche": (p_g, prof_g, larg_g),
                "droite": (p_d, prof_d, larg_d),
                "profondeur": max(prof_g, prof_d),
                "largeur_totale": larg_g + larg_d,
            })
        else:
            rangees.append({
                "gauche": (p_g, prof_g, larg_g),
                "droite": None,
                "profondeur": prof_g,
                "largeur_totale": larg_g,
            })

    return rangees


def repartir_camions(rangees: list[dict]) -> list[dict]:
    """
    Répartit les rangées entre camions en respectant L_UTILE.
    """
    camions = []
    camion_actuel = {"num": 1, "rangees": [], "longueur": 0}

    for r in rangees:
        prof = r["profondeur"] + JEU_SEQ

        if camion_actuel["longueur"] + prof > L_UTILE and camion_actuel["rangees"]:
            camions.append(camion_actuel)
            camion_actuel = {"num": camion_actuel["num"] + 1, "rangees": [], "longueur": 0}

        camion_actuel["rangees"].append(r)
        camion_actuel["longueur"] += prof

    if camion_actuel["rangees"]:
        camions.append(camion_actuel)

    return camions


def refs_display(pile) -> str:
    unique = list(dict.fromkeys(pile["refs"]))
    return " · ".join(unique)


# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────

if run:
    if not uploaded_excel:
        st.markdown("<div class='erreur'>❌ Veuillez importer la base articles Excel.</div>", unsafe_allow_html=True)
        st.stop()
    if not uploaded_pdfs:
        st.markdown("<div class='erreur'>❌ Veuillez importer au moins un bon de préparation PDF.</div>", unsafe_allow_html=True)
        st.stop()

    with st.spinner("Analyse en cours…"):
        try:
            df_palette = pd.read_excel(uploaded_excel, sheet_name="Palettes")
        except Exception as e:
            st.markdown(f"<div class='erreur'>❌ Erreur lecture Excel : {e}</div>", unsafe_allow_html=True)
            st.stop()

        df_refs  = construire_base_articles(df_palette)
        df_cmd   = extraire_commandes(df_refs, uploaded_pdfs)

        if df_cmd.empty:
            st.markdown("<div class='erreur'>❌ Aucune référence reconnue dans les PDFs. Vérifiez que vos références Excel correspondent aux PDFs.</div>", unsafe_allow_html=True)
            st.stop()

        df_full  = df_cmd.merge(df_refs, on="Ref", how="left")
        manquant = df_full[df_full["L_mm"].isna()]
        if not manquant.empty:
            st.markdown(f"<div class='alerte'>⚠️ Références inconnues dans la base : {', '.join(manquant['Ref'].tolist())}. Ajoutez-les dans l'Excel.</div>", unsafe_allow_html=True)
            df_full = df_full.dropna(subset=["L_mm"])

        piles   = construire_piles(df_full)
        rangees = optimiser_rangees(piles)
        camions = repartir_camions(rangees)

        # KPI
        total_piles   = len(piles)
        total_rangees = len(rangees)
        total_camions = len(camions)
        metrage_total = sum(c["longueur"] for c in camions) / 1000
        poids_total   = df_full["Poids_kg"].sum() if "Poids_kg" in df_full.columns else 0

        surcharge     = metrage_total > L_UTILE / 1000 * total_camions

        st.markdown(f"""
        <div class="kpi-row">
          <div class="kpi">
            <div class="val">{total_camions}</div>
            <div class="lbl">Camion(s)</div>
          </div>
          <div class="kpi">
            <div class="val">{metrage_total:.2f} m</div>
            <div class="lbl">Métrage total</div>
          </div>
          <div class="kpi">
            <div class="val">{total_piles}</div>
            <div class="lbl">Piles créées</div>
          </div>
          <div class="kpi">
            <div class="val">{total_rangees}</div>
            <div class="lbl">Rangées</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        # ── PLAN DE CHARGEMENT ──
        st.markdown("<div class='section-title'>Plan de chargement</div>", unsafe_allow_html=True)

        for cam in camions:
            st.markdown(f"""
            <div class="camion-header">
              <span>Camion {cam['num']}</span>
              <span class="mono">{cam['longueur']/1000:.2f} m / {L_UTILE/1000:.1f} m</span>
            </div>
            """, unsafe_allow_html=True)

            for idx, r in enumerate(cam["rangees"], 1):
                g_pile, g_prof, g_larg = r["gauche"]
                g_html = f"""
                  <div class="slot slot-g">
                    <div class="refs">{refs_display(g_pile)}</div>
                    <div class="meta">{int(g_larg)} mm larg · {int(g_prof)} mm prof · ×{g_pile['nb_niveaux']} niv.</div>
                  </div>"""

                if r["droite"]:
                    d_pile, d_prof, d_larg = r["droite"]
                    d_html = f"""
                      <div class="slot slot-d">
                        <div class="refs">{refs_display(d_pile)}</div>
                        <div class="meta">{int(d_larg)} mm larg · {int(d_prof)} mm prof · ×{d_pile['nb_niveaux']} niv.</div>
                      </div>"""
                else:
                    d_html = '<div class="slot slot-vide"><div class="refs">—</div><div class="meta">vide</div></div>'

                st.markdown(f"""
                <div class="rangee-card">
                  <div class="rangee-num">R{idx:02d}</div>
                  <div class="rangee-depth">{int(r['profondeur'])} mm</div>
                  {g_html}
                  {d_html}
                </div>
                """, unsafe_allow_html=True)

        # ── TABLEAU DÉTAIL ──
        st.markdown("<div class='section-title'>Détail des commandes extraites</div>", unsafe_allow_html=True)

        df_display = df_full[["Ref", "Qte", "Description", "L_mm", "l_mm", "H_mm", "Poids_kg", "Empilable"]].copy()
        df_display.columns = ["Référence", "Qté", "Description", "Long. (mm)", "Larg. (mm)", "Haut. (mm)", "Poids (kg)", "Empilable"]
        st.dataframe(df_display.reset_index(drop=True), use_container_width=True, hide_index=True)

else:
    st.markdown("""
    <div style="text-align:center; padding: 80px 0; color: #aaa;">
      <div style="font-size: 3rem; margin-bottom: 16px;">📋</div>
      <div style="font-size: 1rem; font-weight: 600; color: #555;">Importez vos fichiers puis cliquez sur <strong>Calculer →</strong></div>
      <div style="font-size: 0.85rem; margin-top: 8px;">Base Excel (onglet "Palettes") + un ou plusieurs bons de préparation PDF</div>
    </div>
    """, unsafe_allow_html=True)
