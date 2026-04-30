import sys
import time
from decimal import Decimal
from sqlalchemy import (
    create_engine, Column, Integer, String, Numeric, ForeignKey, DateTime, func
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship, Session
from sqlalchemy.exc import SQLAlchemyError

Base = declarative_base()

# Модели базы данных

class Customer(Base):
    __tablename__ = 'customers'
    customer_id = Column(Integer, primary_key=True)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    email = Column(String(100), nullable=False, unique=True)

class Product(Base):
    __tablename__ = 'products'
    product_id = Column(Integer, primary_key=True)
    product_name = Column(String(100), nullable=False)
    price = Column(Numeric(10, 2), nullable=False)

class Order(Base):
    __tablename__ = 'orders'
    order_id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey('customers.customer_id'), nullable=False)
    order_date = Column(DateTime, server_default=func.now())
    total_amount = Column(Numeric(10, 2), default=0.00)

    customer = relationship("Customer")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")

class OrderItem(Base):
    __tablename__ = 'order_items'
    order_item_id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('orders.order_id'), nullable=False)
    product_id = Column(Integer, ForeignKey('products.product_id'), nullable=False)
    quantity = Column(Integer, nullable=False)
    subtotal = Column(Numeric(10, 2), nullable=False)

    order = relationship("Order", back_populates="items")
    product = relationship("Product")

# Функции-сценарии с атомарными транзакциями

def create_order(session: Session, customer_id: int, items_data: list[dict]) -> Order:
    """
    Сценарий 1: Размещение заказа с атомарной транзакцией.
    items_data = [{'product_id': 1, 'quantity': 2}, ...]
    """
    try:
        with session.begin():
            new_order = Order(customer_id=customer_id)
            session.add(new_order)
            session.flush()

            total = Decimal('0.00')
            for item in items_data:
                product = session.get(Product, item['product_id'])
                if not product:
                    raise ValueError(f"Продукт с id={item['product_id']} не найден")
                quantity = item['quantity']
                subtotal = product.price * quantity
                order_item = OrderItem(
                    order_id=new_order.order_id,
                    product_id=product.product_id,
                    quantity=quantity,
                    subtotal=subtotal
                )
                session.add(order_item)
                total += subtotal

            new_order.total_amount = total

        print(f"Заказ #{new_order.order_id} успешно создан. Сумма: {total}")
        return new_order

    except (SQLAlchemyError, ValueError) as e:
        print(f"Ошибка при создании заказа: {e}")
        raise

def update_customer_email(session: Session, customer_id: int, new_email: str) -> Customer:
    """
    Сценарий 2: Атомарное обновление email клиента.
    """
    try:
        with session.begin():
            customer = session.get(Customer, customer_id)
            if not customer:
                raise ValueError(f"Клиент с id={customer_id} не найден")
            customer.email = new_email
        print(f"Email клиента #{customer_id} обновлён на {new_email}")
        return customer

    except (SQLAlchemyError, ValueError) as e:
        print(f"Ошибка при обновлении email: {e}")
        raise

def add_product(session: Session, name: str, price: Decimal) -> Product:
    """
    Сценарий 3: Атомарное добавление нового продукта.
    """
    try:
        with session.begin():
            new_product = Product(product_name=name, price=price)
            session.add(new_product)
        print(f"Продукт '{name}' добавлен с id={new_product.product_id}")
        return new_product

    except SQLAlchemyError as e:
        print(f"Ошибка при добавлении продукта: {e}")
        raise

# Демонстрация работы

if __name__ == "__main__":
    import os
    DB_USER = os.getenv('DB_USER', 'postgres')
    DB_PASS = os.getenv('DB_PASS', 'postgres')
    DB_HOST = os.getenv('DB_HOST', 'db')
    DB_NAME = os.getenv('DB_NAME', 'shop')
    DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:5432/{DB_NAME}"

    engine = create_engine(DATABASE_URL, echo=True)
    Base.metadata.create_all(engine)

    SessionLocal = sessionmaker(bind=engine)

    with SessionLocal() as init_session:
        with init_session.begin():
            if init_session.query(Customer).count() == 0:
                init_session.add_all([
                    Customer(first_name="Иван", last_name="Петров", email="ivan@example.com"),
                    Product(product_name="Ноутбук", price=Decimal("50000.00")),
                    Product(product_name="Мышь", price=Decimal("1500.00")),
                ])

    print("\n=== Сценарий 1: Создание заказа ===")
    with SessionLocal() as s1:
        items = [{'product_id': 1, 'quantity': 1}, {'product_id': 2, 'quantity': 2}]
        create_order(s1, customer_id=1, items_data=items)

    print("\n=== Сценарий 2: Обновление email ===")
    with SessionLocal() as s2:
        update_customer_email(s2, customer_id=1, new_email="new_ivan@example.com")

    print("\n=== Сценарий 3: Добавление продукта ===")
    with SessionLocal() as s3:
        add_product(s3, name="Клавиатура", price=Decimal("2500.00"))

    print("\n=== Все сценарии успешно выполнены ===")

    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        print("Завершение работы")