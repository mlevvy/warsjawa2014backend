FROM ubuntu:14.04

RUN apt-get -y update --fix-missing

RUN apt-get -y install python3-pip python3-dev

ADD . /app

RUN pip3 install -r /app/requirements.txt

EXPOSE 80

CMD cd /app && python3 flaskr.py