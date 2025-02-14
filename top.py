import typer
from gql import gql
from datetime import datetime, timedelta
from utils import get_client

def top(
    limit: int = typer.Option(20, "--limit", "-l", help="Number of top tokens to show"),
    min_volume: float = typer.Option(1000, "--min-volume", "-m", help="Minimum volume in USD")
):
    """
    List top tokens by trading volume in the last 24 hours.
    Only shows tokens with volume greater than min_volume USD.
    """
    if limit < 1:
        raise typer.BadParameter("Limit must be greater than 0")
    if limit > 100:
        raise typer.BadParameter("Limit cannot exceed 100")
    
    client = get_client()
    
    # Calculate 24h ago timestamp
    end_time = datetime.now()
    start_time = end_time - timedelta(days=1)
    start_timestamp = int(start_time.timestamp())
    
    # Query top tokens
    query = gql(
        """
        query getTopTokens($minVolume: BigDecimal!, $timestamp: Int!, $limit: Int!) {
            tokens(
                first: $limit,
                where: { totalValueLockedUSD_gt: $minVolume }
            ) {
                id
                symbol
                name
                decimals
                volume
                volumeUSD
                totalValueLockedUSD
                tokenDayData(
                    first: 1
                    orderBy: date
                    orderDirection: desc
                    where: { date_gt: $timestamp }
                ) {
                    date
                    priceUSD
                    volume
                    volumeUSD
                }
            }
        }
        """
    )
    
    result = client.execute(query, variable_values={
        "minVolume": str(min_volume),
        "timestamp": start_timestamp,
        "limit": limit * 2  # Fetch more to account for tokens with no recent volume
    })
    
    if not result["tokens"]:
        print("No tokens found")
        return
        
    # Filter and sort tokens by 24h volume
    tokens = []
    for token in result["tokens"]:
        day_data = token["tokenDayData"][0] if token["tokenDayData"] else None
        if day_data:
            volume_24h = float(day_data["volumeUSD"])
            if volume_24h > 0:  # Only include tokens with non-zero volume
                tokens.append({
                    "symbol": token["symbol"],
                    "price": float(day_data["priceUSD"]),
                    "volume_24h": volume_24h,
                    "tvl": float(token["totalValueLockedUSD"])
                })
    
    # Sort by 24h volume and take top N
    tokens.sort(key=lambda x: x["volume_24h"], reverse=True)
    tokens = tokens[:limit]
        
    # Print header
    print(f"\nTop {limit} tokens by 24h volume:")
    print(f"{'Symbol':<10} {'Price (USD)':<15} {'24h Volume (USD)':<20} {'TVL (USD)':<15}")
    print("-" * 60)
    
    # Display results
    for token in tokens:
        symbol = token["symbol"]
        price = token["price"]
        volume_24h = token["volume_24h"]
        tvl = token["tvl"]
        
        # Format numbers
        price_str = f"${price:,.2f}"
        volume_str = f"${volume_24h:,.0f}"
        tvl_str = f"${tvl:,.0f}"
        
        print(f"{symbol:<10} {price_str:<15} {volume_str:<20} {tvl_str:<15}")
