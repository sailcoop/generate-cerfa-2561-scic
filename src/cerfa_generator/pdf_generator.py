"""
Générateur de PDF CERFA 2561.

Remplit le template CERFA 2561 avec les données des souscripteurs.

Structure du CERFA 2561 (n° 5243) :
- Page A4 (210mm x 297mm)
- Section PAYEUR en haut à gauche
- Section BÉNÉFICIAIRE au milieu gauche
- Section REVENUS au centre avec cases 2XX à droite
"""

import io
import logging
from pathlib import Path
from typing import Optional

from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from .models import Emetteur, Beneficiaire

logger = logging.getLogger("cerfa_generator")


class PDFGeneratorError(Exception):
    """Erreur lors de la génération du PDF."""

    pass


# =============================================================================
# CONFIGURATION DES POSITIONS DES CHAMPS CERFA 2561
# =============================================================================
# Coordonnées en mm depuis le coin INFÉRIEUR GAUCHE de la page
# Pour ajuster : augmenter Y = monter, augmenter X = aller à droite
#
# Le formulaire CERFA 2561 mesure 210mm x 297mm (A4)
# Les cases de saisie sont généralement de 3-4mm de haut
# =============================================================================

# Police par défaut et tailles
FONT_NORMAL = "Helvetica"
FONT_BOLD = "Helvetica-Bold"
FONT_SIZE_SMALL = 7
FONT_SIZE_NORMAL = 8
FONT_SIZE_AMOUNT = 9

# Largeur max des champs pour éviter les débordements (en mm)
FIELD_MAX_WIDTH = {
    # Section PAYEUR (émetteur)
    "raison_sociale": 55,
    "complement_nom": 55,
    "adresse_ligne1": 55,
    "adresse_ligne2": 55,
    "emetteur_code_postal": 15,
    "emetteur_commune": 40,
    "siret": 40,
    "telephone": 30,
    # Section BÉNÉFICIAIRE
    "nom": 45,
    "prenom": 45,
    "date_naissance": 25,
    "dept_naissance": 10,
    "ville_naissance": 35,
    "code_postal": 15,
    "ville": 40,
    "adresse": 55,
    "complement_adresse": 55,
    "amount": 22,  # Largeur des cases de montants
}

# =============================================================================
# SECTION PAYEUR (DÉSIGNATION DU PAYEUR / ÉMETTEUR) - Haut gauche du formulaire
# Coordonnées calibrées selon le template CERFA 2561
# =============================================================================
# Code champ ZM - Raison sociale
FIELD_ZM_RAISON_SOCIALE = (70, 252)
# Code champ ZO - Numéro de la voie
FIELD_ZO_NUMERO_VOIE = (70, 243)
# Code champ ZP - Nature et nom de la voie
FIELD_ZP_NOM_VOIE = (70, 239)
# Code champ ZQ - Commune
FIELD_ZQ_COMMUNE = (70, 235)
# Code champ ZR - Code postal
FIELD_ZR_CODE_POSTAL = (70, 231)
# Code champ ZS - SIRET au 31/12/2025
FIELD_ZS_SIRET_31_12 = (70, 222)
# Code champ ZT - SIRET année N-1
FIELD_ZT_SIRET_N1 = (70, 217)
# Code champ ZX - Nom du correspondant
FIELD_ZX_NOM_CORRESPONDANT = (70, 213)
# Code champ ZZ - Téléphone correspondant
FIELD_ZZ_TEL_CORRESPONDANT = (25, 210)
# Code champ ZW - Prénom correspondant
FIELD_ZW_PRENOM_CORRESPONDANT = (150, 214)
# Code champ ZY - Racine email correspondant
FIELD_ZY_RACINE_EMAIL = (92, 210)
# Code champ ZY - Domaine email correspondant
FIELD_ZY_DOMAINE_EMAIL = (155, 210)

