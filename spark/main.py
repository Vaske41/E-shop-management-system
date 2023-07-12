import json

from flask import Flask, Response
from flask import request

application = Flask(__name__)

import os
import subprocess


@application.route("/category_spark")
def category_spark():
    os.environ["SPARK_APPLICATION_PYTHON_LOCATION"] = "/app/category_statistics.py"

    os.environ[
        "SPARK_SUBMIT_ARGS"] = "--driver-class-path /app/mysql-connector-j-8.0.33.jar --jars /app/mysql-connector-j-8.0.33.jar"

    result = subprocess.check_output(["/template.sh"])
    result_string = result.decode()
    start_position = result_string.find('[{')
    end_position = result_string.find('}]') + 2
    return_result = result_string[start_position:end_position].replace("'", '"')
    return_result_json = json.loads(return_result)
    statistics = []
    for category in return_result_json:
        statistics.append(category['name'])
    return Response(json.dumps({'statistics': statistics}))

@application.route("/product_spark")
def product_spark():
    os.environ["SPARK_APPLICATION_PYTHON_LOCATION"] = "/app/product_statistics.py"

    os.environ[
        "SPARK_SUBMIT_ARGS"] = "--driver-class-path /app/mysql-connector-j-8.0.33.jar --jars /app/mysql-connector-j-8.0.33.jar"

    result = subprocess.check_output(["/template.sh"])
    result_string = result.decode()
    start_position = result_string.find('[{')
    end_position = result_string.find('}]') + 2
    return_result = result_string[start_position:end_position].replace("'", '"')
    return_result_json = json.loads(return_result)

    return Response(json.dumps({'statistics': return_result_json}))

if (__name__ == "__main__"):
    application.run(host="0.0.0.0", port=5005)