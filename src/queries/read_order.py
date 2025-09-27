"""
Orders (read-only model)
SPDX - License - Identifier: LGPL - 3.0 - or -later
Auteurs : Gabriel C. Ullmann, Fabio Petrillo, 2025
"""

from db import get_sqlalchemy_session, get_redis_conn
from sqlalchemy import desc
from models.order import Order
import json
from types import SimpleNamespace
from collections import defaultdict

def get_order_by_id(order_id):
    """Get order by ID from Redis"""
    r = get_redis_conn()
    return r.hgetall(order_id)

def get_orders_from_mysql(limit=9999):
    """Get last X orders"""
    session = get_sqlalchemy_session()
    return session.query(Order).order_by(desc(Order.id)).limit(limit).all()

def get_orders_from_redis(limit=9999):
    """Get last X orders"""
    r = get_redis_conn()
    keys = r.keys("order:*")

    ids = []
    for k in keys:
        try:
            parts = k.split(":")
            ids.append(int(parts[-1]))
        except Exception:
            continue

    ids = sorted(ids, reverse=True)[:limit]
    orders = []
    for oid in ids:
        key = f"order:{oid}"
        h = r.hgetall(key)
        if not h:
            continue
        items = []
        if h.get('items'):
            items = json.loads(h.get('items'))

            order_obj = SimpleNamespace(
                id=int(h.get('id', oid)),
                user_id=int(h.get('user_id', 0)) if h.get('user_id') is not None else 0,
                total_amount=float(h.get('total_amount', 0.0)),
                items=items
            )
            orders.append(order_obj)

    return orders

def get_highest_spending_users():
    """Get top users by total spending (read from Redis orders).

    Returns a list of tuples: (user_id, total_spent) sorted by total_spent desc (top first).
    """
    orders = get_orders_from_redis(limit=99999)

    expenses_by_user = defaultdict(float)
    for order in orders:
        uid = int(getattr(order, 'user_id', 0) or 0)
        total = float(getattr(order, 'total_amount', 0.0) or 0.0)
        expenses_by_user[uid] += total

    highest_spending_users = sorted(expenses_by_user.items(), key=lambda item: item[1], reverse=True)
    return highest_spending_users[:10]

def get_best_sellers(limit=10):
    r = get_redis_conn()
    keys = r.keys('product:*')

    result = []
    for k in keys:
            parts = k.split(':')
            pid = int(parts[-1])
            val = r.get(k)
            qty = float(val) if val is not None else 0.0
            result.append((pid, qty))

    result = sorted(result, key=lambda item: item[1], reverse=True)
    return result[:limit]