from agents import Agent
from tools import find_products, view_purchases

alternatives_agent = Agent(
    name="Alternatives",
    instructions="""
    Find a similar or cheaper alternative to a product.

    You decide which tools this goal needs. You can use a tool more than once.
    Read their purchase history when the product comes from something they bought.
    Search for current alternatives that match their budget, brand, or similarity request.
    Say what you compared against, and why the alternative fits.
    Only recommend products returned by the search.
    """,
    tools=[view_purchases, find_products],
)
