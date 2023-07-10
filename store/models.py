import datetime

from flask_sqlalchemy import SQLAlchemy

database = SQLAlchemy()

class ProductCategory(database.Model):
    __tablename__ = "productcategory"

    id = database.Column(database.Integer, primary_key=True)
    productId = database.Column(database.Integer, database.ForeignKey("products.id"), nullable=False)
    categoryId = database.Column(database.Integer, database.ForeignKey("categories.id"), nullable=False)

class OrderProduct(database.Model):
    __tablename__ = "orderproduct"

    id = database.Column(database.Integer, primary_key=True)
    productId = database.Column(database.Integer, database.ForeignKey("products.id"), nullable=False)
    orderId = database.Column(database.Integer, database.ForeignKey("orders.id"), nullable=False)
    quantity = database.Column(database.Integer, nullable=False)

class Category(database.Model):
    __tablename__ = 'categories'

    id = database.Column(database.Integer, primary_key=True)
    name = database.Column(database.String(256), nullable=False)

    products = database.relationship("Product", secondary=ProductCategory.__table__, back_populates="categories")

    def __repr__(self):
        return self.name

class Product(database.Model):
    __tablename__ = 'products'

    id = database.Column(database.Integer, primary_key=True)
    name = database.Column(database.String(256), nullable=False, unique=True)
    price = database.Column(database.Float, nullable=False)

    categories = database.relationship("Category", secondary=ProductCategory.__table__, back_populates="products")
    orders = database.relationship("Order", secondary=OrderProduct.__table__, back_populates="products")

    def __repr__(self):
        return str({
            'categories': [category.name for category in self.categories],
            'id': self.id,
            'name': self.name,
            'price': round(self.price, 2)
        })

    def getDict(self):
        return {
            'categories': [category.name for category in self.categories],
            'id': self.id,
            'name': self.name,
            'price': self.price,
        }

class Order(database.Model):
    __tablename__ = 'orders'

    id = database.Column(database.Integer, primary_key=True)
    price = database.Column(database.Float, nullable=False)
    status = database.Column(database.String(256), nullable=False, default='CREATED')
    timestamp = database.Column(database.DateTime, nullable=False, default=datetime.datetime.utcnow)
    email = database.Column(database.String(256), nullable=False)
    contract = database.Column(database.String(256))

    products = database.relationship("Product", secondary=OrderProduct.__table__, back_populates="orders")

    def __repr__(self):
        return str({
            "products": [product.getDict() for product in self.products],
            "price": self.price,
            "status": self.status,
            "timestamp": self.timestamp.isoformat(),
        })

    def getDict(self):
        return {
            "products": [product.getDict() for product in self.products],
            "price": self.price,
            "status": self.status,
            "timestamp": self.timestamp.strftime('%Y-%m-%dT%H:%M:%SZ'),
        }