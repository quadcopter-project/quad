FROM docker.io/ubuntu:22.04
WORKDIR /home/quad
COPY . /setup

RUN apt update
# test gui
RUN apt -y install x11-apps
RUN apt-get -y install libavcodec58 libavformat58 \
libswscale5 libswresample3 libavutil56 libusb-1.0-0 \
libpcre2-16-0 libdouble-conversion3 libxcb-xinput0 \
libxcb-xinerama0 qtbase5-dev qtchooser qt5-qmake \
qtbase5-dev-tools python3 python3-pip portaudio19-dev sudo \
zip unzip

RUN pip3 install -r /setup/requirements.txt

# code base too old, using previous versions
#RUN tar -xzf /setup/docker_setup/spinnaker_python-4.0.0.116-cp310-cp310-linux_x86_64.tar.gz -C /setup
RUN tar -xzf /setup/docker_setup/spinnaker_python-3.2.0.62-cp310-cp310-linux_x86_64.tar.gz -C /setup
RUN pip3 install /setup/spinnaker_python-3.2.0.62-cp310-cp310-linux_x86_64.whl
# install drivers 

RUN tar -xzf /setup/docker_setup/spinnaker-3.2.0.62-amd64-pkg.22.04.tar.gz -C /setup





