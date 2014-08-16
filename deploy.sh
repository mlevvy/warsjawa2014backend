#!/bin/bash
CONTAINER_NAME=$1
DB_NAME=$2
MAILGUN_API_KEY=$3

docker stop ${CONTAINER_NAME}
docker rm ${CONTAINER_NAME}
docker build -t ${CONTAINER_NAME} .
docker run --name ${CONTAINER_NAME} --link ${DB_NAME}:db -d MAILGUN_API_KEY=${MAILGUN_API_KEY} ${CONTAINER_NAME}
