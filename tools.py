import json
import os
import serpapi
from dotenv import load_dotenv

load_dotenv()

purchases = []

def add_purchase(product: str, price: float, store: str):
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
    with open("purchases.json", "r") as f:
        return json.load(f)


def search_products(query: str):
    client = serpapi.Client(
        api_key=os.getenv("SERPAPI_KEY")
    )

    results = client.search({
        "engine": "google_shopping",
        "q": query,
        "location": "United States",
    })

    products = []

    for product in results.get("shopping_results", [])[:5]:
        products.append({
            "name": product.get("title"),
            "price": product.get("price"),
            "store": product.get("source"),
            "link": product.get("product_link"),
        })

    return products