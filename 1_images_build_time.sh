#!/bin/bash
# à exécuter du répertoire racine : bash 1_images_build_time.sh
set -e

now () {
    echo "$(date '+%Y-%m-%d_%H%M%S')"
}
benchmark_start="$(now)"
build_logs_file="1_build_times/${benchmark_start}-build_logs.txt"
build_times_file="1_build_times/${benchmark_start}-build_times.txt"

clean_build () {
    image_name=$1
    echo "= [$(now)] Construction de l'image ${image_name}" >> ${build_logs_file}
    echo "= [$(now)] Construction de l'image ${image_name}" >> ${build_times_file}
    { time docker compose -f docker-compose.yml build ${image_name} >> ${build_logs_file} ;} 2>> ${build_times_file}

    echo "== [$(now)] Espace récupéré en supprimant l'image ${image_name}" >> ${build_times_file}
    docker images >> ${build_times_file}
    docker system prune -a -f >> ${build_times_file}
}

echo "= [$(now)] Nettoyage du cache docker et des images avant de construire les images" >> ${build_times_file}
docker system prune -a -f >> ${build_times_file}

clean_build official
clean_build uv
clean_build pyenvbasic
clean_build pyenvmiopt
clean_build pyenvfullopt
