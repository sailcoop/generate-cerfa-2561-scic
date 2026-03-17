"""
Modèles de données pour le générateur CERFA.

Définit les structures de données pour les émetteurs (SCIC) et les bénéficiaires.
"""

from datetime import date
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, EmailStr, Field, field_validator


class Emetteur(BaseModel):
    """
    Modèle représentant l'émetteur du CERFA (la SCIC).
    
    Ces informations sont fixes pour toutes les déclarations.
    Codes CERFA: ZM, ZN, ZO, ZP, ZQ, ZR, CR, ZS, ZT, ZX, ZW, ZZ, ZY
    """
    
    # Année fiscale
    annee: int = Field(..., description="Année fiscale")
    
    # ZM - Raison sociale
    raison_sociale: str = Field(..., description="Raison sociale de la SCIC")
    
    # ZN - Complément de nom / sigle
    complement_nom: str = Field(default="", description="Complément de nom ou sigle")
    
    # ZO - Numéro de la voie
    numero_voie: str = Field(default="", description="Numéro de la voie")
    
    # ZP - Nature et nom de la voie
    nom_voie: str = Field(default="", description="Nature et nom de la voie")
    
    # ZQ - Code postal
    code_postal: str = Field(..., description="Code postal")
    
    # ZR - Commune
    commune: str = Field(..., description="Commune")
    
    # CR - Code de la retenue
    code_retenue: str = Field(default="", description="Code de la retenue à la source")
    
    # ZS - SIRET (14 chiffres)
    siret: str = Field(..., description="Numéro SIRET (14 chiffres)")
    
    # SIRET au 31/12 de l'année (peut être différent du SIRET N-1)
    siret_31_12: str = Field(default="", description="SIRET au 31/12 de l'année")
    
    # ZT - NIC (5 derniers chiffres du SIRET)
    nic: str = Field(default="", description="NIC (5 derniers chiffres du SIRET)")
    
    # ZX - Téléphone
    telephone: str = Field(default="", description="Numéro de téléphone")
    
    # ZZ - Téléphone correspondant
    tel_correspondant: str = Field(default="", description="Téléphone du correspondant")
    
    # ZX - Nom du correspondant
    nom_correspondant: str = Field(default="", description="Nom du correspondant")
    
    # ZW - Prénom correspondant
    prenom_correspondant: str = Field(default="", description="Prénom du correspondant")
    
    # ZY - Racine email correspondant (partie avant @)
    racine_email: str = Field(default="", description="Racine email correspondant")
    
    # ZY - Domaine email correspondant (partie après @)
    domaine_email: str = Field(default="", description="Domaine email correspondant")
    
    # ZW - Email
    email: str = Field(default="", description="Adresse email de contact")
    
    # ZZ - Code pays
    code_pays: str = Field(default="FR", description="Code pays (FR par défaut)")
    
    # ZY - Référence déclarant
    reference_declarant: str = Field(default="", description="Référence interne du déclarant")
    
    # Configuration Brevo
    brevo_template_default: str = Field(default="", description="ID template Brevo par défaut")
    brevo_sender_email: str = Field(default="", description="Email expéditeur Brevo")
    brevo_sender_name: str = Field(default="", description="Nom expéditeur Brevo")

    @classmethod
    def from_yaml(cls, config_path: Path) -> "Emetteur":
        """Charge la configuration depuis un fichier YAML."""
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        
        # Extraire les infos Brevo si présentes
        brevo = data.pop("brevo", {})
        
        return cls(
            **data,
            brevo_template_default=brevo.get("id_template_default", ""),
            brevo_sender_email=brevo.get("sender_email", ""),
            brevo_sender_name=brevo.get("sender_name", ""),
        )

    @property
    def adresse_complete(self) -> str:
        """Retourne l'adresse complète sur une ligne."""
        parts = [self.adresse_ligne1]
        if self.adresse_ligne2:
            parts.append(self.adresse_ligne2)
        parts.append(f"{self.code_postal} {self.commune}")
        return ", ".join(parts)


