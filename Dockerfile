FROM python:3.9-slim

# update and install chromium
RUN apt-get -y update
RUN apt-get install chromium-driver -y

# set display port to avoid crash
ENV DISPLAY=:99

# upgrade pip
RUN pip install --upgrade pip

# copy codee
COPY . /hasznaltauto_checker
WORKDIR hasznaltauto_checker

# install python env
RUN pip3 install -r requirements.txt

ENTRYPOINT ["python", "run.py"]
