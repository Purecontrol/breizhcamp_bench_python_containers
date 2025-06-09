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

## Le service numérique à conteneuriser : local-processing

(un diagramme plantuml ou mermaid pour illustrer le propos ?)

- dev : pyenv + poetry
- batch lancé toutes les minutes
- récupération des définitions des calculs à faire : IO
- parallélisation
  - récupération des données horodatées à manipuler : IO
  - calculs (conversion, agrégation) : CPU
  - enregistrement des résultats : IO
  - enregistrement de l'état des calculs (succès / échec) : IO

---

## Enjeux et ressources

- nombre de calculs faits chaque minute
- durée moyenne d'un calcul
- CPU et RAM mobilisée

Les performances sur une VM dédiée bichonnée à la main.

---

## Déploiement manuel sur une VM dédiée ?

- utilisation du binaire python distribué avec le système
- dépendances installées sur le système
- git pull + mise à jour des dépendances
- déploiement manuel

![](https://s2.qwant.com/thumbr/474x303/7/7/c159a4416cf1b30fea194a49da801d59f966c0e2d414580ef384f01760efe7/th.jpg?u=https%3A%2F%2Ftse.mm.bing.net%2Fth%3Fid%3DOIP.ZIaKioLPt65-c3ntAHQewgHaEv%26pid%3DApi&q=0&b=1&p=0&a=0)

---

## Conteneurisation Docker

```dockerfile
FROM python:3.12-slim

# installation des dépendances
...
# copie des sources
...
```

L'image embarque tout :
- le binaire Python (passage de 3.8 à 3.11 au passage)
- les dépendances
- le code source
- reproductibilité de l'environnement applicatif
- montée de version automatisable de l'application

---

## Oui mais...

Pertes de performance de 30% !

![width:300px](https://www.petitgoeland.fr/849954-large_default/sweat-homme-col-rond-le-futur-c-etait-mieux-avant.jpg)

---

## Il nous faut un plan

Est-ce l'effet de :
* la conteneurisation et l'allocation de ressources (CPU / RAM, overhead réseau) ?
* la dockerisation (comportement des binaires) ?
* la montée de version de Python ?

---

## Expérimentations 🧪

* VM *a la mano* avec Python 3.11 (pas fait, il me semble - on ne voulait pas renoncer à la dockerisation) 🙅
* Dockerfile avec une image de base embarquant un binaire python 3.12

* -> on retrouve des performances comparables à la VM (😀 ouf !)
* -> on dépend de la version de python de la distribution (pas ouf 😕)
* -> mais qu'est-ce qui cloche avec les images python officielle ? 🤔

---

## Comparaison de Dockerfiles officiels

- https://hub.docker.com/_/python/
  - https://github.com/docker-library/python/blob/14b61451ec7c172cf1d43d8e7859335459fcd344/3.11/slim-bookworm/Dockerfile#L72-L95

---

## Installation personnalisée avec pyenv

voir :
- https://github.com/pyenv/pyenv/blob/master/plugins/python-build/README.md#special-environment-variables : CONFIGURE_OPTS
- https://github.com/pyenv/pyenv/blob/master/plugins/python-build/README.md#building-for-maximum-performance : --enable-optimizations

---

...

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
