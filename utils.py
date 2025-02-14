from gql import Client
from gql.transport.aiohttp import AIOHTTPTransport
import os
from dotenv import load_dotenv

def get_client():
    """Get the GraphQL client with proper configuration."""
    load_dotenv()
    
    subgraph_id = "5zvR82QoaXYFyDEKLZ9t6v9adgnptxYpKpSbxtgVENFV"
    api_key = os.getenv("API_KEY")
    if not api_key:
        raise ValueError("API_KEY environment variable not set")
        
    transport = AIOHTTPTransport(
        url=f"https://gateway.thegraph.com/api/{api_key}/subgraphs/id/{subgraph_id}"
    )
    
    return Client(transport=transport)

def normalize_token_symbol(symbol: str) -> str:
    """Normalize token symbols (e.g., ETH -> WETH)."""
    symbol = symbol.upper()
    if symbol == "BTC":
        return "WBTC"
    elif symbol == "ETH":
        return "WETH"
    return symbol
