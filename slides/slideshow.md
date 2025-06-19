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

- Sébastien Baguet : devOps [Purecontrol](https://www.purecontrol.com/)
- Gaston Gary : dev [Purecontrol](https://www.purecontrol.com/)
- Luc Sorel-Giffo : lead dev [See you sun](https://seeyousun.fr/) (co-animation [Python Rennes](https://www.meetup.com/fr-FR/python-rennes/))


---
## Le service numérique à conteneuriser : local-processing GG

quick intro 

---
### Schema architecture et présentation GG
![width:850px](media/archi.drawio.svg)

---
### key points archi GG

Les specificités propres à LP, objectif d'amélioration et de bonne pratique d'ingenerie logiciel >>> on veut dockeriser

---

### Déploiement manuel sur une VM dédiée ? GG

- utilisation du binaire python distribué avec le système
- dépendances installées sur le système
- git pull + mise à jour des dépendances
- déploiement manuel

![](https://s2.qwant.com/thumbr/474x303/7/7/c159a4416cf1b30fea194a49da801d59f966c0e2d414580ef384f01760efe7/th.jpg?u=https%3A%2F%2Ftse.mm.bing.net%2Fth%3Fid%3DOIP.ZIaKioLPt65-c3ntAHQewgHaEv%26pid%3DApi&q=0&b=1&p=0&a=0)

### Conteneurisation Docker GG

```dockerfile
FROM python:3.12-slim

# installation des dépendances
# copie des sources
...
```

L'image embarque tout :
- le binaire Python (passage de 3.8 à 3.12 au passage)
- les dépendances
- le code source
- reproductibilité de l'environnement applicatif
- montée de version automatisable de l'application

---

### Oui mais... GG

Pertes de performance de 30% !

![width:300px](https://www.petitgoeland.fr/849954-large_default/sweat-homme-col-rond-le-futur-c-etait-mieux-avant.jpg)

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

### Optimisation de l'execution luc

`python -O mon_script.py` (docstrings supprimées, asserts ignorés, à compléter)
- just in time compilation JIT

---

### Optimisation du runtime SEB

- options de compilation de l'interpréteur python

---

#TODO details des flags de compile 

détails des flags dans les images

---

### Comparaison de Dockerfiles officiels LUC

- https://hub.docker.com/_/python/
  - https://github.com/docker-library/python/blob/14b61451ec7c172cf1d43d8e7859335459fcd344/3.11/slim-bookworm/Dockerfile#L72-L95

---

### Installation personnalisée avec pyenv LUC

voir :
- https://github.com/pyenv/pyenv/blob/master/plugins/python-build/README.md#special-environment-variables : CONFIGURE_OPTS
- https://github.com/pyenv/pyenv/blob/master/plugins/python-build/README.md#building-for-maximum-performance : --enable-optimizations

---

### ATTENTION GG
l'utilisation du flag peut vous rendre dépendant de l'architecture CPU.
nécessaire d'avoir la meme archi CPU entre le build et le run.

Temps de compilation de l'interpreteur
l'image peut prendre du temps à build.
stocker l'image déjà compilé dans une registry.

---


## Benchmarking methodo et resultat GG

* comment enquêter ?
  * métriques bas niveau du conteneur (ram, cpu) : `cadvisor`
  * logs métier (nb de tâches traitées, durée moyenne de traitement d'une tâche)
  * profilage du temps passé : kcachegrind

---

### présentation du bench et des différentes images LUC
---

### résultats LUC

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