---
marp: true
theme: gaia

style: |
  img[alt~="center"] {
    display: block;
    margin: 0 auto;
  }
  section.center table {
    margin-left: auto;
    margin-right: auto;
  }
  section {
    font-size: 32px
  }
  section.lead h1 {
    font-size: 100px
  }
---
<!-- _class: lead -->
# Conteneurisation de Python
Chute de performances et investigations

<!--
_footer: "Sébastien Baguet, Gaston Gary, Luc Sorel-Giffo - BreizhCamp - 27 juin 2025"
 -->

---

## Qui sommes-nous ?

- Luc Sorel-Giffo : lead dev [See you sun](https://seeyousun.fr/) (co-animation [Python Rennes](https://www.meetup.com/fr-FR/python-rennes/))
- Sébastien Baguet : devOps [Purecontrol](https://www.purecontrol.com/)
- Gaston Gary : dev [Purecontrol](https://www.purecontrol.com/)

---

### Luc Sorel-Giffo

- **Tech lead** chez **See you sun**.
- **Expert Python** pendant un et demi chez **Purecontrol**.
- **Consultant formateur Python** pendant 6 ans chez **Zenika**. 
- **Co-fondateur** communauté **Python-Rennes**.
- **génération de documentation** à partir du code source, soit par **analyse statique** (py2puml), soit par **traçage d’exécution** (pydoctrace).

---

### Sébastien Baguet

- **Infra lead** chez **Purecontrol**.
- spécialisé dans **l’infrastructure open source**, **l’automatisation** et la **scalabilité** des systèmes.
- Ancien responsable infrastructure chez **ARIADNEXT by IDNow**.
- **Direction des projets R&D** en Big Data et en machine learning.
- Expertises en **bas niveau** (embarqué, électronique, réparation), aux applicatifs **Linux**, en passant par le **kernel**. 
- Intérêt pour **l’impact environnemental** des technologies.

---

### Gaston Gary 

- développeur Python depuis 3 ans chez **Purecontrol**
- Responsable de la récupération de **données externes** en tout genre: *Méteo, puissances actives, relevés manuels d'exploitants ...*
- interconnexions à des APIs
- Responsable d'un service de calcul de timeseries prénommé ...

#TODO schema marketing et quick presentation metier purecontrol

---

## Applicatif métier local-processing

- Traitement et agrégation de **séries temporelles**
- En temps réel
- Plus de **50 000 tâches par minute**
- Génération de données synthétiques utilisées en entrées par d'autres briques métiers. 
- Objectif : **pas de retard**

---

![bg right;width:850px](media/archi.drawio.svg)

---

### key points architecture

- **MainService**
  - **Thread**: soumission des tâches à ProcessPoolexecutor 
  - **boucle infinie**
    - monitoring
    - update tasks output status

- **Worker**
  - traitement **unitaire** d'une tache
  - **récupération** des données temporelles en entrée
  - **transformation**
  - **écriture** de la série temporelle en output

On peut voir qu'il y a beaucoup de parallélisme, beaucoup d'io réseau.

---

### déploiement old school

- utilisation du python systeme.
- Pas de **virtualenv**.
- Déployé sur une VM a la main.
![bg right](https://s2.qwant.com/thumbr/474x303/7/7/c159a4416cf1b30fea194a49da801d59f966c0e2d414580ef384f01760efe7/th.jpg?u=https%3A%2F%2Ftse.mm.bing.net%2Fth%3Fid%3DOIP.ZIaKioLPt65-c3ntAHQewgHaEv%26pid%3DApi&q=0&b=1&p=0&a=0)

---

### Conteneurisation Docker

```dockerfile
FROM python:3.12-slim
# installation des dépendances
# copie des sources
...
```

- le binaire Python
- les dépendances
- le code source

-> une reproductibilité de l'environnement applicatif
-> montée de version automatisable de l'application

---

### Oui mais... perte de performance de 30% ! 

![bg right](https://www.petitgoeland.fr/849954-large_default/sweat-homme-col-rond-le-futur-c-etait-mieux-avant.jpg)

On observe une **diminution** du nombre d'équipements calculés chaque minute de **30%**, entrainant une **latence** du systeme.

---

Est-ce l'effet de :
* la conteneurisation et l'allocation de ressources (CPU / RAM, overhead réseau) ?
* la dockerisation (comportement des binaires) ?
* la montée de version de Python ?

---

## Quels sont les points d'optimisation d'un service numérique python ?
- algorithmie
- architecture
- optimisation du runtime
---

### algorithmie LUC

 (list comprehension: python c'est lent, rediriger vers code compilé, C Rust numpy compréhension)

---

### architecture LUC

 (gestion des connexions à des bdd, IO, concurrence et parallélisation -> évoquer le `global interpreter lock`)

---

### Optimisation de l'execution

`python -O mon_script.py` (docstrings supprimées, asserts ignorés, à compléter)
- just in time compilation JIT

---

### Optimisation du runtime python

- Différentes optimisations durant les phases de compilations

![center](./media/optimizations.drawio.svg)


- Pour visualiser les options du runtime
  - `python3 -m sysconfig | grep CONFIG_ARGS`


<!-- Seb
Compiler level optimisation

-O3 -> va optimiser fichier par fichier
-march=native -> Séléction de l'architecture courante comme cible
/!\ pas compatible avec un CPU qui n'aurait pas les instructions
Voir ici pour les subset https://gcc.gnu.org/onlinedocs/gcc/x86-Options.html

Profile Guided optimization
Compilation instrumenté -> Execution -> Recompilation optimisé

Inlining, réorganisation des blocs, optimisation des boucles, etc.

Link Time Optimization
Optimisation multi fichier .o

Analyse statique du programme entier

Post Link Optimization
Compilation normale -> Profilage (optionnel) -> Optimisation du binaire

Réarrangement des fonctions/blocs (layout), ICF, optimisation des tables de saut, etc.
Optimisation cache


Flags

https://docs.python.org/3/using/configure.html#performance-options

 -->

#TODO slide recap option compile de chaque image GG

---
<!-- 
### Comparaison de Dockerfiles officiels

- https://hub.docker.com/_/python/
  - https://github.com/docker-library/python/blob/14b61451ec7c172cf1d43d8e7859335459fcd344/3.11/slim-bookworm/Dockerfile#L72-L95

---

### Installation personnalisée avec pyenv LUC

voir :
- https://github.com/pyenv/pyenv/blob/master/plugins/python-build/README.md#special-environment-variables : CONFIGURE_OPTS
- https://github.com/pyenv/pyenv/blob/master/plugins/python-build/README.md#building-for-maximum-performance : --enable-optimizations

--- -->

### Attention aux options de compilation

Si les flags de compilation énoncés plus haut peuvent sembler optimaux,
Il y a  tout de même quelques point important à garder en tête ...

---

###  ils introduisent des **dépendances invisibles** à l’architecture CPU

par exemple pour -march=native
- On **compile** l’interpréteur Python **spécifiquement** pour l’architecture du **CPU**.
- Résultat : l’image **ne fonctionne plus** si on la lance sur une autre architecture (ex: `build` sur AMD → `run` sur INTEL)

Il est donc **crucial** d’avoir la **même architecture CPU** entre le `build` et le `run`

Sinon ➜ crash, `illegal instruction`.


<!-- 
- Nous l'avons découvert à la dur, notre runner gitlab était hébergé sur un noeud proxmox sous cpu **Intel Xeon Platinium**, alors que notre **vm de Production** était sur un noeud proxmox sous cpu **AMD EPYC**. -->

---

## Benchmarking : par où commencer ? 

**Comment enquêter sur les perfs d’un conteneur ?**

---

## Outils

- `cadvisor`
- Métriques et logs niveau applicatif
- Profilage du code

<!-- Pour suivre en temps réel :

- l'usage Mémoire
- l'usage CPU
- l'usage I/O disque & réseau

Idéal pour détecter une **saturation système un éventuel bottleneck**


Exploiter les **logs et métriques** pour suivre :

- Nombre de tâches traitées par minute
- Durée moyenne de traitement par tâche
- Les tâches en echecs.

Permet d'avoir une vision fonctionnelle de la performance de notre application.

Utiliser un profiler comme `kcachegrind` sur les résultats de Cprofile.

Pour visualiser :

- Fonctions les plus coûteuses
- Appels imbriqués
- Consommation CPU par bloc de code

En comparant avant et après, cela pourrait permettre d'identifier un endroit ou l'on passe plus de temps, responsable d'une perte de performance.

```python
python -m cProfile -o prof.out my_app.py && pyprof2calltree -i prof.out -o callgrind.out && kcachegrind callgrind.out
```
 -->
---

### présentation du bench et des différentes images LUC todo reformuler

On a compilé et mesuré le temps de création des conteneurs.

une stack docker compose avec:
- cadvisor
- prometheus
- grafana

---

Maquette de notre applicatif python:
- Cpu heavy
- IO
- en continue sur 30 minutes. 

<!-- Cadvisor génère des métriques sur les conteneurs, prometheus les scraps et les stocks, grafana nous permets de les visualiser.  -->
---

#TODO GASTON tableau récap des flags de compile de chaque Dockerfile

---

### résultats #LUC


- nombre de calculs faits chaque minute
- durée moyenne d'un calcul
- CPU et RAM mobilisée

---

## Conclusions

- python est un langage interprété, son interpréteur est compilé ; des options de compilations existent (https://docs.python.org/3/using/configure.html#general-options, https://docs.python.org/3/using/configure.html#performance-options)

- (https://stackoverflow.com/questions/10192758/how-to-get-the-list-of-options-that-python-was-compiled-with)

```sh
# configuration de python
python3 -m sysconfig
python3 -m sysconfig | grep CONFIG_ARGS
```

- pyenv installe depuis les sources, configuration du build avec des drapeaux ou des variables d'environnement
- python-build-standalone (utilisé par uv) produit des binaires optimisés avec `--enable-optimizations` (https://github.com/astral-sh/python-build-standalone/blob/main/cpython-unix/build-cpython.sh#L472), mais d'autres drapeaux d'optimisation spécifique (à l'architecture du CPU) ne sont pas utilisés

---

### Bonne pratique

 **Construisez l’image une fois**, puis :

- Stockez-la dans une **registry**
- **Réutilisez-la** sur toutes les machines compatibles, et toutes les applications python compatible.

Ne reconstruisez pas l’image inutilement à chaque run.

![bg right](media/buildworkflow.drawio.svg)

---

## Merci !

Vos questions

Vos retours via openfeedback :

![width:400px](media/openfeedback_qrcode.svg)
