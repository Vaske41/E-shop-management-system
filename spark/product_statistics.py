import json

from pyspark.sql import SparkSession
from pyspark.sql.functions import sum, coalesce, when, col, lit

import os

DATABASE_IP = os.environ["DATABASE_IP"] if ("DATABASE_IP" in os.environ) else "localhost"

builder = SparkSession.builder.appName("Category statistics")

spark = builder.getOrCreate()

products_df = spark.read \
    .format("jdbc") \
    .option("driver", "com.mysql.cj.jdbc.Driver") \
    .option("url", f"jdbc:mysql://{DATABASE_IP}:3306/store") \
    .option("dbtable", "store.products") \
    .option("user", "root") \
    .option("password", "root") \
    .load()

orderProducts_df = spark.read \
    .format("jdbc") \
    .option("driver", "com.mysql.cj.jdbc.Driver") \
    .option("url", f"jdbc:mysql://{DATABASE_IP}:3306/store") \
    .option("dbtable", "store.orderproduct") \
    .option("user", "root") \
    .option("password", "root") \
    .load()

order_df = spark.read \
    .format("jdbc") \
    .option("driver", "com.mysql.cj.jdbc.Driver") \
    .option("url", f"jdbc:mysql://{DATABASE_IP}:3306/store") \
    .option("dbtable", "store.orders") \
    .option("user", "root") \
    .option("password", "root") \
    .load()



product_result_df =  products_df \
    .join(orderProducts_df, orderProducts_df['productId'] == products_df['id']) \
    .join(order_df, order_df['id'] == orderProducts_df['orderId']) \
    .groupBy(products_df['name']) \
    .agg(
        coalesce(sum(when(order_df['status'] == 'COMPLETE', orderProducts_df['quantity'])), lit(0)).alias('sold'),
        coalesce(sum(when(order_df['status'] != 'COMPLETE', orderProducts_df['quantity'])), lit(0)).alias('waiting')
    ).orderBy(products_df['name']).toJSON().map(lambda json_str: json.loads(json_str)).collect()


print(product_result_df)

spark.stop()