from pyspark.sql import SparkSession
from pyspark.sql.functions import sum, coalesce, when, col, lit

import os
import json

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

categories_df = spark.read \
    .format("jdbc") \
    .option("driver", "com.mysql.cj.jdbc.Driver") \
    .option("url", f"jdbc:mysql://{DATABASE_IP}:3306/store") \
    .option("dbtable", "store.categories") \
    .option("user", "root") \
    .option("password", "root") \
    .load()

productCategories_df = spark.read \
    .format("jdbc") \
    .option("driver", "com.mysql.cj.jdbc.Driver") \
    .option("url", f"jdbc:mysql://{DATABASE_IP}:3306/store") \
    .option("dbtable", "store.productcategory") \
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

category_result_df = categories_df \
    .join(productCategories_df, categories_df['id'] == productCategories_df['categoryId'], 'left') \
    .join(products_df, productCategories_df['productId'] == products_df['id'], 'left') \
    .join(orderProducts_df, products_df['id'] == orderProducts_df['productId'], 'left') \
    .join(order_df, order_df['id'] == orderProducts_df['orderId'], 'left') \
    .groupBy(categories_df['name']) \
    .agg(
        coalesce(sum(when((col('status')) == 'COMPLETE', orderProducts_df['quantity'])), lit(0)).alias('completed')
    ).orderBy(col('completed').desc(), categories_df['name']).toJSON().map(lambda json_str: json.loads(json_str)).collect()


print(category_result_df)


spark.stop()