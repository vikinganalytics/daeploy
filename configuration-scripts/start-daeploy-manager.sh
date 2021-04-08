#!/bin/bash

if (($# == 0)); then
  echo "Please pass arguments -u <docker_user>...-t <docker_token>... -h <host_ip>... -a <activation_key>... -s <secured?>... -v <version_tag>"
  exit 2
fi

while getopts ":u:t:h:a:s:v:" opt;
do
  case $opt in
    u) username=${OPTARG};;
    t) token=${OPTARG};;
    h) host=${OPTARG};;
    a) activation_key=${OPTARG};;
    s) secured=${OPTARG};;
    v) version=${OPTARG};;
  esac
done


echo "Logging in to container registry"
echo $token | docker login --username $username --password-stdin ghcr.io

echo "Pulling the latest version of the image"
docker pull ghcr.io/vikinganalytics/mvi/daeploy_manager:$version

echo "DAEPLOY_HOST_NAME is" $host

echo "Stopping and removing current Docker container"
docker stop daeploy_manager || true && docker rm daeploy_manager || true && \

echo "Creating docker volume for persistent db storage"
docker volume create daeploy_data

echo "Running the latest version of DAEPLOY Manager"
docker run \
        --name daeploy_manager \
        -v /var/run/docker.sock:/var/run/docker.sock \
        -v daeploy_data:/data \
        -p 80:80 \
        -p 443:443 \
        -e DAEPLOY_HOST_NAME=$host \
        -e DAEPLOY_AUTH_ENABLED=true \
        -e DAEPLOY_ACTIVATION_KEY=$activation_key \
        -e DAEPLOY_PROXY_HTTPS=$secured \
        --restart always \
        --log-driver json-file \
        --log-opt max-size=100m \
        --log-opt max-file=5 \
        -d ghcr.io/vikinganalytics/mvi/daeploy_manager:$version

echo "Logging our of container registry"
docker logout ghcr.io