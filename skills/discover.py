from agents import Agent
from tools import find_products, view_purchases

discover_agent = Agent(
    name="Discovery",
    instructions="""
    Find products that match a category or constraint, such as a budget.

    You decide which tools this goal needs. You can search more than once if the first results do not fit.
    Read their purchase history only when it would narrow the search.
    Only suggest products returned by the search, and say briefly why each one fits the constraint.
    """,
    tools=[view_purchases, find_products],
)
