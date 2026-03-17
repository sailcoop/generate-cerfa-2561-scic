"""
Générateur de PDF CERFA 2561.

Remplit le template CERFA 2561 avec les données des souscripteurs.
"""

import io
import logging
from pathlib import Path
from typing import Optional

from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from .models import Souscripteur

logger = logging.getLogger("cerfa_generator")


class PDFGeneratorError(Exception):
    """Erreur lors de la génération du PDF."""

    pass


# Coordonnées des champs sur le formulaire CERFA 2561
# Ces valeurs peuvent nécessiter un ajustement selon le template exact
# Format: (x, y) en points depuis le coin inférieur gauche
FIELD_POSITIONS = {
    # Partie identification du déclarant (cadre 1)
    "raison_sociale": (45 * mm, 252 * mm),
    "siret": (45 * mm, 242 * mm),
    
    # Partie identification du bénéficiaire (cadre 2)
    "nom": (45 * mm, 205 * mm),
    "prenom": (45 * mm, 195 * mm),
    "date_naissance": (45 * mm, 185 * mm),
    "ville_naissance": (90 * mm, 185 * mm),
    "adresse": (45 * mm, 175 * mm),
    "code_postal_ville": (45 * mm, 165 * mm),
    
    # Partie montants (cadre des revenus)
    # Case 2TR - Revenus de capitaux mobiliers
    "2TR": (165 * mm, 120 * mm),
    # Case 2BH - Revenus déjà soumis aux prélèvements sociaux
    "2BH": (165 * mm, 95 * mm),
    # Case 2CK - Crédit d'impôt
    "2CK": (165 * mm, 65 * mm),
    
    # Année
    "annee": (170 * mm, 270 * mm),
}


def create_overlay(souscripteur: Souscripteur, page_size: tuple = A4) -> io.BytesIO:
    """
    Crée une couche de texte à superposer sur le template PDF.

    Args:
        souscripteur: Données du souscripteur
        page_size: Taille de la page (défaut A4)

    Returns:
        Buffer contenant le PDF de la couche de texte
    """
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=page_size)
    
    # Configuration de la police
    can.setFont("Helvetica", 10)
    
    # Fonction helper pour ajouter du texte
    def add_text(field_name: str, value: str, font_size: int = 10):
        if field_name in FIELD_POSITIONS:
            x, y = FIELD_POSITIONS[field_name]
            can.setFont("Helvetica", font_size)
            can.drawString(x, y, str(value))
    
    # Remplir les champs
    add_text("raison_sociale", souscripteur.raison_sociale)
    add_text("siret", souscripteur.siret)
    add_text("nom", souscripteur.nom)
    add_text("prenom", souscripteur.prenom)
    add_text("date_naissance", souscripteur.date_naissance_formatted)
    add_text("ville_naissance", souscripteur.ville_naissance)
    add_text("code_postal_ville", souscripteur.adresse_complete)
    add_text("annee", str(souscripteur.annee))
    
    # Montants (alignés à droite, plus grand)
    can.setFont("Helvetica-Bold", 11)
    add_text("2TR", f"{souscripteur.montant_2tr:.2f} €", 11)
    add_text("2BH", f"{souscripteur.montant_2bh:.2f} €", 11)
    add_text("2CK", f"{souscripteur.montant_2ck:.2f} €", 11)
    
    can.save()
    packet.seek(0)
    return packet


def generate_pdf(
    souscripteur: Souscripteur,
    template_path: Path,
    output_path: Path,
) -> Path:
    """
    Génère un PDF CERFA 2561 rempli pour un souscripteur.

    Args:
        souscripteur: Données du souscripteur
        template_path: Chemin vers le template PDF CERFA
        output_path: Chemin de sortie pour le PDF généré

    Returns:
        Chemin vers le fichier PDF généré

    Raises:
        PDFGeneratorError: Si la génération échoue
    """
    logger.info(f"Génération du PDF pour {souscripteur.nom_complet}")
    
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
        
        overlay_buffer = create_overlay(souscripteur, (page_width, page_height))
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
    souscripteurs: list[Souscripteur],
    template_path: Path,
    output_dir: Path,
) -> list[tuple[Souscripteur, Path]]:
    """
    Génère les PDF CERFA pour tous les souscripteurs.

    Args:
        souscripteurs: Liste des souscripteurs
        template_path: Chemin vers le template PDF
        output_dir: Répertoire de sortie

    Returns:
        Liste de tuples (souscripteur, chemin_pdf)
    """
    results = []
    total = len(souscripteurs)
    
    logger.info(f"Génération de {total} PDF...")
    
    for i, souscripteur in enumerate(souscripteurs, start=1):
        logger.info(f"[{i}/{total}] Traitement de {souscripteur.nom_complet}")
        
        output_path = output_dir / souscripteur.get_pdf_filename()
        
        try:
            pdf_path = generate_pdf(souscripteur, template_path, output_path)
            results.append((souscripteur, pdf_path))
        except PDFGeneratorError as e:
            logger.error(f"Échec pour {souscripteur.nom_complet}: {e}")
    
    logger.info(f"Génération terminée: {len(results)}/{total} PDF créés")
    return results


def adjust_field_positions(
    field_name: str,
    x_mm: float,
    y_mm: float,
):
    """
    Ajuste la position d'un champ sur le formulaire.
    
    Utile pour calibrer les positions lors de la mise en place initiale.

    Args:
        field_name: Nom du champ
        x_mm: Position X en millimètres
        y_mm: Position Y en millimètres
    """
    FIELD_POSITIONS[field_name] = (x_mm * mm, y_mm * mm)
    logger.debug(f"Position ajustée pour {field_name}: ({x_mm}mm, {y_mm}mm)")
