#!/bin/bash
set -e

# création du dossier stockant les résultats du benchmark
mkdir -p 2_benchmark_results/

now () {
    echo "$(date '+%Y-%m-%d_%H%M%S')"
}

run_benchmark () {
    echo "= [$(now)] Attente de 30 secondes..."
    sleep 30s
    image_name=$1
    echo "= [$(now)] Lancement du benchmark ${image_name}..."
    docker compose -f docker-compose.yml up ${image_name}
    docker compose -f docker-compose.yml stop ${image_name}
    echo "= [$(now)] fin du benchmark ${image_name}"
}

echo "= [$(now)] Début du benchmark"

echo "= [$(now)] Suppression du volume de données prometheus"
sudo rm -fr prometheus-data

echo "= [$(now)] démarrage de cadvisor et prometheus"
docker compose -f docker-compose.monitoring.yml up --remove-orphans --detach cadvisor prometheus

run_benchmark debian
run_benchmark official
run_benchmark pyenvbasic
run_benchmark pyenvopt
run_benchmark pyenvoptmarch
run_benchmark pyenvoptmarchbolt
run_benchmark uv

echo "= [$(now)] Arrêt des conteneurs de monitoring"
docker compose -f docker-compose.monitoring.yml stop

echo "= [$(now)] Fin du benchmark"
