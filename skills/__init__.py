from skills.alternatives import alternatives_agent
from skills.compare import compare_agent
from skills.discover import discover_agent
from skills.recommend import recommend_agent

recommend_products = recommend_agent.as_tool(
    tool_name="recommend_products",
    tool_description=(
        "Recommend products for a shopping goal. "
        "Use this when the user wants a recommendation, including one based on past purchases, "
        "a category, or a budget. This skill decides whether to read purchase history and search."
    ),
)

compare_products = compare_agent.as_tool(
    tool_name="compare_products",
    tool_description=(
        "Compare a few products and pick the best one for the user. "
        "Use this when the user asks which option is better or wants the differences explained."
    ),
)

find_alternatives = alternatives_agent.as_tool(
    tool_name="find_alternatives",
    tool_description=(
        "Find a similar or cheaper alternative to a product, including one the user bought before. "
        "This skill decides whether to read purchase history and search."
    ),
)

discover_products = discover_agent.as_tool(
    tool_name="discover_products",
    tool_description=(
        "Find current products for a category or constraint, such as sunscreen under $30. "
        "Use this for product discovery that is not mainly a comparison or a past-purchase recommendation."
    ),
)
