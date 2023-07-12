import csv
import io

from eth_account import Account
from flask import Flask, request, Response, jsonify
from web3.exceptions import ContractLogicError

from configuration import Configuration
from models import database, Product, Category, ProductCategory, OrderProduct, Order
from email.utils import parseaddr
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt, get_jwt_identity
from sqlalchemy import and_, or_, func
from roleCheck import roleCheck
import json
from blockchainsetup import web3, owner, abi, bytecode


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
    address = request.json.get('address', None)
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

    if not address:
        return Response(json.dumps({'message': 'Missing address.'}), status=400)

    if not web3.is_address(address):
        return Response(json.dumps({'message': 'Invalid address.'}), status=400)

    newContract = web3.eth.contract(
        address=order.contract,
        abi=abi,
        bytecode=bytecode
    )
    try:
        transactionHash = newContract.functions.join_courier(address).transact({
            'from': owner,
        })
    except ContractLogicError as error:
        return Response(json.dumps({'message': f'{str(error)[70:]}'}), status=400)

    order.status = 'PENDING'
    database.session.add(order)
    database.session.commit()
    return Response(status=200)

if __name__ == "__main__":
    database.init_app(application)
    application.run(debug=True, host="0.0.0.0", port=5003)