# =============================================================================
# SECTION BÉNÉFICIAIRE (DÉSIGNATION DU BÉNÉFICIAIRE) - Milieu gauche
# Coordonnées calibrées selon le template CERFA 2561
# =============================================================================
# Code champ ZC - Nom de famille
FIELD_ZC_NOM = (70, 201)
# Code champ ZD - Prénoms
FIELD_ZD_PRENOM = (70, 197)
# Code champ AC - Date de naissance (format AAAAMMJJ sur le CERFA)
FIELD_AC_DATE_NAISSANCE = (176, 201)
# Code champ AE - Commune de naissance
FIELD_AE_VILLE_NAISSANCE = (176, 188)
# Code champ ZG - Numéro de la voie
FIELD_ZG_NUMERO_VOIE = (70, 184)
# Code champ ZH - Nature et nom de la voie
FIELD_ZH_NOM_VOIE = (70, 189)
# Code champ ZJ - Code postal de résidence
FIELD_ZJ_CODE_POSTAL = (70, 171)
# Code champ ZI - Commune de résidence
FIELD_ZI_VILLE = (70, 176)
# Code champ AB - Code bénéficiaire
FIELD_AB_CODE_BENEFICIAIRE = (176, 243)
# Code champ AQ - Période référence
FIELD_AQ_PERIODE_REFERENCE = (176, 239)
# Code champ AO - Code établissement
FIELD_AO_CODE_ETABLISSEMENT = (176, 235)
# Code champ AG - Code guichet
FIELD_AG_CODE_GUICHET = (176, 231)
# Code champ AI - Référence du compte
FIELD_AI_REFERENCE_COMPTE = (176, 226)
# Code champ AH - Nature du compte
FIELD_AH_NATURE_COMPTE = (176, 222)
# Code champ BR - Type de compte
FIELD_BR_TYPE_COMPTE = (176, 217)

# =============================================================================
# SECTION REVENUS - Cases 2XX (valeurs alignées à droite dans les cases)
# Coordonnées calibrées selon le template CERFA 2561
# =============================================================================
# Case 2TR (code AR) - Gains/Revenus de placements à revenu fixe
FIELD_2TR = (186, 163)

# Case 2BH (code DQ) - Produits soumis à CSG déductible (option barème)
FIELD_2BH = (94, 101)

# Case 2CK (code AJ) - Crédit d'impôt restituable
FIELD_2CK = (186, 45)

# =============================================================================
# SECTION CODE SEXE - Cases à cocher
# =============================================================================
# Code sexe 1 = Masculin
FIELD_SEXE_MASCULIN = (185, 180)
# Code sexe 2 = Féminin
FIELD_SEXE_FEMININ = (195, 180)