class Beneficiaire(BaseModel):
    """
    Modèle représentant un bénéficiaire (souscripteur de titres participatifs).
    
    Ces informations varient pour chaque déclaration.
    Codes CERFA: ZC, ZD, AC, AE, ZJ, ZI, AB, AQ, BO, AG, AI, AH, BR
    """

    # ZC - Nom de famille
    nom: str = Field(..., description="Nom de famille du bénéficiaire")
    
    # ZD - Prénoms
    prenom: str = Field(..., description="Prénom(s) du bénéficiaire")
    
    # AC - Date de naissance (format AAAAMMJJ)
    date_naissance: str = Field(..., description="Date de naissance (format AAAAMMJJ)")
    
    # AE - Commune de naissance
    ville_naissance: str = Field(..., description="Commune de naissance")
    
    # ZJ - Code postal de résidence
    code_postal: str = Field(..., description="Code postal de résidence")
    
    # ZI - Commune de résidence
    ville: str = Field(..., description="Commune de résidence")
    
    # ZG - Numéro de la voie
    numero_voie: str = Field(default="", description="Numéro de la voie")
    
    # ZH - Nature et nom de la voie
    nom_voie: str = Field(default="", description="Nature et nom de la voie")
    
    # Code sexe (1=Masculin, 2=Féminin)
    code_sexe: str = Field(default="1", description="Code sexe (1=Masculin, 2=Féminin)")
    
    # AB - Code bénéficiaire
    code_beneficiaire: str = Field(default="", description="Code bénéficiaire")
    
    # AQ - Période référence
    periode_reference: str = Field(default="", description="Période de référence")
    
    # AO - Code établissement
    code_etablissement: str = Field(default="", description="Code établissement")
    
    # AG - Code guichet
    code_guichet: str = Field(default="", description="Code guichet")
    
    # AI - Référence du compte
    reference_compte: str = Field(default="", description="Référence du compte")
    
    # AH - Nature du compte
    nature_compte: str = Field(default="", description="Nature du compte")
    
    # BR - Type de compte
    type_compte: str = Field(default="", description="Type de compte")

    # Contact
    email: EmailStr = Field(..., description="Adresse email")
    
    # Template Brevo (optionnel, utilise celui de l'émetteur si vide)
    id_template_brevo: str = Field(default="", description="ID du template Brevo")

    # Montants fiscaux (cases du CERFA)
    montant_2tr: float = Field(..., alias="2TR", description="Case 2TR - Revenus de capitaux mobiliers")
    montant_2bh: float = Field(..., alias="2BH", description="Case 2BH - Revenus déjà soumis aux PS")
    montant_2ck: float = Field(..., alias="2CK", description="Case 2CK - Crédit d'impôt restituable")

    class Config:
        """Configuration du modèle."""
        populate_by_name = True

    @field_validator("date_naissance")
    @classmethod
    def validate_date_naissance(cls, v: str) -> str:
        """Valide le format de la date de naissance."""
        if len(v) != 8:
            raise ValueError("La date de naissance doit être au format AAAAMMJJ")
        try:
            int(v)
        except ValueError:
            raise ValueError("La date de naissance doit contenir uniquement des chiffres")
        return v

    @property
    def date_naissance_formatted(self) -> str:
        """Retourne la date de naissance au format JJ/MM/AAAA."""
        return f"{self.date_naissance[6:8]}/{self.date_naissance[4:6]}/{self.date_naissance[:4]}"

    @property
    def nom_complet(self) -> str:
        """Retourne le nom complet du bénéficiaire."""
        return f"{self.prenom} {self.nom}"

    @property
    def adresse_complete(self) -> str:
        """Retourne l'adresse complète."""
        return f"{self.code_postal} {self.ville}"

    def get_pdf_filename(self, annee: int) -> str:
        """Génère le nom de fichier PDF pour ce bénéficiaire."""
        nom_clean = self.nom.replace(" ", "_").upper()
        prenom_clean = self.prenom.replace(" ", "_").upper()
        return f"CERFA_2561_{annee}_{nom_clean}_{prenom_clean}.pdf"


# Alias pour compatibilité avec l'ancien code
Souscripteur = Beneficiaire


class EmailResult(BaseModel):
    """Résultat de l'envoi d'un email."""

    beneficiaire: Beneficiaire
    success: bool
    message: str
    message_id: Optional[str] = None
