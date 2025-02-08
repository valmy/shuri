import typer
from gql import Client, gql
from gql.transport.aiohttp import AIOHTTPTransport
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
import json
import plotly.graph_objects as go
from plotly.subplots import make_subplots

load_dotenv()

app = typer.Typer()

@app.command()
def main(
    token_symbol: str = typer.Argument("WETH", help="Token symbol to chart (e.g. WBTC, WETH, LINK)")
):
    """
    Generate price charts for the specified token using data from The Graph.
    Saves both interactive HTML and static PNG versions of the chart.
    """
    # Convert token symbol to uppercase for consistency
    token_symbol = token_symbol.upper()
    
    subgraph_id = "5zvR82QoaXYFyDEKLZ9t6v9adgnptxYpKpSbxtgVENFV"
    api_key = os.getenv("API_KEY")
    if not api_key:
        raise ValueError("API_KEY environment variable not set")
    transport = AIOHTTPTransport(
        url=f"https://gateway.thegraph.com/api/{api_key}/subgraphs/id/{subgraph_id}"
    )

    # Create a GraphQL client using the defined transport
    client = Client(transport=transport)

    # Provide a GraphQL query for token data
    query = gql(
        """
        query getTokenData($symbol: String!, $skip: Int!) {
            tokens(
                first: 1
                where: { symbol: $symbol }
                orderBy: volume
                orderDirection: desc
            ) {
                id
                name
                tokenDayData(
                    first: 100
                    skip: $skip
                    orderBy: date
                    orderDirection: desc
                ) {
                    date
                    priceUSD
                    high
                    low
                    open
                    close
                    volume
                }
            }
        }
        """
    )

    # Execute the query
    variables = {
        "symbol": token_symbol,
        "skip": 0
    }
    
    result = client.execute(query, variable_values=variables)

    if not result["tokens"] or not result["tokens"][0]["tokenDayData"]:
        print(f"No data found for token {token_symbol}")
        return

    # Process the data
    token_data = result["tokens"][0]["tokenDayData"]

    # Print the symbol, id and name
    print(f"Symbol: {token_symbol}, ID: {result['tokens'][0]['id']}, Name: {result['tokens'][0]['name']}")
    
    # Prepare data for plotting
    dates = [datetime.fromtimestamp(int(day["date"])) for day in token_data]
    
    # Create the candlestick chart
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                       vertical_spacing=0.03, 
                       row_heights=[0.7, 0.3])

    fig.add_trace(go.Candlestick(
        x=dates,
        open=[float(day["open"]) for day in token_data],
        high=[float(day["high"]) for day in token_data],
        low=[float(day["low"]) for day in token_data],
        close=[float(day["close"]) for day in token_data],
        name="Price",
        increasing_line_color='#26A69A',    # Green for up candles
        decreasing_line_color='#EF5350'     # Red for down candles
    ), row=1, col=1)

    # Add volume bars
    fig.add_trace(go.Bar(
        x=dates,
        y=[float(day["volume"]) for day in token_data],
        name="Volume",
        marker_color='#5C6BC0'  # Blue for volume bars
    ), row=2, col=1)

    # Get current date for filenames
    current_date = datetime.now().strftime("%Y%m%d")

    # Update layout with dark theme
    fig.update_layout(
        title=f"{token_symbol}/USD Price Chart",
        yaxis_title="Price (USD)",
        yaxis2_title="Volume",
        xaxis_rangeslider_visible=False,
        height=800,
        template="plotly_dark",
        paper_bgcolor='black',
        plot_bgcolor='black',
        font=dict(color='white'),
    )

    # Additional style updates for dark theme
    fig.update_xaxes(gridcolor='#1f1f1f', zerolinecolor='#1f1f1f')
    fig.update_yaxes(gridcolor='#1f1f1f', zerolinecolor='#1f1f1f')

    # Save the interactive HTML chart
    html_filename = f"{token_symbol}_chart_{current_date}.html"
    fig.write_html(html_filename)
    print(f"Interactive chart has been saved to {html_filename}")

    # Save static PNG version
    png_filename = f"{token_symbol}_chart_{current_date}.png"
    fig.write_image(png_filename)
    print(f"Static chart has been saved to {png_filename}")


if __name__ == "__main__":
    app()