def create_overlay(emetteur: Emetteur, beneficiaire: Beneficiaire, page_size: tuple = A4) -> io.BytesIO:
    """
    Crée une couche de texte à superposer sur le template PDF.

    Args:
        emetteur: Données de l'émetteur (SCIC)
        beneficiaire: Données du bénéficiaire
        page_size: Taille de la page (défaut A4)

    Returns:
        Buffer contenant le PDF de la couche de texte
    """
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=page_size)
    
    def fit_text(text: str, max_width_mm: float, font_name: str, max_font_size: int) -> tuple:
        """
        Ajuste la taille de police pour que le texte tienne dans la largeur donnée.
        
        Returns:
            (font_size, truncated_text)
        """
        from reportlab.pdfbase.pdfmetrics import stringWidth
        
        max_width_pts = max_width_mm * mm
        
        for font_size in range(max_font_size, 5, -1):
            text_width = stringWidth(text, font_name, font_size)
            if text_width <= max_width_pts:
                return font_size, text
        
        # Si même à 6pt ça ne rentre pas, on tronque
        font_size = 6
        while len(text) > 3:
            text_width = stringWidth(text + "...", font_name, font_size)
            if text_width <= max_width_pts:
                return font_size, text + "..."
            text = text[:-1]
        
        return font_size, text
    
    def draw_text(x_mm: float, y_mm: float, text: str, 
                  max_width_mm: float = 50, font_name: str = FONT_NORMAL,
                  max_font_size: int = FONT_SIZE_NORMAL):
        """Dessine du texte avec ajustement automatique de la taille."""
        if not text:  # Ne rien dessiner si le texte est vide
            return
        font_size, fitted_text = fit_text(str(text), max_width_mm, font_name, max_font_size)
        can.setFont(font_name, font_size)
        can.drawString(x_mm * mm, y_mm * mm, fitted_text)
    
    def draw_amount(x_mm: float, y_mm: float, amount: float, max_width_mm: float = 22):
        """
        Dessine un montant aligné à droite dans une case.
        Le x_mm correspond au bord DROIT de la case.
        """
        text = f"{amount:.0f}" if amount == int(amount) else f"{amount:.2f}"
        
        from reportlab.pdfbase.pdfmetrics import stringWidth
        
        # Trouver la bonne taille de police
        font_size = FONT_SIZE_AMOUNT
        text_width = stringWidth(text, FONT_BOLD, font_size)
        max_width_pts = max_width_mm * mm
        
        while text_width > max_width_pts and font_size > 6:
            font_size -= 1
            text_width = stringWidth(text, FONT_BOLD, font_size)
        
        can.setFont(FONT_BOLD, font_size)
        # Aligner à droite : x - largeur du texte
        can.drawRightString(x_mm * mm, y_mm * mm, text)
    
    # =========================================================================
    # REMPLISSAGE DES CHAMPS ÉMETTEUR (PAYEUR)
    # Seuls les champs calibrés sont remplis
    # =========================================================================
    
    # ZM - Raison sociale
    draw_text(
        FIELD_ZM_RAISON_SOCIALE[0], FIELD_ZM_RAISON_SOCIALE[1],
        emetteur.raison_sociale,
        max_width_mm=FIELD_MAX_WIDTH["raison_sociale"],
        max_font_size=FONT_SIZE_NORMAL
    )
    # ZO - Numéro de la voie
    draw_text(
        FIELD_ZO_NUMERO_VOIE[0], FIELD_ZO_NUMERO_VOIE[1],
        emetteur.numero_voie,
        max_width_mm=15,
        max_font_size=FONT_SIZE_NORMAL
    )
    # ZP - Nature et nom de la voie
    draw_text(
        FIELD_ZP_NOM_VOIE[0], FIELD_ZP_NOM_VOIE[1],
        emetteur.nom_voie,
        max_width_mm=FIELD_MAX_WIDTH["adresse_ligne1"],
        max_font_size=FONT_SIZE_NORMAL
    )
    # ZQ - Commune
    draw_text(
        FIELD_ZQ_COMMUNE[0], FIELD_ZQ_COMMUNE[1],
        emetteur.commune,
        max_width_mm=FIELD_MAX_WIDTH["emetteur_commune"],
        max_font_size=FONT_SIZE_NORMAL
    )
    # ZR - Code postal
    draw_text(
        FIELD_ZR_CODE_POSTAL[0], FIELD_ZR_CODE_POSTAL[1],
        emetteur.code_postal,
        max_width_mm=FIELD_MAX_WIDTH["emetteur_code_postal"],
        max_font_size=FONT_SIZE_NORMAL
    )
    # ZS - SIRET au 31/12
    draw_text(
        FIELD_ZS_SIRET_31_12[0], FIELD_ZS_SIRET_31_12[1],
        emetteur.siret_31_12,
        max_width_mm=40,
        max_font_size=FONT_SIZE_NORMAL
    )
    # ZT - SIRET année N-1
    draw_text(
        FIELD_ZT_SIRET_N1[0], FIELD_ZT_SIRET_N1[1],
        emetteur.siret,
        max_width_mm=40,
        max_font_size=FONT_SIZE_NORMAL
    )
    # ZX - Nom du correspondant
    draw_text(
        FIELD_ZX_NOM_CORRESPONDANT[0], FIELD_ZX_NOM_CORRESPONDANT[1],
        emetteur.nom_correspondant,
        max_width_mm=FIELD_MAX_WIDTH["telephone"],
        max_font_size=FONT_SIZE_NORMAL
    )
    # ZZ - Téléphone correspondant
    draw_text(
        FIELD_ZZ_TEL_CORRESPONDANT[0], FIELD_ZZ_TEL_CORRESPONDANT[1],
        emetteur.tel_correspondant,
        max_width_mm=25,
        max_font_size=FONT_SIZE_NORMAL
    )
    # ZW - Prénom correspondant
    draw_text(
        FIELD_ZW_PRENOM_CORRESPONDANT[0], FIELD_ZW_PRENOM_CORRESPONDANT[1],
        emetteur.prenom_correspondant,
        max_width_mm=30,
        max_font_size=FONT_SIZE_NORMAL
    )
    # ZY - Racine email correspondant
    draw_text(
        FIELD_ZY_RACINE_EMAIL[0], FIELD_ZY_RACINE_EMAIL[1],
        emetteur.racine_email,
        max_width_mm=30,
        max_font_size=FONT_SIZE_NORMAL
    )
    # ZY - Domaine email correspondant
    draw_text(
        FIELD_ZY_DOMAINE_EMAIL[0], FIELD_ZY_DOMAINE_EMAIL[1],
        emetteur.domaine_email,
        max_width_mm=30,
        max_font_size=FONT_SIZE_NORMAL
    )
    
    # =========================================================================
    # REMPLISSAGE DES CHAMPS BÉNÉFICIAIRE
    # =========================================================================
    
    # ZC - Nom
    draw_text(
        FIELD_ZC_NOM[0], FIELD_ZC_NOM[1],
        beneficiaire.nom,
        max_width_mm=FIELD_MAX_WIDTH["nom"],
        max_font_size=FONT_SIZE_NORMAL
    )
    # ZD - Prénom
    draw_text(
        FIELD_ZD_PRENOM[0], FIELD_ZD_PRENOM[1],
        beneficiaire.prenom,
        max_width_mm=FIELD_MAX_WIDTH["prenom"],
        max_font_size=FONT_SIZE_NORMAL
    )
    # AC - Date de naissance
    draw_text(
        FIELD_AC_DATE_NAISSANCE[0], FIELD_AC_DATE_NAISSANCE[1],
        beneficiaire.date_naissance,
        max_width_mm=FIELD_MAX_WIDTH["date_naissance"],
        max_font_size=FONT_SIZE_NORMAL
    )
    # AE - Ville de naissance
    draw_text(
        FIELD_AE_VILLE_NAISSANCE[0], FIELD_AE_VILLE_NAISSANCE[1],
        beneficiaire.ville_naissance,
        max_width_mm=FIELD_MAX_WIDTH["ville_naissance"],
        max_font_size=FONT_SIZE_SMALL
    )
    # ZG - Numéro de la voie
    draw_text(
        FIELD_ZG_NUMERO_VOIE[0], FIELD_ZG_NUMERO_VOIE[1],
        beneficiaire.numero_voie,
        max_width_mm=15,
        max_font_size=FONT_SIZE_NORMAL
    )
    # ZH - Nature et nom de la voie
    draw_text(
        FIELD_ZH_NOM_VOIE[0], FIELD_ZH_NOM_VOIE[1],
        beneficiaire.nom_voie,
        max_width_mm=FIELD_MAX_WIDTH["adresse"],
        max_font_size=FONT_SIZE_NORMAL
    )
    # ZJ - Code postal résidence
    draw_text(
        FIELD_ZJ_CODE_POSTAL[0], FIELD_ZJ_CODE_POSTAL[1],
        beneficiaire.code_postal,
        max_width_mm=FIELD_MAX_WIDTH["code_postal"],
        max_font_size=FONT_SIZE_NORMAL
    )
    # ZI - Ville résidence
    draw_text(
        FIELD_ZI_VILLE[0], FIELD_ZI_VILLE[1],
        beneficiaire.ville,
        max_width_mm=FIELD_MAX_WIDTH["ville"],
        max_font_size=FONT_SIZE_NORMAL
    )
    # AB - Code bénéficiaire
    draw_text(
        FIELD_AB_CODE_BENEFICIAIRE[0], FIELD_AB_CODE_BENEFICIAIRE[1],
        beneficiaire.code_beneficiaire,
        max_width_mm=20,
        max_font_size=FONT_SIZE_NORMAL
    )
    # AQ - Période référence
    draw_text(
        FIELD_AQ_PERIODE_REFERENCE[0], FIELD_AQ_PERIODE_REFERENCE[1],
        beneficiaire.periode_reference,
        max_width_mm=20,
        max_font_size=FONT_SIZE_NORMAL
    )
    # AO - Code établissement
    draw_text(
        FIELD_AO_CODE_ETABLISSEMENT[0], FIELD_AO_CODE_ETABLISSEMENT[1],
        beneficiaire.code_etablissement,
        max_width_mm=20,
        max_font_size=FONT_SIZE_NORMAL
    )
    # AG - Code guichet
    draw_text(
        FIELD_AG_CODE_GUICHET[0], FIELD_AG_CODE_GUICHET[1],
        beneficiaire.code_guichet,
        max_width_mm=20,
        max_font_size=FONT_SIZE_NORMAL
    )
    # AI - Référence du compte
    draw_text(
        FIELD_AI_REFERENCE_COMPTE[0], FIELD_AI_REFERENCE_COMPTE[1],
        beneficiaire.reference_compte,
        max_width_mm=30,
        max_font_size=FONT_SIZE_NORMAL
    )
    # AH - Nature du compte
    draw_text(
        FIELD_AH_NATURE_COMPTE[0], FIELD_AH_NATURE_COMPTE[1],
        beneficiaire.nature_compte,
        max_width_mm=20,
        max_font_size=FONT_SIZE_NORMAL
    )
    # BR - Type de compte
    draw_text(
        FIELD_BR_TYPE_COMPTE[0], FIELD_BR_TYPE_COMPTE[1],
        beneficiaire.type_compte,
        max_width_mm=20,
        max_font_size=FONT_SIZE_NORMAL
    )
    
    # =========================================================================
    # SECTION MONTANTS (cases 2XX)
    # =========================================================================
    draw_amount(FIELD_2TR[0], FIELD_2TR[1], beneficiaire.montant_2tr)
    draw_amount(FIELD_2BH[0], FIELD_2BH[1], beneficiaire.montant_2bh)
    draw_amount(FIELD_2CK[0], FIELD_2CK[1], beneficiaire.montant_2ck)
    
    # =========================================================================
    # SECTION CODE SEXE (case à cocher)
    # =========================================================================
    if beneficiaire.code_sexe == "1":
        can.setFont(FONT_BOLD, FONT_SIZE_NORMAL)
        can.drawString(FIELD_SEXE_MASCULIN[0] * mm, FIELD_SEXE_MASCULIN[1] * mm, "X")
    elif beneficiaire.code_sexe == "2":
        can.setFont(FONT_BOLD, FONT_SIZE_NORMAL)
        can.drawString(FIELD_SEXE_FEMININ[0] * mm, FIELD_SEXE_FEMININ[1] * mm, "X")
    
    can.save()
    packet.seek(0)
    return packet


