from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
import mcp.server.stdio
import asyncio
import os
from .tantivy_search_agent import TantivySearchAgent
import json

# Initialize TantivySearchAgent with the index path
current_dir = os.path.dirname(os.path.abspath(__file__))
index_path = os.path.join(os.path.dirname(os.path.dirname(current_dir)), "index")
search_agent = TantivySearchAgent(index_path)
if not search_agent.validate_index():
    raise ValueError("failed to open index")

server = Server("jewish_library")



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
                                     '- Phrase search ("exact phrase")\n' +
                                     "- Wildcards (?, *)",
                    },
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="hello",
            description="A simple test tool that returns a greeting",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "The name to greet",
                    },
                },
                "required": ["name"],
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
        try:
            query = arguments.get("query")
            if not query:
                raise ValueError("Missing query parameter")
            
            results = await search_agent.search(query, num_results=1)
            if not results or len(results) == 0:
                return [types.TextContent(
                    type="text",
                    text="No results found"
                )]
            formatted_results = []
            for result in results:
                formatted_results.append(f"Text: {result.get('text', 'N/A')}\nReference: {result.get('reference', 'N/A')}")
            return [
                types.TextContent(
                    type="text",
                    text="\n\n".join(formatted_results)
                )
            ]
        except Exception as err:            
            return [types.TextContent(
                    type="text",
                    text=f"Error: {str(err)}"
                )]
    
    elif name == "hello":
        try:
            name_param = arguments.get("name")
            if not name_param:
                raise ValueError("Missing name parameter")
            
            return [types.TextContent(
                type="text",
                text=f"Hello, {name_param}! This is a test message from the Jewish Library server."
            )]
        except Exception as err:
            return [types.TextContent(
                type="text",
                text=f"Error: {str(err)}"
            )]
            
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
