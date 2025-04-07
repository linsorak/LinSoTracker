#!/bin/bash

# Active l'environnement virtuel
source .venv/bin/activate

# Supprime les dossiers existants
rm -rf dist
rm -rf __pycache__
rm -rf build
# rm -f LinSoTracker.spec  # Décommentez si vous souhaitez également supprimer le fichier de spec

# Vérifie que le fichier icon.ico existe
if [ ! -f icon.ico ]; then
    echo "Erreur : Le fichier icon.ico est introuvable."
    exit 1
fi

# Détermine l'icône à utiliser selon le système
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Vérifie si ImageMagick est installé
    if command -v convert >/dev/null 2>&1; then
        echo "Conversion de icon.ico en icon.png..."
        convert icon.ico icon.png
        ICON_OPTION="--icon icon.png"
    else
        echo "Erreur : ImageMagick n'est pas installé. Veuillez l'installer pour convertir l'icône."
        exit 1
    fi
else
    ICON_OPTION="--icon icon.ico"
fi

# Compile avec PyInstaller en utilisant l'icône appropriée
pyinstaller --clean --onefile --specpath . --version-file "properties.rc" $ICON_OPTION "LinSoTracker.py"
if [ $? -ne 0 ]; then
    echo "Erreur lors de la compilation"
    exit 1
fi

# Copie les templates dans le dossier de distribution
mkdir -p dist/templates
cp -r templates/* dist/templates

# Crée un dossier pour les devtemplates
mkdir -p dist/devtemplates

# Copie des fichiers spécifiques s'ils existent
[ -f tracker.data ] && cp tracker.data dist/tracker.data
[ -f .dev ] && cp .dev dist/.dev

echo "Build terminé avec succès !"
