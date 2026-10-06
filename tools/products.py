import os
import serpapi
from dotenv import load_dotenv

load_dotenv()


def search_products(query: str):
    """Search Google Shopping and return a few current products."""
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
