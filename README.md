# LinSoTracker
<img src="https://linsotracker.com/tracker/gitbanner.png"></img>
## Installation

Use the package manager [pip](https://pip.pypa.io/en/stable/) to install LinSoTracker.

```bash
pip install -r requirements.txt
```

## Libraries versions

Here you can find used libraries and their versions

| Library     | Version |
|-------------|---------|
| pygame      | 2.1.2   |
| pygame-menu | 4.2.5   |
| pyinstaller | 5.3     |
| python      | 3.10.0  |

## Build version with no false positive virus

 - Download lastest version of pyinstaller : https://github.com/pyinstaller/pyinstaller/tree/develop
 - Open CMD and go to bootloader directory
 - Run this command :
```bash
    python.exe ./waf all --target-arch=64bit
```
 - Run CMD as admin
 - cd to root Pyinstaller directory
 - Run this command
```bash
    python.exe setup.py install
``` 
 - Go to your LinSoTracker directory and delete "__build__", "__dist__", "__pycache__"
 - Run CMD as admin
```bash
    pyinstaller --clean --onefile --version-file "properties.rc" --icon "icon.ico"  "LinSoTracker.py"
``` 

## Special Thanks

I would like to thank :
 - RawZ
 - Marco
 - Yoshizor 
 - TriRetr0

## Discord 

Join our discord : https://discord.com/invite/5MQvh7MAGN

## 2.4 Patch note

Hello @everyone,

** LinSoTracker 2.4 is now release :  **
    - Windows : https://linsotracker.com/tracker/downloads/LinSoTracker-win.zip

🇫🇷 **Patch note 2.4 :**  
- **Optimisation du code** permettant d'améliorer les performances des calculs de la logique des *Map Templates*.  
- **Ajout d'un template** `2.4 Update` qui permet de montrer les derniers ajouts.  
- **Ajout du template** `Tutorial` par @BusinessAlex.  
- **La molette de la souris vers le haut** a désormais le comportement du clic gauche de la souris sur les objets.  
- **La molette de la souris vers le bas** a désormais le comportement du clic droit de la souris sur les objets.  

### Nouveautés concernant les objets :  
- Ajout de l'objet `DraggableEvolutionItem`.  
- Ajout de l'objet `EditableBox`.  
- Ajout de l'objet `OpenLinkItem`.  
- Nouveaux ajouts permettant aux objets d'avoir des enfants s'ils sont dans un état activé, désactivé, ou les deux.  

### Pour les `@TemplateMaker`  
Il est désormais possible de placer les répertoires des templates en cours de création directement dans le répertoire `devtemplates` à la racine de l'exécutable.  

### Mises à jour des options *Map Template* :  
- Vous pouvez maintenant **drag and drop** les objets sur les différents checks/blocks de la carte. Lorsqu'un objet est dans un bloc, un `!` jaune apparaît près de lui.  
- `RulesOptionsLists` est maintenant un tableau permettant d'avoir plusieurs pages de *rules*. Vous pouvez assigner une *rule* à une page en renseignant son parent — Exemple : `"ParentListName": "Main Rules"`.  
- Dans les *Actions*, il est possible de réinitialiser un objet avec l'action `ResetItem`.  

### Ajout de nouvelles conditions :  
- `haveAlternateValue('Item Name')` → Permet de vérifier si l'objet dispose de sa valeur alternative.  
- `isChecked('Item Name')` → Permet de vérifier si l'objet est coché.  
- `isVisible('Item Name')` → Permet de vérifier si l'objet est visible.  

### Amélioration de l’interface :  
- Les menus ne se ferment désormais que lorsque l'on clique dans leur zone, ce qui permet des interactions avec les différents objets / checks.  


:flag_us: **Patch Note 2.4:**  
- **Code optimization** to improve performance in *Map Templates* logic calculations.  
- **Added a new template** `2.4 Update` showcasing the latest additions.  
- **Added the template** `Tutorial` by @BusinessAlex.  
- **Scrolling the mouse wheel up** now behaves like a left-click on objects.  
- **Scrolling the mouse wheel down** now behaves like a right-click on objects.  

### New Features for Objects:  
- Added the object `DraggableEvolutionItem`.  
- Added the object `EditableBox`.  
- Added the object `OpenLinkItem`.  
- New additions allowing objects to have children if they are in an enabled, disabled, or both states.  

### For `@TemplateMaker`  
It is now possible to place the directories of templates currently being created directly in the `devtemplates` folder at the root of the executable.  

### Updates on *Map Template* Options:  
- You can now **drag and drop** objects onto different checks/blocks on the map. When an object is within a block, a yellow `!` appears next to it.  
- `RulesOptionsLists` is now an array allowing multiple pages of *rules*. You can assign a *rule* to a page by specifying its parent — Example: `"ParentListName": "Main Rules"`.  
- In *Actions*, it's possible to reset an object with the action `ResetItem`.  

### New Conditions Added:  
- `haveAlternateValue('Item Name')` → Checks if the object has an alternate value.  
- `isChecked('Item Name')` → Checks if the object is checked.  
- `isVisible('Item Name')` → Checks if the object is visible.  

### Interface Improvement:  
- Menus now only close when clicked within their area, allowing interactions with different objects / checks.  
