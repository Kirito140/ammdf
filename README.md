# AMMDF - Planche d'etiquettes

Application de bureau pour creer et imprimer des etiquettes AMMDF sur des feuilles A4.

Chaque page contient une grille de **2 colonnes x 7 lignes**, soit **14 etiquettes par page**. Le nombre total d'etiquettes n'est pas limite : au-dela de 14 etiquettes, une nouvelle page est automatiquement ajoutee.

## Fonctionnalites

- Interface graphique Tkinter.
- Formulaire de saisie integre a la page principale.
- Champs :
  - votre lot ;
  - emplacement ;
  - quantite.
- La quantite cree plusieurs etiquettes identiques dans la liste.
- La quantite n'est pas imprimee sur l'etiquette.
- Logo AMMDF integre dans chaque etiquette.
- Mise en page A4 avec marge d'impression.
- Pagination automatique toutes les 14 etiquettes.
- Apercu du PDF avant impression.
- Navigation entre les pages de l'aperçu.
- Gestionnaire d'imprimante Windows avec choix de l'imprimante et du nombre d'exemplaires.
- Impression macOS via CUPS lorsque l'application est executee depuis macOS.
- Export PDF dans le dossier `files`.
- Executable Windows autonome disponible dans `dist/AMMDF.exe`.

## Prerequis

### Execution Python

- Python 3.11 ou plus recent recommande.
- Tkinter installe avec Python.
- Windows ou macOS pour l'impression directe.

### Installation

Depuis le dossier du projet :

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Sous macOS, installez Python avec Tk via Homebrew, puis créez le venv avec Python 3.12 :

```bash
brew install python@3.12 python-tk@3.12
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Sous Linux :

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

## Lancer l'application

### Impression sous Windows

```powershell
.\.venv\Scripts\python.exe app.py
```

Ou double-cliquez sur :

```text
dist\AMMDF.exe
```

### Impression sous macOS

```bash
.venv/bin/python app.py
```

L'impression macOS utilise CUPS et les commandes `lp` / `lpstat` fournies par le systeme.

## Utilisation

1. Lancez l'application.
2. Le formulaire est deja ouvert et le curseur est place dans le champ `Votre lot`.
3. Saisissez le lot.
4. Appuyez sur `Entree` pour passer a l'emplacement.
5. Saisissez l'emplacement.
6. Appuyez sur `Entree` pour passer a la quantite.
7. Saisissez la quantite souhaitee.
8. Appuyez sur `Entree` ou cliquez sur `Ajouter`.
9. Les etiquettes creees apparaissent dans la liste.
10. Cliquez sur `Apercu / imprimer` pour verifier le rendu.
11. Dans l'aperçu, choisissez `Choisir une imprimante...` puis lancez l'impression.

### Exemple

Avec les valeurs suivantes :

```text
Votre lot     : bonjour
Emplacement   : Bonjour
Quantite      : 12
```

L'application ajoute 12 etiquettes identiques dans la liste. Le nombre `12` n'apparait pas sur les etiquettes imprimees.

## Raccourcis clavier

| Raccourci | Action |
| --- | --- |
| `Ctrl` (Windows) / `⌘` (macOS) + `N` | Afficher le formulaire d'ajout et placer le focus sur le lot |
| `Delete` (Windows) / `⌫` (macOS) | Supprimer l'etiquette selectionnee |
| `Ctrl+Suppr` (Windows) / `⌘+⌫` (macOS) | Vider toute la liste apres confirmation |
| `Ctrl+S` (Windows) / `⌘+S` (macOS) | Enregistrer le PDF |
| `Ctrl+P` (Windows) / `⌘+P` (macOS) | Ouvrir l'aperçu avant impression |
| `Entree` | Passer au champ suivant ou ajouter l'etiquette |
| `←` / `→` | Naviguer entre les pages de l'aperçu |
| `Echap` | Fermer l'aperçu ou le gestionnaire d'imprimante |

## Fichiers produits

Les PDF sont enregistres dans :

```text
files/planche_ammf.pdf
```

Le fichier est remplace a chaque nouvel export ou nouvelle impression.

Avec l'executable Windows, le dossier de sortie est :

```text
dist/files/planche_ammf.pdf
```

## Creer ou mettre a jour l'executable Windows

Le script `update_exe.cmd` automatise la reconstruction :

1. creation du venv s'il n'existe pas ;
2. installation des dependances de build ;
3. nettoyage du build PyInstaller ;
4. creation de `dist/AMMDF.exe` avec le logo et les ressources PDF.

Lancez-le depuis PowerShell ou avec un double-clic :

```powershell
.\update_exe.cmd
```

Le fichier final est genere ici :

```text
dist\AMMDF.exe
```

Fermez l'executable avant de lancer la reconstruction afin que Windows puisse remplacer le fichier.

## Creer l'image disque macOS

Le script `build_macos.sh` compile l'application en `AMMDF.app`, puis cree une image disque avec un raccourci vers le dossier Applications. Il faut macOS, Xcode Command Line Tools et Python 3.11+ avec Tk 8.6+.

```bash
brew install python@3.12 python-tk@3.12
./build_macos.sh
```

Le fichier genere est `dist/AMMDF-macOS.dmg`. Le bundle n'est pas signe ni notarie; une distribution publique necessite une signature Developer ID et une notarisation Apple.

## Dependances

Les dependances d'execution sont dans `requirements.txt` :

- `Pillow` : chargement du logo et rendu d'images ;
- `PyMuPDF` : apercu et rasterisation du PDF ;
- `reportlab` : generation du PDF ;
- `pywin32` : enumeration des imprimantes et impression directe sous Windows.

Les dependances de build sont dans `requirements-build.txt` :

- les dependances d'execution ;
- `PyInstaller` pour creer les applications Windows et macOS.

## Structure du projet

```text
ammdf/
├── app.py                    # Application Tkinter et generation PDF
├── images/
│   └── logo.jpg              # Logo integre aux etiquettes
├── files/                    # PDF generes localement
├── templates/                # Templates HTML existants
├── requirements.txt          # Dependances d'execution
├── requirements-build.txt    # Dependances de build
├── update_exe.cmd            # Reconstruction automatique de l'executable Windows
├── build_macos.sh            # Creation de AMMDF.app et du DMG macOS
└── dist/
  ├── AMMDF.exe             # Executable Windows genere
  └── AMMDF-macOS.dmg       # Image disque macOS generee
