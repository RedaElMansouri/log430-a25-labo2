"""
Orders (write-only model)
SPDX - License - Identifier: LGPL - 3.0 - or -later
Auteurs : Gabriel C. Ullmann, Fabio Petrillo, 2025
"""
from models.product import Product
from models.order_item import OrderItem
from models.order import Order
from queries.read_order import get_orders_from_mysql
from db import get_sqlalchemy_session, get_redis_conn
import json

def add_order(user_id: int, items: list):
    """Insert order with items in MySQL, keep Redis in sync"""
    if not user_id or not items:
        raise ValueError("Vous devez indiquer au moins 1 utilisateur et 1 item pour chaque commande.")

    try:
        product_ids = []
        for item in items:
            product_ids.append(int(item['product_id']))
    except Exception as e:
        print(e)
        raise ValueError(f"L'ID Article n'est pas valide: {item['product_id']}")
    session = get_sqlalchemy_session()

    try:
        products_query = session.query(Product).filter(Product.id.in_(product_ids)).all()
        price_map = {product.id: product.price for product in products_query}
        total_amount = 0
        order_items_data = []
        
        for item in items:
            pid = int(item["product_id"])
            qty = float(item["quantity"])

            if not qty or qty <= 0:
                raise ValueError(f"Vous devez indiquer une quantité superieure à zéro.")

            if pid not in price_map:
                raise ValueError(f"Article ID {pid} n'est pas dans la base de données.")

            unit_price = price_map[pid]
            total_amount += unit_price * qty
            order_items_data.append({
                'product_id': pid,
                'quantity': qty,
                'unit_price': unit_price
            })
        
        new_order = Order(user_id=user_id, total_amount=total_amount)
        session.add(new_order)
        session.flush() 
        
        order_id = new_order.id

        for item_data in order_items_data:
            order_item = OrderItem(
                order_id=order_id,
                product_id=item_data['product_id'],
                quantity=item_data['quantity'],
                unit_price=item_data['unit_price']
            )
            session.add(order_item)

        session.commit()

        # TODO: ajouter la commande à Redis
        add_order_to_redis(order_id, user_id, total_amount, items)

        return order_id

    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def delete_order(order_id: int):
    """Delete order in MySQL, keep Redis in sync"""
    session = get_sqlalchemy_session()
    committed = False
    order = None
    try:
        order = session.query(Order).filter(Order.id == order_id).first()

        if order:
            session.delete(order)
            session.commit()
            committed = True
            return 1
        else:
            return 0
    except Exception as e:
        session.rollback()
        raise e
    finally:
        try:
            session.close()
        except Exception:
            pass

        if committed and order:
            try:
                delete_order_from_redis(order_id)
            except Exception as e:
                print(f"Failed to delete order from redis after mysql commit: {e}")

def add_order_to_redis(order_id, user_id, total_amount, items):
    """Insert order to Redis"""
    r = get_redis_conn()
    key = f"order:{order_id}"
    r.hset(key, mapping={
        'id': int(order_id),
        'user_id': int(user_id),
        'total_amount': float(total_amount),
        'items': json.dumps(items)
    })

    for item in items:
        pid = int(item.get('product_id'))
        qty = item.get('quantity')
        q_int = int(float(qty))
        if float(qty) == float(q_int):
            r.incrby(f"product:{pid}", q_int)
        else:
            r.incrbyfloat(f"product:{pid}", float(qty))

def delete_order_from_redis(order_id):
    """Delete order from Redis"""
    r = get_redis_conn()
    key = f"order:{order_id}"
    r.delete(key)

def sync_all_orders_to_redis():
    """ Sync orders from MySQL to Redis """
    
    r = get_redis_conn()
    sync_flag = 'orders:sync_done'
    try:
        if r.exists(sync_flag):
            orders_in_redis = r.keys(f"order:*")
            print('Redis already contains orders or sync already performed, no need to sync!')
            return len(orders_in_redis)

        orders_in_redis = r.keys(f"order:*")
        if len(orders_in_redis) > 0:
            r.set(sync_flag, 1)
            print('Redis already contains orders, marking sync as done.')
            return len(orders_in_redis)

        orders_from_mysql = get_orders_from_mysql()
        rows_added = 0
        for order in orders_from_mysql:
            items = []
            for oi in getattr(order, 'order_items', []) or []:
                items.append({
                    'product_id': int(oi.product_id),
                    'quantity': float(oi.quantity),
                    'unit_price': float(oi.unit_price)
                })

            add_order_to_redis(order.id, order.user_id, order.total_amount, items)
            rows_added += 1

        r.set(sync_flag, 1)

        return rows_added
    except Exception as e:
        print(e)
        return 0