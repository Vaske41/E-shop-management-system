import csv
import io

from flask import Flask, request, Response, jsonify
from configuration import Configuration
from models import database, Product, Category, ProductCategory, OrderProduct, Order
from email.utils import parseaddr
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt, get_jwt_identity
from sqlalchemy import and_, or_, func
from sqlalchemy.types import Integer
from roleCheck import roleCheck
import json


def isInt(number):
    try:
        tmp = int(number)
    except ValueError:
        return False
    return True


def isFloat(number):
    try:
        tmp = float(number)
    except ValueError:
        return False
    return True


application = Flask(__name__)
application.config.from_object(Configuration)

jwt = JWTManager(application)

@application.route("/update", methods=["POST"])
@roleCheck("owner")
def update():
    if not request.files.get("file", None):
        return Response(json.dumps({'message': 'Field file is missing.'}), status=400)
    content = request.files["file"].stream.read().decode("utf-8")
    stream = io.StringIO(content)
    reader = csv.reader(stream)

    products = []

    index = 0
    for row in reader:
        if len(row) != 3:
            return Response(json.dumps({'message': f'Incorrect number of values on line {index}.'}), status=400)
        categoriesNames = row[0].split('|')
        productName = row[1]
        price = row[2]
        if not isFloat(price):
            return Response(json.dumps({'message': f'Incorrect price on line {index}.'}), status=400)
        price = float(price)
        if price <= 0:
            return Response(json.dumps({'message': f'Incorrect price on line {index}.'}), status=400)
        product = Product.query.filter(Product.name == productName).first()
        if product:
            return Response(json.dumps({'message': f'Product {productName} already exists.'}), status=400)
        products.append({
            'product': productName,
            'categories': categoriesNames,
            'price': price,
        })
        index += 1

    for productInfo in products:
        product = Product(name=productInfo['product'], price=productInfo['price'])
        database.session.add(product)
        database.session.commit()
        for categoryName in productInfo['categories']:
            category = Category.query.filter(Category.name == categoryName).first()
            if not category:
                category = Category(name=categoryName)
                database.session.add(category)
                database.session.commit()
            productCategory = ProductCategory(productId=product.id, categoryId=category.id)
            database.session.add(productCategory)
            database.session.commit()

    return Response(status=200)


@application.route("/product_statistics", methods=["GET"])
@roleCheck("owner")
def product_statistics():
    products = Product.query \
        .join(OrderProduct, Product.id == OrderProduct.productId) \
        .join(Order, OrderProduct.orderId == Order.id) \
        .having(func.count(Order.id) > 0) \
        .group_by(Product.id)
    statistics = []
    for product in products:
        sold = database.session.query(func.cast(func.coalesce(func.sum(OrderProduct.quantity), 0), Integer)) \
            .join(Product, OrderProduct.productId == Product.id) \
            .join(Order, Order.id == OrderProduct.orderId) \
            .filter(
            and_(
                Product.id == product.id,
                Order.status == 'COMPLETE'
            )
        ) \
            .scalar()
        waiting = database.session.query(func.cast(func.coalesce(func.sum(OrderProduct.quantity), 0), Integer)) \
            .join(Product, OrderProduct.productId == Product.id) \
            .join(Order, Order.id == OrderProduct.orderId) \
            .filter(
            and_(
                Product.id == product.id,
                Order.status != 'COMPLETE'
            )
        ) \
            .scalar()
        statistics.append({
            'name': product.name,
            'sold': int(sold),
            'waiting': int(waiting),
        })
    return Response(json.dumps({'statistics': statistics}), status=200)


@application.route('/category_statistics', methods=['GET'])
@roleCheck('owner')
def category_statistics():
    statistics = []
    subquery = database.session.query(
        Category.id,
        func.sum(OrderProduct.quantity).label('total')
    ).join(ProductCategory, ProductCategory.categoryId == Category.id) \
        .join(Product, Product.id == ProductCategory.productId) \
        .join(OrderProduct, OrderProduct.productId == Product.id) \
        .join(Order, OrderProduct.orderId == Order.id) \
        .filter(Order.status == 'COMPLETE') \
        .group_by(Category.id).subquery()

    categories = Category.query.outerjoin(subquery, Category.id == subquery.c.id) \
        .order_by(func.coalesce(subquery.c.total, 0).desc(), Category.name).all()

    for category in categories:
        statistics.append(category.name)

    return Response(json.dumps({'statistics': statistics}), status=200)


if __name__ == "__main__":
    database.init_app(application)
    application.run(debug=True, host="0.0.0.0", port=5001)