def generate_pdf(
    emetteur: Emetteur,
    beneficiaire: Beneficiaire,
    template_path: Path,
    output_path: Path,
) -> Path:
    """
    Génère un PDF CERFA 2561 rempli pour un bénéficiaire.

    Args:
        emetteur: Données de l'émetteur (SCIC)
        beneficiaire: Données du bénéficiaire
        template_path: Chemin vers le template PDF CERFA
        output_path: Chemin de sortie pour le PDF généré

    Returns:
        Chemin vers le fichier PDF généré

    Raises:
        PDFGeneratorError: Si la génération échoue
    """
    logger.info(f"Génération du PDF pour {beneficiaire.nom_complet}")
    
    if not template_path.exists():
        raise PDFGeneratorError(f"Template PDF introuvable: {template_path}")
    
    try:
        # Lire le template
        template_reader = PdfReader(template_path)
        
        if len(template_reader.pages) == 0:
            raise PDFGeneratorError("Le template PDF est vide")
        
        # Créer la couche de texte
        # Obtenir les dimensions de la première page du template
        template_page = template_reader.pages[0]
        page_width = float(template_page.mediabox.width)
        page_height = float(template_page.mediabox.height)
        
        overlay_buffer = create_overlay(emetteur, beneficiaire, (page_width, page_height))
        overlay_reader = PdfReader(overlay_buffer)
        
        # Créer le PDF de sortie
        writer = PdfWriter()
        
        # Fusionner le template avec la couche de texte (première page uniquement)
        page = template_reader.pages[0]
        page.merge_page(overlay_reader.pages[0])
        writer.add_page(page)
        
        # Ajouter les autres pages du template si présentes
        for i in range(1, len(template_reader.pages)):
            writer.add_page(template_reader.pages[i])
        
        # S'assurer que le répertoire de sortie existe
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Écrire le fichier
        with open(output_path, "wb") as output_file:
            writer.write(output_file)
        
        logger.info(f"PDF généré: {output_path}")
        return output_path
    
    except Exception as e:
        logger.error(f"Erreur lors de la génération du PDF: {e}")
        raise PDFGeneratorError(f"Erreur de génération: {e}")


