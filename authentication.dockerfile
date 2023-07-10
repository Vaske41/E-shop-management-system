FROM python:3

RUN mkdir -p /opt/src/authentication # ovo je da se izvrsi naredba
WORKDIR /opt/src/authentication

COPY authentication/application.py ./application.py
COPY authentication/configuration.py ./configuration.py
COPY authentication/models.py ./models.py
COPY authentication/requiremetns.txt ./requirements.txt

RUN pip install -r ./requirements.txt

ENV PYTHONPATH="/opt/src/authentication"

ENTRYPOINT ["python", "./application.py"]
