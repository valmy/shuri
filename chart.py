import typer
from gql import gql
from datetime import datetime, timedelta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from utils import get_client, normalize_token_symbol

def chart(
    token_symbol: str = typer.Argument("WETH", help="Token symbol to chart (e.g. WBTC, WETH, LINK)"),
    timeframe: str = typer.Option("1d", "--timeframe", "-t", 
                                help="Timeframe for the chart (1h, 2h, 4h, 8h, 12h, 16h, 1d, 2d)",
                                callback=lambda x: x.lower()),
    points: int = typer.Option(100, "--points", "-p", 
                             help="Number of data points to fetch")
):
    """
    Generate price charts for the specified token using data from The Graph.
    Saves both interactive HTML and static PNG versions of the chart.

    Args:
        token_symbol: Token symbol to chart (e.g. WBTC, WETH, LINK)
        timeframe: Timeframe for the chart (1h, 2h, 4h, 8h, 12h, 16h, 1d, 2d)
        points: Number of data points to fetch (default: 100)
    """
    # Validate timeframe
    valid_timeframes = {
        "1h": 60, "2h": 120, "4h": 240, "8h": 480,
        "12h": 720, "16h": 960, "1d": 1440, "2d": 2880
    }
    if timeframe not in valid_timeframes:
        raise typer.BadParameter(f"Invalid timeframe. Choose from: {', '.join(valid_timeframes.keys())}")

    # Validate points
    if points < 1:
        raise typer.BadParameter("Points must be greater than 0")
    if points > 1000:
        raise typer.BadParameter("Points must not exceed 1000 to avoid overwhelming the API")

    # Convert token symbol to uppercase and normalize
    token_symbol = normalize_token_symbol(token_symbol)
    
    # Get GraphQL client
    client = get_client()

    # Calculate time range based on timeframe
    end_time = datetime.now()
    minutes = valid_timeframes[timeframe]
    points_needed = points
    start_time = end_time - timedelta(minutes=minutes * points_needed)
    
    # Determine if we should use hourly or daily data
    use_hourly = timeframe in {"1h", "2h", "4h", "8h", "12h", "16h"}

    # First get the token ID
    token_query = gql(
        """
        query getTokenId($symbol: String!) {
            tokens(
                first: 1
                where: { symbol: $symbol }
                orderBy: volume
                orderDirection: desc
            ) {
                id
                name
            }
        }
        """
    )

    # Get token ID first
    token_result = client.execute(token_query, variable_values={"symbol": token_symbol})
    
    if not token_result["tokens"]:
        print(f"No token found with symbol {token_symbol}")
        return

    token = token_result["tokens"][0]
    token_id = token["id"]
    print(f"Symbol: {token_symbol}, ID: {token_id}, Name: {token['name']}")

    # Now query the hourly or daily data
    if use_hourly:
        data_query = gql(
            """
            query getHourlyData($token: String!, $points: Int!) {
                tokenHourDatas(
                    first: $points
                    orderBy: periodStartUnix
                    orderDirection: desc
                    where: { token: $token }
                ) {
                    periodStartUnix
                    high
                    low
                    open
                    close
                    volume
                }
            }
            """
        )
        variables = {
            "token": token_id,
            "points": points_needed
        }
    else:
        data_query = gql(
            """
            query getDailyData($token: String!, $points: Int!) {
                tokenDayDatas(
                    first: $points
                    orderBy: date
                    orderDirection: desc
                    where: { token: $token }
                ) {
                    date
                    high
                    low
                    open
                    close
                    volume
                }
            }
            """
        )
        variables = {
            "token": token_id,
            "points": points_needed
        }

    # Execute the query
    result = client.execute(data_query, variable_values=variables)
    
    # Get the appropriate data field
    data_field = "tokenHourDatas" if use_hourly else "tokenDayDatas"
    
    if not result[data_field]:
        print(f"No data found for token {token_symbol}")
        return

    # Process the data
    token_data = result[data_field]
    
    # Convert timestamps and extract price data
    dates = []
    highs = []
    lows = []
    opens = []
    closes = []
    volumes = []

    for data_point in token_data:
        # Handle different timestamp fields
        timestamp = data_point["periodStartUnix"] if use_hourly else data_point["date"]
        date = datetime.fromtimestamp(int(timestamp))
        
        if start_time <= date <= end_time:
            dates.append(date)
            highs.append(float(data_point["high"]))
            lows.append(float(data_point["low"]))
            opens.append(float(data_point["open"]))
            closes.append(float(data_point["close"]))
            volumes.append(float(data_point["volume"]))

    if not dates:
        print(f"No data found for the specified timeframe")
        return

    # Create the candlestick chart
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                       vertical_spacing=0.03, 
                       row_heights=[0.7, 0.3])

    fig.add_trace(go.Candlestick(
        x=dates,
        open=opens,
        high=highs,
        low=lows,
        close=closes,
        name="Price",
        increasing_line_color='#26A69A',    # Green for up candles
        decreasing_line_color='#EF5350'     # Red for down candles
    ), row=1, col=1)

    # Add volume bars
    fig.add_trace(go.Bar(
        x=dates,
        y=volumes,
        name="Volume",
        marker_color='#5C6BC0'  # Blue for volume bars
    ), row=2, col=1)

    # Update layout for a dark theme
    fig.update_layout(
        template='plotly_dark',
        title=f"{token_symbol} Price Chart",
        yaxis_title="Price (USD)",
        yaxis2_title="Volume (USD)",
        showlegend=False
    )

    # Customize grid
    fig.update_xaxes(gridcolor='#1f1f1f', zerolinecolor='#1f1f1f')
    fig.update_yaxes(gridcolor='#1f1f1f', zerolinecolor='#1f1f1f')

    # Get current date for filenames
    current_date = datetime.now().strftime("%Y%m%d")

    # Save the interactive HTML chart
    html_filename = f"{token_symbol}_chart_{timeframe}_{current_date}.html"
    png_filename = f"{token_symbol}_chart_{timeframe}_{current_date}.png"

    fig.write_html(html_filename)
    print(f"Interactive chart has been saved to {html_filename}")

    # Save a static PNG version
    fig.write_image(png_filename)
    print(f"Static chart has been saved to {png_filename}")