def generate_all_pdfs(
    emetteur: Emetteur,
    beneficiaires: list[Beneficiaire],
    template_path: Path,
    output_dir: Path,
) -> list[tuple[Beneficiaire, Path]]:
    """
    Génère les PDF CERFA pour tous les bénéficiaires.

    Args:
        emetteur: Données de l'émetteur (SCIC)
        beneficiaires: Liste des bénéficiaires
        template_path: Chemin vers le template PDF
        output_dir: Répertoire de sortie

    Returns:
        Liste de tuples (beneficiaire, chemin_pdf)
    """
    results = []
    total = len(beneficiaires)
    
    logger.info(f"Génération de {total} PDF...")
    
    for i, beneficiaire in enumerate(beneficiaires, start=1):
        logger.info(f"[{i}/{total}] Traitement de {beneficiaire.nom_complet}")
        
        output_path = output_dir / beneficiaire.get_pdf_filename(emetteur.annee)
        
        try:
            pdf_path = generate_pdf(emetteur, beneficiaire, template_path, output_path)
            results.append((beneficiaire, pdf_path))
        except PDFGeneratorError as e:
            logger.error(f"Échec pour {beneficiaire.nom_complet}: {e}")
    
    logger.info(f"Génération terminée: {len(results)}/{total} PDF créés")
    return results
