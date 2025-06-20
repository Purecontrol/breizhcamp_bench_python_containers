#!/bin/bash

# à exécuter du répertoire racine : bash build/build_images.sh

clean_build () {
    start_datetime=$(date '+%Y-%m-%d_%H%M%S')
    image_name=$1
    echo "= Building image ${image_name} ${start_datetime}" >> build/build_logs.txt
    echo "= Building image ${image_name} ${start_datetime}" >> build/build_times.txt
    { time docker compose -f docker-compose.yml build ${image_name} >> build/build_logs.txt ;} 2>> build/build_times.txt

    echo "== Reclaimed space for ${image_name}" >> build/build_times.txt
    docker images >> build/build_times.txt
    docker system prune -a -f >> build/build_times.txt
}

rm build/build_*.txt
echo "= Cleaning up docker cache and images before build benchmark" >> build/build_times.txt
docker system prune -a -f >> build/build_times.txt

clean_build official
clean_build uv
clean_build pyenvbasic
clean_build pyenvmiopt
clean_build pyenvfullopt
