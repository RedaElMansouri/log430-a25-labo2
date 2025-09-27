"""
Report view
SPDX - License - Identifier: LGPL - 3.0 - or -later
Auteurs : Gabriel C. Ullmann, Fabio Petrillo, 2025
"""
from views.template_view import get_template, get_param

def show_highest_spending_users():
    """ Show report of highest spending users """
    content = """
    <h2>Les plus gros acheteurs</h2>
    <ul>
        <li>Ada Lovelace - 1999.99</li>
    </ul>
    """
    return get_template(content)

def show_best_sellers():
    """ Show report of best selling products """
    content = """
    <h2>Les articles les plus vendus</h2>
    <ul>
        <li>Laptop ABC - 1 vendu</li>
    </ul>
    """
    return get_template(content)