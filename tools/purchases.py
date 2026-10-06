purchases = []


def add_purchase(product: str, price: float, store: str):
    """Save one purchase in the temporary list for this run."""
    purchase = {
        "product": product,
        "price": price,
        "store": store,
    }

    purchases.append(purchase)

    return {
        "success": True,
        "purchase": purchase,
    }


def get_purchases():
    """Read the purchase history saved in purchases.json."""
    import json

    with open("purchases.json", "r") as f:
        return json.load(f)
