import csv
import io

from flask import Flask, request, Response, jsonify
from configuration import Configuration
from models import database, Product, Category, ProductCategory, OrderProduct, Order
from email.utils import parseaddr
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt, get_jwt_identity
from sqlalchemy import and_, or_, func
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
        return Response(json.dumps({'message': 'Field file missing.'}), status=400)
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
            return Response(json.dumps({'message': f'“Product {productName} already exists..'}), status=400)
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
        .filter(Order.status == 'COMPLETE') \
        .group_by(Product.id)
    statistics = []
    for product in products:
        sold = Product.join(OrderProduct, OrderProduct.productId == Product.id) \
            .join(Order, Order.id == OrderProduct.orderId).filter(
            and_(
                Product.id == product.id,
                Order.status == 'COMPLETE',
            )
        ).count()
        waiting = Product.join(OrderProduct, OrderProduct.productId == Product.id) \
            .join(Order, Order.id == OrderProduct.orderId).filter(
            and_(
                Product.id == product.id,
                Order.status == 'PENDING',
            ).count()
        )
        statistics.append({
            'name': product.name,
            'sold': sold,
            'waiting': waiting,
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
        .filter(Order.status == 'COMPLETED') \
        .group_by(Category.id).subquery()

    categories = database.session.query(
        Category
    ).outerjoin(subquery, Category.id == subquery.c.id).order_by(func.coalesce(subquery.c.total, 0).desc(),
                                                                 Category.name).all()

    for category in categories:
        statistics.append(category.name)

    return Response(json.dumps({'statistics': statistics}), status=200)


@application.route("/search", methods=["GET"])
@roleCheck("customer")
def search():
    name = request.args.get('name', '')
    categoryName = request.args.get('category', '')
    if name != '' and categoryName != '':
        products = Product.query.filter(and_(
            Product.name.like(f'%{name}%'),
            or_(
                *[category.name.like(f'%{categoryName}%') for category in Product.categories]
            )
        ))

        categories = Category.query \
            .join(ProductCategory, Category.id == ProductCategory.categoryId) \
            .join(Product, Product.id == ProductCategory.productId) \
            .filter(and_(
            Product.id.in_([product.id for product in products])),
            Category.name.like(f'%{categoryName}%')
        ) \
            .group_by(Category.id) \
            .having(func.count(Product.id) > 0) \
            .all()
    elif categoryName != '':
        products = Product.query.filter(
            or_(
                *[category.name.like(f'%{categoryName}%') for category in Product.categories]
            )
        )
        categories = Category.query \
            .join(ProductCategory, Category.id == ProductCategory.categoryId) \
            .join(Product, Product.id == ProductCategory.productId) \
            .filter(and_(
            Product.id.in_([product.id for product in products])),
            Category.name.like(f'%{categoryName}%')
        ) \
            .group_by(Category.id) \
            .having(func.count(Product.id) > 0) \
            .all()
    elif name != '':
        products = Product.query.filter(Product.name.like(f'%{name}%'))
        categories = Category.query \
            .join(ProductCategory, Category.id == ProductCategory.categoryId) \
            .join(Product, Product.id == ProductCategory.productId) \
            .filter(Product.id.in_([product.id for product in products])) \
            .group_by(Category.id) \
            .having(func.count(Product.id) > 0) \
            .all()
    else:
        products = Product.query.all()
        categories = Category.query \
            .join(ProductCategory, Category.id == ProductCategory.categoryId) \
            .join(Product, Product.id == ProductCategory.productId) \
            .filter(Product.id.in_([product.id for product in products])) \
            .group_by(Category.id) \
            .having(func.count(Product.id) > 0) \
            .all()
    return Response(json.dumps({
        'categories': [str(category) for category in categories],
        'products': [str(product) for product in products]
    }), status=200)


@application.route('/order', methods=["POST"])
@roleCheck('buyer')
def order():
    requests = request.json.get('requests', None)
    email = get_jwt_identity()
    if not requests:
        return Response(json.dumps({'message': 'Field requests is missing.'}), status=400)

    index = 0
    totalPrice = 0.
    for req in requests:
        id = req.get('id', None)
        quantity = req.get('quantity', None)
        if not id:
            return Response(json.dumps({'message': f'Product id is missing for request number {index}.'}), status=400)
        if not quantity:
            return Response(json.dumps({'message': f'Product quantity is missing for request number {index}.'}),
                            status=400)
        if not isInt(id):
            return Response(json.dumps({'message': f'Invalid product id for request number {index}.'}), status=400)
        id = int(id)
        if id <= 0:
            return Response(json.dumps({'message': f'Invalid product id for request number {index}.'}), status=400)
        if not isInt(quantity):
            return Response(json.dumps({'message': f'Invalid product quantity for request number {index}.'}), status=400)
        quantity = int(quantity)
        if quantity <= 0:
            return Response(json.dumps({'message': f'Invalid product quantity for request number {index}.'}), status=400)
        product = Product.query.filter(Product.id == id).first()
        if not product:
            return Response(json.dumps({'message': f'Invalid product for request number {index}.'}), status=400)
        index += 1
        totalPrice += product.price * quantity

    order = Order(price=totalPrice, email=email)
    database.session.add(order)
    database.session.commit()
    for req in requests:
        product = Product.query.filter(Product.id == int(req.get('id'))).first()
        quantity = int(req.get('quantity'))
        orderProduct = OrderProduct(productId=product.id, orderId=order.id, quantity=quantity)
        database.session.add(orderProduct)
        database.session.commit()

    return Response(json.dumps({'id': order.id}), status=200)


@application.route('/status', methods=['GET'])
@roleCheck('buyer')
def status():
    email = get_jwt_identity()
    orders = Order.query.filter(Order.email == email).all()
    return Response(json.dumps({'orders': [str(order) for order in orders]}), status=200)


@application.route('/delivered', methods=['POST'])
@roleCheck('buyer')
def delivered():
    id = request.json.get('id', None)
    if not id:
        return Response(json.dumps({'message': 'Missing order id.'}), status=400)
    if not isInt(id):
        return Response(json.dumps({'message': 'Invalid order id.'}), status=400)
    id = int(id)
    if id <= 0:
        return Response(json.dumps({'message': 'Invalid order id.'}), status=400)
    order = Order.query.filter(and_(
        Order.id == id,
        Order.status == 'PENDING'
    )).first()
    if not order:
        return Response(json.dumps({'message': 'Invalid order id.'}), status=400)
    order.status = 'COMPLETE'
    database.session.add(order)
    database.session.commit(order)
    return Response(status=200)


@application.route('/orders_to_deliver', methods=['GET'])
@roleCheck('courier')
def orders_to_deliver():
    orders = Order.query.filter(Order.status == 'CREATED').all()
    return Response(json.dumps({
        'orders': [{
            'id': order.id,
            'email': order.email,
        } for order in orders]
    }), status=200)


@application.route('/pick_up_order', methods=['POST'])
@roleCheck('courier')
def pick_up_order():
    id = request.json.get('id', None)
    if not id:
        return Response(json.dumps({'message': 'Missing order id.'}), status=400)
    if not isInt(id):
        return Response(json.dumps({'message': 'Invalid order id.'}), status=400)
    id = int(id)
    if id <= 0:
        return Response(json.dumps({'message': 'Invalid order id.'}), status=400)
    order = Order.query.filter(and_(
        Order.id == id,
        Order.status == 'CREATED'
    )).first()
    if not order:
        return Response(json.dumps({'message': 'Invalid order id.'}), status=400)
    order.status = 'PENDING'
    database.session.add(order)
    database.session.commit(order)
    return Response(status=200)


if __name__ == "__main__":
    database.init_app(application)
    application.run(debug=True, host="0.0.0.0", port=5002)
