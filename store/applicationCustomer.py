import csv
import io

from flask import Flask, request, Response, jsonify
from web3.exceptions import ContractLogicError, InvalidAddress

from configuration import Configuration
from models import database, Product, Category, ProductCategory, OrderProduct, Order
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt, get_jwt_identity
from sqlalchemy import and_, or_, func
from roleCheck import roleCheck
import json
from web3 import Account
from blockchainsetup import owner, orderContractInterface, bytecode, abi, web3


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


@application.route("/search", methods=["GET"])
@roleCheck("customer")
def search():
    name = request.args.get('name', '')
    categoryName = request.args.get('category', '')
    if name != '' and categoryName != '':
        products = Product.query.join(Product.categories).filter(and_(
            Product.name.like(f'%{name}%'),
            Category.name.like(f'%{categoryName}%')
        )).group_by(Product.id).all()

        categories = Category.query \
            .join(ProductCategory, Category.id == ProductCategory.categoryId) \
            .join(Product, Product.id == ProductCategory.productId) \
            .filter(and_(
            Product.id.in_([product.id for product in products]),
            Category.name.like(f'%{categoryName}%'))
        ) \
            .group_by(Category.id) \
            .having(func.count(Product.id) > 0) \
            .all()
    elif categoryName != '':

        products = Product.query.join(Product.categories).filter(
            Category.name.like(f'%{categoryName}%')
        ).group_by(Product.id).all()

        categories = Category.query \
            .join(ProductCategory, Category.id == ProductCategory.categoryId) \
            .join(Product, Product.id == ProductCategory.productId) \
            .filter(and_(
            Product.id.in_([product.id for product in products]),
            Category.name.like(f'%{categoryName}%'))
        ) \
            .group_by(Category.id) \
            .having(func.count(Product.id) > 0) \
            .all()
    elif name != '':
        products = Product.query.filter(Product.name.like(f'%{name}%')).all()
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
        'products': [product.getDict() for product in products]
    }), status=200)


@application.route('/order', methods=["POST"])
@roleCheck('customer')
def order():
    requests = request.json.get('requests', None)
    address = request.json.get('address', None)
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
            return Response(json.dumps({'message': f'Invalid product quantity for request number {index}.'}),
                            status=400)
        quantity = int(quantity)
        if quantity <= 0:
            return Response(json.dumps({'message': f'Invalid product quantity for request number {index}.'}),
                            status=400)
        product = Product.query.filter(Product.id == id).first()
        if not product:
            return Response(json.dumps({'message': f'Invalid product for request number {index}.'}), status=400)
        index += 1
        totalPrice += product.price * quantity

    if not address:
        return Response(json.dumps({'message': 'Field address is missing.'}), status=400)

    if not web3.is_address(address):
        return Response(json.dumps({'message': 'Invalid address.'}), status=400)


    transactionHash = orderContractInterface.constructor(address).transact({
            "from": owner,
    })
    receipt = web3.eth.wait_for_transaction_receipt(transactionHash)

    order = Order(price=totalPrice, email=email, contract=receipt.contractAddress)
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
@roleCheck('customer')
def status():
    email = get_jwt_identity()
    result = {'orders': []}
    orders = (
        Order.query
        .filter(Order.email == email)
        .all()
    )

    for order in orders:
        order_data = {
            "products": [],
            "price": order.price,
            "status": order.status,
            "timestamp": order.timestamp.strftime('%Y-%m-%dT%H:%M:%SZ'),
        }

        orderProducts = OrderProduct.query.filter(OrderProduct.orderId == order.id).all()

        for orderProduct in orderProducts:
            product = Product.query.filter(Product.id == orderProduct.productId).first()
            product_data = {
                "categories": [category.name for category in product.categories],
                "name": product.name,
                "price": product.price,
                "quantity": orderProduct.quantity,
            }
            order_data["products"].append(product_data)

        result["orders"].append(order_data)

    return Response(json.dumps(result), status=200)


@application.route('/pay', methods=['POST'])
@roleCheck('customer')
def pay():
    id = request.json.get('id', None)
    keys = request.json.get('keys', None)
    passphrase = request.json.get('passphrase', None)

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

    if not keys:
        return Response(json.dumps({'message': 'Missing keys.'}), status=400)
    if not passphrase or len(passphrase) == 0:
        return Response(json.dumps({'message': 'Missing passphrase.'}), status=400)

    try:
        encodedKeys = json.loads(keys.replace("'", '"'))
        privateKey = Account.decrypt(encodedKeys, passphrase).hex()
        address = web3.to_checksum_address(encodedKeys['address'])
    except Exception as e:
        return Response(json.dumps({'message': 'Invalid credentials.'}), status=400)

    newContract = web3.eth.contract(
        address=order.contract,
        abi=abi,
        bytecode=bytecode
    )


    try:
        transactionHash = newContract.functions.pay().build_transaction({
            "from": address,
			"value": int(order.price),
            "gasPrice": 21000,
            "nonce": web3.eth.get_transaction_count(address),
        })

        signedTransaction = web3.eth.account.sign_transaction(transactionHash, privateKey)
        tr_hash = web3.eth.send_raw_transaction(signedTransaction.rawTransaction)
        transaction_receipt = web3.eth.wait_for_transaction_receipt(tr_hash)
    except ContractLogicError as error:
        return Response(json.dumps({'message': f'{str(error)[70:]}'}), status=400)
    except ValueError as ve:
        return Response(json.dumps({'message': 'Insufficient funds.'}), status=400)

    return Response(status=200)


@application.route('/delivered', methods=['POST'])
@roleCheck('customer')
def delivered():
    id = request.json.get('id', None)
    keys = request.json.get('keys', None)
    passphrase = request.json.get('passphrase', None)

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

    if not keys:
        return Response(json.dumps({'message': 'Missing keys.'}), status=400)
    if not passphrase or len(passphrase) == 0:
        return Response(json.dumps({'message': 'Missing passphrase.'}), status=400)

    try:
        keys = json.loads(keys.replace("'", '"'))
        address = web3.to_checksum_address(keys['address'])
        privateKey = Account.decrypt(keys, passphrase).hex()

    except Exception as e:
        return Response(json.dumps({'message': 'Invalid credentials.'}), status=400)

    newContract = web3.eth.contract(
        address=order.contract,
        abi=abi,
        bytecode=bytecode
    )

    try:
        transactionHash = newContract.functions.deliver().build_transaction({
            "from": address,
            "gasPrice": 21000,
            "nonce": web3.eth.get_transaction_count(address),
        })

        signedTransaction = web3.eth.account.sign_transaction(transactionHash, privateKey)
        tr_hash = web3.eth.send_raw_transaction(signedTransaction.rawTransaction)
        transaction_receipt = web3.eth.wait_for_transaction_receipt(tr_hash)
    except ContractLogicError as error:
        return Response(json.dumps({'message': f'{str(error)[70:]}'}), status=400)
    except ValueError as ve:
        return Response(json.dumps({'message': 'Insufficient funds.'}), status=400)


    order.status = 'COMPLETE'
    database.session.add(order)
    database.session.commit()
    return Response(status=200)


if __name__ == "__main__":
    database.init_app(application)
    application.run(debug=True, host="0.0.0.0", port=5002)
