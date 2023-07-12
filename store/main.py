from flask import Flask
from flask import request

application = Flask(__name__)

import os
import subprocess


@application.route("/category_spark")
def database():
    os.environ["SPARK_APPLICATION_PYTHON_LOCATION"] = "/app/category_statistics.py"

    os.environ[
        "SPARK_SUBMIT_ARGS"] = "--driver-class-path /app/mysql-connector-j-8.0.33.jar --jars /app/mysql-connector-j-8.0.33.jar"

    result = subprocess.check_output(["/template.sh"])
    return result.decode()

@application.route("/product_spark")
def database():
    os.environ["SPARK_APPLICATION_PYTHON_LOCATION"] = "/app/product_statistics.py"

    os.environ[
        "SPARK_SUBMIT_ARGS"] = "--driver-class-path /app/mysql-connector-j-8.0.33.jar --jars /app/mysql-connector-j-8.0.33.jar"

    result = subprocess.check_output(["/template.sh"])
    return result.decode()

if (__name__ == "__main__"):
    application.run(host="0.0.0.0", port=5005)