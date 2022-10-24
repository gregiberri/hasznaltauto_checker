FROM deinchristian/rpi-selenium-node-chrome:3.14.0
ENV DEBIAN_FRONTEND=noninteractive
USER root

RUN apt update
RUN apt install -y chromium

RUN apt install -y python3 python3-pip

COPY . /hasznaltauto_checker

WORKDIR hasznaltauto_checker

RUN pip3 install -r requirements.txt

ENTRYPOINT ["python3", "run.py"]