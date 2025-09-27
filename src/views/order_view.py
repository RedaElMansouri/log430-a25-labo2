"""
Order view
SPDX - License - Identifier: LGPL - 3.0 - or -later
Auteurs : Gabriel C. Ullmann, Fabio Petrillo, 2025
"""
import numbers
from views.template_view import get_template, get_param
from controllers.order_controller import create_order, delete_order, list_orders_from_redis
from controllers.product_controller import list_products
from controllers.user_controller import list_users

def show_order_form():
    """ Show order form and list """
    orders = list_orders_from_redis(10)
    products = list_products(99)
    users = list_users(99)
    order_rows = [f"""
            <tr>
                <td>{order.id}</td>
                <td>${order.total_amount}</td>
                <td><a href="/orders/remove/{order.id}">Supprimer</a></td>
            </tr> """ for order in orders]
    user_rows = [f"""<option key={user.id} value={user.id}>{user.name}</option>""" for user in users]
    product_rows = [f"""<option key={product.id} value={product.id}>{product.name} (${product.price})</option>""" for product in products]
    return get_template(f"""
        <h2>Commandes</h2>
        <p>Voici les 10 derniers enregistrements :</p>
        <table class="table">
            <tr>
                <th>ID</th> 
                <th>Total</th> 
                <th>Actions</th> 
            </tr>  
            {" ".join(order_rows)}
        </table>
        <h2>Enregistrement</h2>
        <form method="POST" action="/orders/add">
            <div class="mb-3">
                <label class="form-label">Utilisateur</label>
                <select class="form-control" name="user_id" required>
                    {" ".join(user_rows)}
                </select>
            </div>
            <div class="mb-3">
                <label class="form-label">Article</label>
                <select class="form-control" name="product_id" required>
                    {" ".join(product_rows)}
                </select>
            </div>
            <div class="mb-3">
                <label class="form-label">Quantité</label>
                <input class="form-control" type="number" name="quantity" step="1" value="1" min="1" max="999" required>
            </div>
            <button type="submit" class="btn btn-primary">Enregistrer</button>
        </form>
    """)

def register_order(params):
    """ Add an order based on given params """
    if len(params.keys()):
        user_id = get_param(params, "user_id")
        product_id = get_param(params, "product_id")
        quantity = get_param(params, "quantity")
        items = [
            {'product_id': product_id, 'quantity': quantity}
        ]
        result = create_order(user_id, items)
    else: 
        return get_template(f"""
                <h2>Erreur</h2>
                <code>La requête est vide</code>
            """)

    if isinstance(result, numbers.Number):
        return get_template(f"""
                <h2>Information: la commande {result} a été ajoutée.</h2>
                <a href="/orders">← Retourner à la page des commandes</a>
            """)
    else:
        return get_template(f"""
                <h2>Erreur</h2>
                <code>{result}</code>
            """)
    
def remove_order(order_id):
    """ Remove an order with the given ID """
    result = delete_order(order_id)
    if result:
        return get_template(f"""
            <h2>Information: la commande {order_id} a été supprimée.</h2>
            <a href="/orders">← Retourner à la page des commandes</a>
        """)
    else:
        return get_template(f"""
                <h2>Erreur</h2>
                <code>{result}</code>
            """)