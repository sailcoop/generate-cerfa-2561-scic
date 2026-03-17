# CERFA 2561 Generator pour SCIC

Générateur de formulaires CERFA 2561 (IFU - Imprimé Fiscal Unique) pour les souscripteurs de titres participatifs d'une SCIC (Société Coopérative d'Intérêt Collectif).

## 📋 Fonctionnalités

- **Génération de PDF** : Remplit automatiquement les formulaires CERFA 2561 à partir d'un fichier CSV
- **Envoi par email** : Envoie les PDF générés aux souscripteurs via l'API Brevo
- **Mode test** : Permet de tester sans envoyer réellement les emails
- **Logging complet** : Trace toutes les opérations pour le suivi et le débogage

## 🚀 Installation

### Prérequis

- Python 3.10 ou supérieur
- Un compte Brevo avec une clé API (pour l'envoi d'emails)

### Installation

1. Clonez le dépôt :
```bash
git clone <url-du-repo>
cd generate-cerfa-2561-scic
```

2. Créez un environnement virtuel :
```bash
python -m venv .venv
source .venv/bin/activate  # Sur macOS/Linux
# ou
.venv\Scripts\activate  # Sur Windows
```

3. Installez les dépendances :
```bash
pip install -e .
# ou
pip install -r requirements.txt
```

4. Copiez le fichier de configuration :
```bash
cp .env.example .env
```

5. Éditez `.env` avec votre clé API Brevo et vos paramètres.

6. Placez le template PDF CERFA 2561 dans `templates/2561_5243.pdf`.

## 📖 Utilisation

### Format du fichier CSV

Le fichier CSV doit utiliser le point-virgule (`;`) comme séparateur et contenir les colonnes suivantes :

| Colonne | Description | Exemple |
|---------|-------------|---------|
| `annee` | Année fiscale | 2025 |
| `raison_sociale` | Nom de la SCIC | SCIC WINDCOOP |
| `siret` | Numéro SIRET | 91348171900015 |
| `nom` | Nom du souscripteur | DUPONT |
| `prenom` | Prénom du souscripteur | JEAN |
| `date_naissance` | Date de naissance (YYYYMMDD) | 19880809 |
| `ville_naissance` | Ville de naissance | FREJUS |
| `code_postal` | Code postal | 56100 |
| `ville` | Ville de résidence | LORIENT |
| `email` | Adresse email | jean.dupont@example.com |
| `id_template_brevo` | ID du template Brevo | ifu_2025 |
| `2TR` | Montant case 2TR (revenus) | 20 |
| `2BH` | Montant case 2BH (revenus déjà soumis) | 20 |
| `2CK` | Montant case 2CK (crédit d'impôt) | 3 |

Exemple de fichier CSV :
```csv
annee;raison_sociale;siret;nom;prenom;date_naissance;ville_naissance;code_postal;ville;email;id_template_brevo;2TR;2BH;2CK
2025;SCIC WINDCOOP;91348171900015;DUPONT;JEAN;19880809;FREJUS;56100;LORIENT;jean.dupont@example.com;ifu_2025;20;20;3
```

### Commandes disponibles

#### 1. Générer les PDF

```bash
cerfa-generator generate data/souscripteurs.csv
```

Options :
- `--template, -t` : Chemin vers le template PDF (défaut: `templates/2561_5243.pdf`)
- `--output, -o` : Répertoire de sortie (défaut: `output/`)
- `--debug` : Active le mode debug

#### 2. Envoyer les emails

```bash
cerfa-generator send data/souscripteurs.csv --api-key VOTRE_CLE_API
```

Options :
- `--api-key, -k` : Clé API Brevo (ou variable `BREVO_API_KEY`)
- `--pdf-dir, -p` : Répertoire contenant les PDF (défaut: `output/`)
- `--sender-email` : Email de l'expéditeur (ou variable `SENDER_EMAIL`)
- `--sender-name` : Nom de l'expéditeur (ou variable `SENDER_NAME`)
- `--dry-run, -n` : **Mode test** - simule l'envoi sans envoyer réellement
- `--yes, -y` : Confirme automatiquement l'envoi

#### 3. Tout en une commande

```bash
cerfa-generator all data/souscripteurs.csv --api-key VOTRE_CLE_API
```

Combine `generate` et `send` en une seule opération.

### Mode test (dry-run)

Pour tester sans envoyer d'emails :

```bash
# Générer les PDF puis simuler l'envoi
cerfa-generator generate data/souscripteurs.csv
cerfa-generator send data/souscripteurs.csv --dry-run

# Ou tout en un
cerfa-generator all data/souscripteurs.csv --dry-run
```

En mode test :
- ✅ Les PDF sont générés normalement
- ✅ Le CSV est validé
- ✅ Les emails sont simulés (aucun envoi réel)
- ✅ Les logs montrent ce qui aurait été envoyé

## 📁 Structure du projet

```
generate-cerfa-2561-scic/
├── README.md                 # Cette documentation
├── pyproject.toml            # Configuration du package Python
├── requirements.txt          # Dépendances
├── .env.example              # Template de configuration
├── .gitignore
├── src/
│   └── cerfa_generator/
│       ├── __init__.py       # Initialisation du module
│       ├── cli.py            # Interface en ligne de commande
│       ├── config.py         # Configuration et logging
│       ├── models.py         # Modèles de données
│       ├── csv_parser.py     # Parsing du fichier CSV
│       ├── pdf_generator.py  # Génération des PDF
│       └── email_sender.py   # Envoi des emails via Brevo
├── templates/
│   └── 2561_5243.pdf         # Template CERFA (à ajouter)
├── data/
│   └── example.csv           # Exemple de fichier CSV
├── output/                   # PDFs générés
└── logs/                     # Fichiers de log
```

## ⚙️ Configuration

Créez un fichier `.env` à la racine du projet :

```bash
# Clé API Brevo
BREVO_API_KEY=votre_cle_api_brevo

# Email expéditeur (doit être vérifié dans Brevo)
SENDER_EMAIL=contact@windcoop.fr
SENDER_NAME=SCIC WindCoop

# Mode debug
DEBUG=false
```

## 📝 Cases du CERFA 2561

Ce générateur remplit les cases suivantes du CERFA 2561 :

| Case | Description |
|------|-------------|
| **2TR** | Revenus de capitaux mobiliers |
| **2BH** | Revenus déjà soumis aux prélèvements sociaux |
| **2CK** | Crédit d'impôt (prélèvement non libératoire déjà versé) |

## 🔧 Personnalisation

### Ajuster les positions des champs

Si les textes ne sont pas correctement positionnés sur le PDF, vous pouvez ajuster les coordonnées dans `pdf_generator.py` :

```python
FIELD_POSITIONS = {
    "raison_sociale": (45 * mm, 252 * mm),
    "siret": (45 * mm, 242 * mm),
    # ... etc
}
```

Les coordonnées sont en millimètres depuis le coin inférieur gauche de la page.

## 🐛 Dépannage

### Les positions des champs sont décalées
1. Ouvrez le PDF généré
2. Identifiez le décalage
3. Ajustez les valeurs dans `FIELD_POSITIONS`

### Erreur "Template PDF introuvable"
- Assurez-vous que le fichier `2561_5243.pdf` est bien dans le dossier `templates/`

### Erreur API Brevo
- Vérifiez que votre clé API est correcte
- Vérifiez que l'email expéditeur est bien vérifié dans Brevo

## 📜 Licence

MIT License - voir le fichier LICENSE pour plus de détails.

## 🤝 Contribution

Les contributions sont les bienvenues ! N'hésitez pas à ouvrir une issue ou une pull request.
