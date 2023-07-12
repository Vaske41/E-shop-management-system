FROM python:3

RUN mkdir -p /opt/src/store/courier
WORKDIR /opt/src/store/courier

COPY store/applicationCourier.py ./applicationCourier.py
COPY store/configuration.py ./configuration.py
COPY store/models.py ./models.py
COPY store/order.abi ./order.abi
COPY store/order.bin ./order.bin
COPY store/blockchainsetup.py ./blockchainsetup.py
COPY store/requiremetns.txt ./requirements.txt
COPY store/roleCheck.py ./roleCheck.py

RUN pip install -r ./requirements.txt

ENV PYTHONPATH="/opt/src/store"

ENTRYPOINT ["python", "./applicationCourier.py"]
