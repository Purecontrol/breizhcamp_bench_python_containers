## Abstract

Notre service numérique python de traitement de données temporelles tournait sur un serveur en mêlant multithreading et multiprocessing, il était temps de le conteneuriser. Un coup de Docker et c’est parti… pour une chute de 30% des performances : CPU et RAM qui grimpent, le temps d’exécution aussi et l’ingestion des données prend du retard. Trop.

On s’aperçoit alors que les images Docker Python “officielles” ne sont pas performantes, que l’installation de Python sur un système propose des options de compilation au potentiel intéressant. Un trio se met en place pour élaborer un benchmark pour comparer les performances de différentes façon d’installer Python dans un conteneur Docker : image officielle, Python natif d‘une image Debian, différentes modalités d’installation par pyenv et par uv, l’outil sorti en 2024 qui “dérouille” l’écosystème Python (vous l’avez ?).

Tout benchmark a ses biais, c’est pourquoi nous insisterons sur la démarche élaborée et suivie pour que vous puissiez la reproduire sur vos bases de codes, plutôt que d’insister sur les résultats.

Le trio :

- Gaston Gary : spécialiste du métier du service numérique
- Sébastien Baguet : spécialiste infrastructure et conteneurisation
- Luc Sorel-Giffo : spécialiste Python

## Diaporama

```sh
# lancement d'un serveur web permettant de visualiser la présentation dans un navigateur, qui s'auto-rafraichit
docker run --rm --init -v $PWD:/home/marp/app -e LANG=$LANG -p 8080:8080 -p 37717:37717 marpteam/marp-cli -s .
# -> aller à http://localhost:8080/slides/slideshow.md

# génération et mise à jour en temps réel du fichier html
docker run --rm -v $PWD/:/home/marp/app/ -e LANG=$LANG -e MARP_USER="$(id -u):$(id -g)" marpteam/marp-cli -w slides/slideshow.md


# génération du fichier slides/slideshow.html
docker run --rm -v $PWD/:/home/marp/app/ -e LANG=$LANG -e MARP_USER="$(id -u):$(id -g)" marpteam/marp-cli slides/slideshow.md
```

Documentation :

- https://marpit.marp.app/image-syntax

## contenu de la présentation

- intégrer diagramme de fonctionnement local-pro (Luc)

- comment enquêter ?
  - métriques bas niveau du conteneur (ram, cpu) : `cadvisor`
  - logs métier (nb de tâches traitées, durée moyenne de traitement d'une tâche)
  - profilage du temps passé : kcachegrind

- optimiser un service numérique Python (Luc)
  - algorithmie (list comprehension)
  - architecture (gestion des connexions à des bdd, IO, concurrence et parallélisation -> évoquer le `global interpreter lock`)
  - `python -O mon_script.py` (docstrings supprimées, asserts ignorés, à compléter)
  - options de compilation de l'interpréteur python

- conclusions
  - nous :
    - le profilage du temps d'exécution ne nous a pas aidé
    - [transition vers conclusions génériques] mesurer avant d'optimiser (et après !)
  - plus génériques
    - `python -O` intéressant mais rarement utilisé
    - pyenv par défaut : installation rapide de python mais sans aucune option d'optimisation /!\
    - pyenv avec options d'optimisation : installation lente (on ne le fait pas tous les jours sur son poste ; attention à la CI -> utiliser des images python pré-compilées), mais améliorations conséquentes !
    - uv + python-build-standalone : un binaire python portable a longtemps été une difficulté (différents chemins de fichiers en dur) mais l'ambition de ce projet est de fournir des binaires pré-compilés -> options d'optimisation incluses (à vérifier) et temps de téléchargement rapide

## plan d'expérience

- version ancienne de local-pro (Sébastien et Gary)
- benchmark.py (Luc)

conteneurisations :

1. image docker python officielle : 3.12.11. Compilée avec `--enable-optimizations` et potentiellement avec `--with-lto` (https://github.com/docker-library/python/blob/14b61451ec7c172cf1d43d8e7859335459fcd344/3.12/slim-bookworm/Dockerfile#L72-L78)
2. image pyenv sans aucune option d'otimisation dans pyenv
3. image pyenv avec les options d'otimisation `PYTHON_CONFIGURE_OPTS="--enable-optimizations --with-lto"` dans pyenv
4. image pyenv avec les options d'otimisation `PYTHON_CONFIGURE_OPTS="--enable-optimizations --with-lto"` et `PYTHON_CFLAGS="-march=native -mtune=native"` dans pyenv
5. (option) avec la version [python-build-standalone](https://github.com/astral-sh/python-build-standalone) installée avec [uv](https://docs.astral.sh/uv/guides/install-python/) ?
  - `--enable-optimizations` : https://github.com/astral-sh/python-build-standalone/blob/main/cpython-unix/build-cpython.sh#L472
  - `--with-lto` : https://github.com/astral-sh/python-build-standalone/blob/main/cpython-unix/build-cpython.sh#L509
  - pas de `PYTHON_CFLAGS="-march=native -mtune=native"`

```Dockerfile
FROM debian:bookworm-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

RUN uv python install 3.12.11

# installation de poetry
# installation des dépendances avec poetry
```