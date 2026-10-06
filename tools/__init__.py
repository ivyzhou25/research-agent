from agents import function_tool

from tools.products import search_products
from tools.purchases import add_purchase, get_purchases


@function_tool
def save_purchase(product: str, price: float, store: str):
    """Save a purchase the user just told you about."""
    return add_purchase(product, price, store)


@function_tool
def view_purchases():
    """Read the user's saved purchase history."""
    return get_purchases()


@function_tool
def find_products(query: str):
    """Search for current online products and prices."""
    return search_products(query)
