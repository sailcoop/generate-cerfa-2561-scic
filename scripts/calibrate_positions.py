#!/usr/bin/env python3
"""
Script de calibration pour le CERFA 2561.

Génère UN SEUL PDF avec :
- La grille de coordonnées (mm)
- Les marqueurs aux positions actuelles
- Les valeurs de test remplies

Usage:
    python scripts/calibrate_positions.py
"""

import io
from pathlib import Path
from pypdf import PdfReader, PdfWriter
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.colors import red, blue, green, black, Color, orange
from reportlab.pdfbase.pdfmetrics import stringWidth


def create_calibration_pdf(template_path: Path, output_path: Path):
    """
    Crée un PDF de calibration complet avec grille, marqueurs et valeurs test.
    """
    reader = PdfReader(template_path)
    page = reader.pages[0]
    width = float(page.mediabox.width)
    height = float(page.mediabox.height)
    
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=(width, height))
    
    # =========================================================================
    # 1. GRILLE DE COORDONNÉES
    # =========================================================================
    
    # Grille fine tous les 5mm en gris très clair
    can.setStrokeColor(Color(0.9, 0.9, 0.9))
    can.setLineWidth(0.1)
    for x in range(0, 220, 5):
        can.line(x*mm, 0, x*mm, height)
    for y in range(0, 300, 5):
        can.line(0, y*mm, width, y*mm)
    
    # Grille tous les 10mm plus visible
    can.setStrokeColor(Color(0.75, 0.75, 0.75))
    can.setLineWidth(0.2)
    for x in range(0, 220, 10):
        can.line(x*mm, 0, x*mm, height)
    for y in range(0, 300, 10):
        can.line(0, y*mm, width, y*mm)
    
    # Graduations tous les 20mm avec labels
    can.setFont("Helvetica", 5)
    can.setFillColor(Color(0.4, 0.4, 0.4))
    for x in range(0, 220, 20):
        can.drawString(x*mm + 0.5*mm, 2*mm, f"{x}")
    for y in range(0, 300, 20):
        can.drawString(1*mm, y*mm + 0.5*mm, f"{y}")
    
    # =========================================================================
    # 2. POSITIONS ACTUELLES (coordonnées calibrées selon notes)
    # =========================================================================
    
    # Positions configurées dans pdf_generator.py
    positions = {
        # Section PAYEUR / ÉMETTEUR (vert)
        "ZM Raison sociale": (70, 252, green),
        "ZO Numéro voie": (70, 243, green),
        "ZP Nom voie": (70, 239, green),
        "ZQ Commune": (70, 235, green),
        "ZR Code postal": (70, 231, green),
        "ZS SIRET 31/12": (70, 222, green),
        "ZT SIRET année N-1": (70, 217, green),
        "ZX Nom correspondant": (70, 213, green),
        "ZZ Tel correspondant": (25, 210, green),
        "ZW Prénom corresp.": (150, 214, green),
        "ZY Racine email": (92, 210, green),
        "ZY Domaine email": (155, 210, green),
        
        # Section BÉNÉFICIAIRE (bleu)
        "ZC Nom": (70, 201, blue),
        "ZD Prénom": (70, 197, blue),
        "AC Date naissance": (176, 201, blue),
        "AE Ville naissance": (176, 188, blue),
        "ZG Numéro voie": (70, 184, blue),
        "ZH Nom voie": (70, 189, blue),
        "ZJ Code postal": (70, 171, blue),
        "ZI Ville": (70, 176, blue),
        "AB Code bénéf.": (176, 243, blue),
        "AQ Période réf.": (176, 239, blue),
        "AO Code étab.": (176, 235, blue),
        "AG Code guichet": (176, 231, blue),
        "AI Réf. compte": (176, 226, blue),
        "AH Nature compte": (176, 222, blue),
        "BR Type compte": (176, 217, blue),
        "Sexe M (1)": (185, 180, blue),
        "Sexe F (2)": (195, 180, blue),
        
        # Section MONTANTS (rouge/orange) - alignés à DROITE
        "2TR AR": (176, 163, red),
        "2BH DQ": (84, 101, orange),
        "2CK AJ": (176, 45, red),
    }
    
    def draw_marker(x_mm, y_mm, label, color):
        """Dessine un marqueur avec croix et label."""
        x = x_mm * mm
        y = y_mm * mm
        
        can.setStrokeColor(color)
        can.setFillColor(color)
        
        # Croix bien visible
        can.setLineWidth(1)
        can.line(x - 4*mm, y, x + 4*mm, y)
        can.line(x, y - 3*mm, x, y + 3*mm)
        
        # Point central
        can.circle(x, y, 1.5, fill=1)
        
        # Label avec fond blanc pour lisibilité
        can.setFont("Helvetica-Bold", 6)
        text = f"{label} ({x_mm},{y_mm})"
        text_width = stringWidth(text, "Helvetica-Bold", 6)
        
        # Fond blanc semi-transparent
        can.setFillColor(Color(1, 1, 1, alpha=0.85))
        can.rect(x + 2*mm, y - 1*mm, text_width + 2, 8, fill=1, stroke=0)
        
        # Texte coloré
        can.setFillColor(color)
        can.drawString(x + 3*mm, y, text)
    
    for label, (x, y, color) in positions.items():
        draw_marker(x, y, label, color)
    
    # =========================================================================
    # 3. LÉGENDE EN BAS
    # =========================================================================
    
    can.setFont("Helvetica-Bold", 7)
    can.setFillColor(black)
    can.drawString(5*mm, 8*mm, "LÉGENDE:")
    
    can.setFillColor(green)
    can.drawString(25*mm, 8*mm, "● PAYEUR")
    can.setFillColor(blue)
    can.drawString(50*mm, 8*mm, "● BÉNÉFICIAIRE")
    can.setFillColor(red)
    can.drawString(85*mm, 8*mm, "● MONTANTS 2XX")
    
    can.setFillColor(black)
    can.setFont("Helvetica", 6)
    can.drawString(120*mm, 8*mm, "Coordonnées: (X mm, Y mm) depuis coin inférieur gauche")
    
    can.save()
    packet.seek(0)
    
    # Fusionner avec le template
    overlay = PdfReader(packet)
    writer = PdfWriter()
    page.merge_page(overlay.pages[0])
    writer.add_page(page)
    
    with open(output_path, "wb") as f:
        writer.write(f)
    
    print(f"✅ PDF de calibration: {output_path}")


if __name__ == "__main__":
    template = Path("templates/2561_5243.pdf")
    
    if not template.exists():
        print(f"❌ Template non trouvé: {template}")
        exit(1)
    
    create_calibration_pdf(template, Path("output/calibration.pdf"))
    
    print("\n📋 Instructions:")
    print("1. Ouvrir output/calibration.pdf")
    print("2. Les croix colorées + texte noir = positions ACTUELLES")
    print("3. Lire sur la grille les coordonnées où chaque champ DEVRAIT être")
    print("4. Me donner les nouvelles coordonnées (X,Y) pour chaque champ décalé")
