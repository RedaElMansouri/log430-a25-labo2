# Labo 01 — Rapport

<img src="https://upload.wikimedia.org/wikipedia/commons/2/2a/Ets_quebec_logo.png" width="250"> \
Reda El Mansouri ELMR90070104 \
Rapport de laboratoire \
LOG430 — Architecture logicielle \
2025-09-19 \
École de technologie supérieure

## Questions

####  Question 1 : Lorsque l'application démarre, la synchronisation entre Redis et MySQL est-elle initialement déclenchée par quelle méthode ? Veuillez inclure le code pour illustrer votre réponse.

Lorsque l’application démarre, la synchronisation entre Redis et MySQL est déclenchée par la méthode **sync_all_orders_to_redis()**. Cette méthode, définie dans commands/write_order.py, charge toutes les commandes présentes dans MySQL et les insère dans Redis.
Pour éviter une surcharge inutile, elle utilise un flag (orders:sync_done) afin de s’exécuter uniquement une seule fois au démarrage. Voici le code illustration de ma réponse: 
```py
def sync_all_orders_to_redis():
    """ Sync orders from MySQL to Redis """
    
    r = get_redis_conn()
    sync_flag = 'orders:sync_done'
    try:
        if r.exists(sync_flag):
            orders_in_redis = r.keys("order:*")
            print("Redis already contains orders or sync already performed, no need to sync!")
            return len(orders_in_redis)

        orders_in_redis = r.keys("order:*")
        if len(orders_in_redis) > 0:
            r.set(sync_flag, 1)
            print("Redis already contains orders, marking sync as done.")
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

```

#### Question 2 : Quelles méthodes avez-vous utilisées pour lire des données à partir de Redis ? Veuillez inclure le code pour illustrer votre réponse.
Pour lire les données à partir de Redis, nous avons utilisé principalement deux méthodes :

- **r.keys("order:*")** pour obtenir la liste des commandes,

- **r.hgetall(key)** pour lire les champs stockés dans chaque commande.

- **json.loads()** → pour décoder les champs JSON tels que la liste des items.

Ainsi, les commandes sont entièrement lues depuis Redis sans interroger MySQL.

Exemple d'implémentation: 
```py
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
```

Pour ajouter des données dans Redis, nous avons utilisé les méthodes hset, incrby et incrbyfloat.
Elles permettent respectivement d’insérer une commande sous forme de hash et de mettre à jour les ventes par produit. Voici son implémentation: 
```py
def add_order_to_redis(order_id, user_id, total_amount, items):
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

```
#### Question 4 : Quelles méthodes avez-vous utilisées pour supprimer des données dans Redis ? Veuillez inclure le code pour illustrer votre réponse.

Lorsque nous supprimons une commande dans MySQL, nous devons également la supprimer dans Redis pour que les deux sources restent cohérentes.

Pour cela, nous avons utilisé la méthode r.delete(key) qui supprime complètement la clé correspondant à la commande dans Redis.

- **r.delete(key)** supprime la commande identifiée par order:*{order_id}*.

Cela garantit que Redis ne contient plus de données obsolètes après une suppression dans MySQL. Voici son implémentation: 
```py
def delete_order_from_redis(order_id):
    """Delete order from Redis"""
    r = get_redis_conn()
    key = f"order:{order_id}"
    r.delete(key)
```

#### Question 5 : Si nous souhaitions créer un rapport similaire, mais présentant les produits les plus vendus, les informations dont nous disposons actuellement dans Redis sont-elles suffisantes, ou devrions-nous chercher dans les tables sur MySQL ? Si nécessaire, quelles informations devrions-nous ajouter à Redis ? Veuillez inclure le code pour illustrer votre réponse.

Les informations actuellement stockées dans Redis sont suffisantes pour créer un rapport des produits les plus vendus, car chaque produit a un compteur mis à jour lors de l’ajout d’une commande. Il n’est donc pas nécessaire de consulter MySQL pour ce rapport. Voici l'implémentation qui appui mon point : 
```py
from db import get_redis_conn

def get_best_sellers(limit=10):
    r = get_redis_conn()
    keys = r.keys("product:*")

    result = []
    for k in keys:
        parts = k.split(":")
        pid = int(parts[-1])
        qty = r.get(k)
        qty = float(qty) if qty is not None else 0.0
        result.append((pid, qty))

    result = sorted(result, key=lambda item: item[1], reverse=True)
    return result[:limit]

```
## Observations additionnelles

Je n’ai pas pu mettre en place un déploiement complet en CI/CD, car je n’avais pas accès à l’adresse IP de ma machine virtuelle.

Cependant, si j’avais eu cet accès, j’aurais configuré un runner self-hosted directement sur ma machine (comme vu au laboratoire 0). Le pipeline GitHub Actions aurait alors suivi les étapes classiques d’intégration continue (CI) :

checkout du dépôt,

installation de Python,

création du fichier .env,

installation des dépendances,

démarrage des conteneurs nécessaires (MySQL, MongoDB),

attente de l’initialisation des services,

exécution des tests unitaires avec pytest,

et enfin, nettoyage avec docker compose down -v.

Ainsi, avec l’accès à la VM et un runner self-hosted configuré, j’aurais pu non seulement exécuter mes tests (CI), mais aussi automatiser le déploiement de l’application (CD).