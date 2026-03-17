#!/usr/bin/env python3
"""
Extrait le texte et les positions du template PDF pour identifier les zones.
"""

from pathlib import Path
from pypdf import PdfReader


def extract_text_with_positions(pdf_path: Path):
    """Extrait le texte du PDF avec les informations de position."""
    reader = PdfReader(pdf_path)
    
    print(f"=== Extraction du texte de {pdf_path} ===\n")
    
    for i, page in enumerate(reader.pages):
        print(f"--- Page {i+1} ---")
        
        # Extraire le texte brut
        text = page.extract_text()
        
        # Afficher par lignes avec numéros
        lines = text.split('\n')
        for j, line in enumerate(lines):
            if line.strip():
                print(f"L{j:03d}: {line[:100]}")
        
        print(f"\n--- Fin page {i+1} ({len(lines)} lignes) ---\n")


def find_cerfa_patterns(pdf_path: Path):
    """Recherche les patterns spécifiques du CERFA 2561."""
    reader = PdfReader(pdf_path)
    text = reader.pages[0].extract_text()
    
    patterns = ["2TR", "2BH", "2CK", "2AB", "2DC", "SIRET", "SIREN", 
                "Nom", "Prénom", "naissance", "adresse", "postal",
                "déclarant", "bénéficiaire", "revenus"]
    
    print("=== Recherche de patterns CERFA ===\n")
    
    lines = text.split('\n')
    for pattern in patterns:
        found = False
        for i, line in enumerate(lines):
            if pattern.upper() in line.upper():
                print(f"'{pattern}' trouvé ligne {i}: {line[:80]}")
                found = True
        if not found:
            print(f"'{pattern}' non trouvé")
    
    return text


if __name__ == "__main__":
    template = Path("templates/2561_5243.pdf")
    
    if template.exists():
        extract_text_with_positions(template)
        print("\n" + "="*60 + "\n")
        find_cerfa_patterns(template)
    else:
        print(f"Template non trouvé: {template}")
