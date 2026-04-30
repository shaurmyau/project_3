set -e 

docker-compose down -v

docker-compose build --no-cache app

docker-compose up -d

sleep 5

docker-compose logs app >> log.txt