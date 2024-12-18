from typing import Any

import httpx
from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
import mcp.server.stdio
import asyncio
import os
from .tantivy_search_agent import TantivySearchAgent

# Initialize TantivySearchAgent with the index path
current_dir = os.path.dirname(os.path.abspath(__file__))
index_path = os.path.join(os.path.dirname(os.path.dirname(current_dir)), "index")
search_agent = TantivySearchAgent(index_path)

server = Server("jewish_library")

async def search_jewish_library(query: str) -> list[dict]:
    """Search the Jewish library using TantivySearchAgent"""
    results = search_agent.search(query)
    return results

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """
    List available tools.
    Each tool specifies its arguments using JSON Schema validation.
    """
    return [
        types.Tool(
            name="full_text_search",
            description="Full text searching in the jewish library",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The query to search for. Supports advanced query syntax including:\n" + 
                                     "- Field-specific search (text:term, reference:term, topics:term)\n" +
                                     "- Boolean operators (AND, OR)\n" +
                                     "- Required/excluded terms (+term, -term)\n" +
                                     "- Phrase search ('exact phrase')\n" +
                                     "- Wildcards (?, *)",
                    },
                },
                "required": ["query"],
            },
        ),
    ]

@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """
    Handle tool execution requests.
    Tools can search the Jewish library and return formatted results.
    """
    if not arguments:
        raise ValueError("Missing arguments")
  
    if name == "full_text_search":
        query = arguments.get("query")
        if not query:
            raise ValueError("Missing query parameter")
        
        results = await search_jewish_library(query)
        if not results:
            return [types.TextContent(
                type="text",
                text="No results found"
            )]
        
        # Format results into readable text
        results_text = "Search Results:\n\n"
        for i, result in enumerate(results, 1):
            results_text += f"Result {i}:\n"
            if result.get("reference"):
                results_text += f"Reference: {result['reference']}\n"
            if result.get("topics"):
                results_text += f"Topics: {result['topics']}\n"
            results_text += "Highlights:\n"
            for highlight in result["highlights"]:
                results_text += f"  {highlight}\n"
            results_text += f"Score: {result['score']:.2f}\n"
            results_text += "-" * 80 + "\n\n"

        return [
            types.TextContent(
                type="text",
                text=results_text
            )
        ]
    else:
        raise ValueError(f"Unknown tool: {name}")
    
async def main():
    # Run the server using stdin/stdout streams
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="jewish_library",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())
