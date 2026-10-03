"""Run a selected PersonalOS MCP server over stdio."""

import argparse


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "server",
        choices=("renewal", "health", "market", "document"),
    )
    selected = parser.parse_args().server
    if selected == "renewal":
        from mcp_servers.renewal.server import run
    elif selected == "health":
        from mcp_servers.health.server import run
    elif selected == "market":
        from mcp_servers.market.server import run
    else:
        from mcp_servers.document.server import run
    run()


if __name__ == "__main__":
    main()
