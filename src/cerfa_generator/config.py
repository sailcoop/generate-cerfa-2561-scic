"""
Configuration du générateur CERFA.

Gère les paramètres de configuration via variables d'environnement et fichier .env.
"""

import logging
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Charger les variables d'environnement depuis .env
load_dotenv()


class Config(BaseModel):
    """Configuration de l'application."""

    # Brevo API
    brevo_api_key: Optional[str] = Field(default=None, description="Clé API Brevo")
    sender_email: str = Field(default="contact@windcoop.fr", description="Email expéditeur")
    sender_name: str = Field(default="SCIC WindCoop", description="Nom expéditeur")

    # Chemins
    template_path: Path = Field(
        default=Path("templates/2561_5243.pdf"), description="Chemin vers le template PDF"
    )
    output_dir: Path = Field(default=Path("output"), description="Répertoire de sortie des PDFs")
    log_dir: Path = Field(default=Path("logs"), description="Répertoire des logs")

    # Mode debug
    debug: bool = Field(default=False, description="Mode debug")

    @classmethod
    def from_env(cls) -> "Config":
        """Crée une configuration à partir des variables d'environnement."""
        return cls(
            brevo_api_key=os.getenv("BREVO_API_KEY"),
            sender_email=os.getenv("SENDER_EMAIL", "contact@windcoop.fr"),
            sender_name=os.getenv("SENDER_NAME", "SCIC WindCoop"),
            debug=os.getenv("DEBUG", "false").lower() == "true",
        )


def setup_logging(log_dir: Path, debug: bool = False) -> logging.Logger:
    """
    Configure le logging de l'application.

    Args:
        log_dir: Répertoire où stocker les fichiers de log
        debug: Active le mode debug (niveau DEBUG au lieu de INFO)

    Returns:
        Logger configuré
    """
    # Créer le répertoire de logs si nécessaire
    log_dir.mkdir(parents=True, exist_ok=True)

    # Niveau de log
    level = logging.DEBUG if debug else logging.INFO

    # Format des logs
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Logger racine
    logger = logging.getLogger("cerfa_generator")
    logger.setLevel(level)

    # Handler console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Handler fichier
    file_handler = logging.FileHandler(log_dir / "cerfa_generator.log", encoding="utf-8")
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
