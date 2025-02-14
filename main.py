import typer
from chart import chart
from top import top

app = typer.Typer(help="Uniswap v3 token analytics tool")

# Register commands
app.command("chart")(chart)
app.command("top")(top)

if __name__ == "__main__":
    app()
