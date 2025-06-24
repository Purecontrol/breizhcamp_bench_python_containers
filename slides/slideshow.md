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

* Sébastien Baguet : devOps [Purecontrol](https://www.purecontrol.com/)
* Gaston Gary : dev [Purecontrol](https://www.purecontrol.com/)
* Luc Sorel-Giffo : lead dev [See you sun](https://seeyousun.fr/)
  - ex-Purecontrol 🫶
  - co-animation [Python Rennes](https://www.meetup.com/fr-FR/python-rennes/) 🔔
  - [@lucsorelgiffo@floss.social](https://floss.social/@lucsorelgiffo)

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

(titre alternatif : Une antiquité bien dynamique)

- traitement et agrégation de **séries temporelles**
- données synthétiques utilisées par d'autres briques métier
- **50 000+ tâches par minute**
- en temps réel
- impératif : **ne pas accumuler de retard**

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

-> parallélisme +++, IO réseau ++, CPU + (traitement des données)

---

### Déploiement old school

- interpréteur python de la VM
- git pull (à la main en SSH)
- installation des dépendances sans **.venv/**
- redémarrage 🤞

![bg right](media/vm-museum.png)

---

### Conteneurisation Docker

```dockerfile
ARG PYTHON_VERSION
FROM python:{PYTHON_VERSION}-slim
# installation des dépendances
# copie des sources
# lancement de l'application
...
```

Avantages classiques d'une image :
- isolation et maitrise du binaire python + dépendances + code source
- exécution iso dev / tests / prod
- déploiement : rapide, automatisable, serein

On en profite pour passer de 3.8 à 3.12 😁

---

### Oui mais... perte de performance de 30% ! 

![bg right](media/futur-c-etait-mieux-avant.jpg)

- **diminution** du nombre de tâches calculées chaque minute de **30%**
- accumulation rapide de **retard**
- optimisation dégradée des pilotages

---

### 🤔 Est-ce l'effet de :

- la conteneurisation et l'allocation de ressources (CPU / RAM, overhead réseau) ?
* la dockerisation (comportement des binaires) ?
* la montée de version de Python ?

---

## Quels sont les points d'optimisation d'un service numérique python ?
- algorithmie
- architecture
- optimisation du runtime
---

### Algorithmie - 1

```python
cursor.execute(t"SELECT * FROM tasks LIMIT 100")
tasks = []
for record in cursor:
  tasks.append(Task.from_db_record(record))
execute_tasks(tasks)
```

```python
tasks = [
  Task.from_db_record(record)
  for record in cursor
] # le corps de la compréhension est exécuté "d'un coup"
```

```python
execute_tasks(
  Task.from_db_record(record) for record in cursor
) # générateur streamant les tâches
```

---

### Algorithmie - 2

- Python est un langage interprété 🐌
* facilite l'encapsulation de binaires pour les traitements CPU ⚡
  - numpy, pandas, polars
  - Tensorflow, pytorch, jax

---

### Architecture

- multithreading ou asyncio pour paralléliser les opérations IO
  * ⚠️ au `global interpreter lock`
  * désactivable dans la 3.14
* multiprocessing pour les opérations CPU

---

### Optimisation de l'exécution - 1

```python
def transfer_money(amount: float, account):
  """ Adds a positive amount of money to the given account """
  assert is_a_valid_amount(amount)
  account.add(amount)
```

`python -O mon_script.py` supprime :
  - `-O` : les assertions, les blocs `if __debug__:`
  - `-OO` : les docstrings aussi

Éviter d'exprimer les vérifications métier avec des `assert`
- ignorées en mode optimize (voir la doc [cmdoption-O](https://docs.python.org/3/using/cmdline.html#cmdoption-O))
- try-except : tout devient `AssertionError`

---

### Optimisation de l'exécution - 2

🧪 Just-in-time compiler (3.13+) :
- modification du bytecode au fil de l'exécution du programme
* additionner des entiers `!=` additionner des décimaux
* 🔎 l'interpréteur doit avoir été compilé avec cette option d'exécution

Voir [whatsnew313-jit-compiler](https://docs.python.org/3/whatsnew/3.13.html#whatsnew313-jit-compiler)

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
