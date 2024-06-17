#!/bin/bash
# check if docker image has already been made
IMAGE_EXISTS=$(docker images --format "{{.Repository}}" | grep "quadproject/quadbox")
if [ -z "$IMAGE_EXISTS" ]; then
	echo "Image $IMAGE_NAME does not exist, building..."

	# Build the Docker image
	docker build -t "quadproject/quadbox" .
else
	echo "Image quadproject/quadbox already exists, skipping build."
fi

# run docker instance
sudo docker run --privileged --rm -it --net=host --env="DISPLAY" -v $PWD:/home/quad quadproject/quadbox
