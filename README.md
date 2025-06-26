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
docker run --rm --init -v $PWD:/home/marp/app -e LANG=$LANG -p 8080:8080 -p 37717:37717 marpteam/marp-cli -s --html .
# -> aller à http://localhost:8080/slides/slideshow.md

# génération et mise à jour en temps réel du fichier html
docker run --rm -v $PWD/:/home/marp/app/ -e LANG=$LANG -e MARP_USER="$(id -u):$(id -g)" marpteam/marp-cli -w slides/slideshow.md


# génération du fichier slides/slideshow.html
docker run --rm -v $PWD/:/home/marp/app/ -e LANG=$LANG -e MARP_USER="$(id -u):$(id -g)" marpteam/marp-cli slides/slideshow.md
```

Documentation Marp :

- https://marpit.marp.app/image-syntax
- https://chris-ayers.com/2023/03/31/customizing-marp
- https://connaissances.fournier38.fr/entry/Utiliser%20les%20graphs%20Mermaid%20dans%20le%20Markdown

## contenu de la présentation

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

conteneurisations :

1. image docker python officielle : 3.12.11. Compilée avec `--enable-optimizations` et potentiellement avec `--with-lto` (https://github.com/docker-library/python/blob/14b61451ec7c172cf1d43d8e7859335459fcd344/3.12/slim-bookworm/Dockerfile#L72-L78)
2. image pyenv sans aucune option d'otimisation dans pyenv
3. image pyenv avec les options d'otimisation `PYTHON_CONFIGURE_OPTS="--enable-optimizations --with-lto"` dans pyenv
4. image pyenv avec les options d'otimisation `PYTHON_CONFIGURE_OPTS="--enable-optimizations --with-lto"` et `PYTHON_CFLAGS="-march=native -mtune=native"` dans pyenv
5. (option) avec la version [python-build-standalone](https://github.com/astral-sh/python-build-standalone) installée avec [uv](https://docs.astral.sh/uv/guides/install-python/) ?
  - `--enable-optimizations` : https://github.com/astral-sh/python-build-standalone/blob/main/cpython-unix/build-cpython.sh#L472
  - `--with-lto` : https://github.com/astral-sh/python-build-standalone/blob/main/cpython-unix/build-cpython.sh#L509
  - pas de `PYTHON_CFLAGS="-march=native -mtune=native"`

## Monitoring du benchmark

### Temps de création des images Docker applicatives

```sh
# construction des images et logging des temps
bash 1_images_build_time.sh
# -> résultats dans le dossier 1_build_times/ (non versionné)
```

Note : la version de python installée dans les images est 3.12.11, sauf debian bookworm qui embarque la 3.11.2

### Performances des images applicatives

```sh
# 0. construire les images
docker compose -f docker-compose.yml build

# 1. lancer le benchmark
bash 2_monitor_benchmark.sh &> "2_benchmark_results/$(date '+%Y-%m-%d_%H%M%S')-benchmark_monitoring.txt"

# 2. plus tard, lancer prometheus et grafana pour visualiser les consommations CPU et RAM
docker compose -f docker-compose.monitoring.yml up grafana

# 3. ouvrir les dashboards grafana
http://127.0.0.1:9100/dashboards

# 4. importer le dashboard 193 (https://grafana.com/grafana/dashboards/193-docker-monitoring/) en sélectionnant la source de données Prometheus

# 5. exporter les données CPU et RAM (toutes les séries, sans pré-formatage) en fichier CSV ; les enregistrer dans 2_benchmark_results

# notes :
# - arrête les conteneurs
docker compose -f docker-compose.monitoring.yml stop
# - arrête et supprime les conteneurs
docker compose -f docker-compose.monitoring.yml down
```

### Notebook d'analyse du benchmark

Documentation marimo :

- https://docs.marimo.io/guides/deploying/deploying_docker/
- https://docs.marimo.io/cli/#marimo-edit

```sh
docker compose -f docker-compose.notebook.yml up
```

Le notebook lit la variable d'environnement `BENCHMARK_SOURCES_CONFIG_FILE` indiquant le fichier JSON de configuration de l'analyse.
Ce fichier a le format suivant :

```js
{
    "build_results_dir": "1_build_times",
    "build_times": "2025-06-22_135819-build_times.txt",
    "benchmark_results_dir": "2_benchmark_results",
    "cpu_usage": "2025-06-23_134155-CPU_Usage-data-as-joinbyfield.csv",
    "ram_usage": "2025-06-23_134155-Memory_Usage-data-as-joinbyfield.csv",
    "images": {
        "debian": {
          // couleur utilisée pour les graphiques de cette image docker
          "color": "#A80030",
          // début du fichier, sans le nom de l'image ni l'extension ("2025-06-23T02-58-28" pour "2025-06-23T02-58-28_debian.json")
            "results_prefix": "2025-06-24T00-49-05"
        },
        "official": {
            "color": "#FFD43B",
            "results_prefix": "2025-06-24T01-19-38"
        },
        "pyenvbasic": {
            "color": "#07B08C",
            "results_prefix": "2025-06-24T01-50-11"
        },
        "pyenvopt": {
            "color": "#068F71",
            "results_prefix": "2025-06-24T02-20-44"
        },
        "pyenvoptmarch": {
            "color": "#046D57",
            "results_prefix": "2025-06-24T02-51-18"
        },
        "pyenvoptmarchbolt": {
            "color": "#034C3C",
            "results_prefix": "2025-06-24T03-21-51"
        },
        "uv": {
            "color": "#AB47BC",
            "results_prefix": "2025-06-24T03-52-24"
        }
    }
}
```