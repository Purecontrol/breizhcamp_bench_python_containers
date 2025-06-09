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