```

Les dossiers `build`, `dist`, `.venv`, les caches Python et les PDF generes sont ignores par Git lorsque le projet est versionne.

## Impression

### Windows

Le gestionnaire d'imprimante utilise les pilotes Windows via `pywin32`. Il permet de :

- choisir une imprimante locale ou reseau ;
- choisir le nombre d'exemplaires ;
- envoyer directement les pages A4 au pilote choisi.

Aucun navigateur n'est necessaire.

### macOS

L'impression utilise le systeme CUPS :

- `lpstat -p` pour lister les imprimantes ;
- `lpstat -d` pour trouver l'imprimante par defaut ;
- `lp` pour envoyer le PDF avec le format A4.

## Depannage

### Le PDF est cree mais l'impression echoue

- Verifiez que l'imprimante est allumee et installee dans le systeme.
- Sous Windows, verifiez que `pywin32` est installe dans le venv utilise par l'application.
- Sous macOS, verifiez que l'imprimante apparait dans les reglages systeme et avec `lpstat -p`.
- Utilisez d'abord l'aperçu pour verifier la mise en page.

### Le texte imprime seulement les contours

Le PDF genere contient du texte rempli. Si l'aperçu est correct mais l'impression est en contour :

- verifiez la cartouche noire ;
- lancez un test des buses ;
- nettoyez la tete d'impression ;
- desactivez le mode brouillon ou economie d'encre ;
- verifiez la qualite d'impression du pilote.

### Le logo n'apparait pas

En execution Python, verifiez que le fichier suivant existe :

```text
images/logo.jpg
```

Pour l'executable, relancez `update_exe.cmd` afin de reintegrer les ressources.

## Limites connues

- La mise en page est prevue pour une feuille A4 en portrait.
- Les etiquettes sont organisees en 2 colonnes et 7 lignes par page.
- L'impression directe depend des pilotes installes sur le systeme.
- L'application n'enregistre pas automatiquement les listes entre deux lancements.

## Licence

Ce projet est distribue sous licence **MIT**.

Copyright (c) 2026 Campourcy Maxence.

La licence complete est disponible dans le fichier [LICENSE](LICENSE). Elle autorise notamment l'utilisation, la copie, la modification et la distribution du logiciel, sous reserve de conserver la notice de copyright et les conditions de la licence.
