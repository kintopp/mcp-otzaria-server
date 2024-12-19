from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
import mcp.server.stdio
import asyncio
import os
import logging
import sys
import json
from .tantivy_search_agent import TantivySearchAgent

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stderr),
        logging.FileHandler('jewish_library.log', encoding='utf-8')
    ]
)
logger = logging.getLogger('jewish_library')

# Initialize TantivySearchAgent with the index path
current_dir = os.path.dirname(os.path.abspath(__file__))
index_path = os.path.join(os.path.dirname(os.path.dirname(current_dir)), "index")
try:
    search_agent = TantivySearchAgent(index_path)
    logger.info("Search agent initialized")
except Exception as e:
    logger.error(f"Failed to initialize search agent: {e}")
    raise


server = Server("jewish_library")

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """
    List available tools.
    Each tool specifies its arguments using JSON Schema validation.
    """
    logger.debug("Handling list_tools request")
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
    logger.debug(f"Handling call_tool request for {name} with arguments {arguments}")
    
    try:
        if not arguments:
            raise ValueError("Missing arguments")
    
        if name == "full_text_search":
            try:
                query = arguments.get("query")
                if not query:
                    raise ValueError("Missing query parameter")
                
                logger.info(f"Searching with query: {query}")
                
                # Now do the actual search
                logger.debug(f"Executing search with query: {query}")
                results = await search_agent.search(query, num_results=1)
                logger.debug(f"Search completed: {len(results)} results")
                
                if not results or len(results) == 0:
                    logger.info("No results found")
                    return [types.TextContent(
                        type="text",
                        text="No results found"
                    )]
                
                formatted_results = []
                for result in results:
                    text = result.get('text', 'N/A')
                    reference = result.get('reference', 'N/A')
                    formatted_results.append(f"Text: {text}\nReference: {reference}")
                
                logger.info(f"Found {len(formatted_results)} results")
                response_text = "\n\n".join(formatted_results)
                logger.debug(f"Response text: {response_text}")
                
                return [
                    types.TextContent(
                        type="text",
                        text=response_text
                    )
                ]
            except Exception as err:
                logger.error(f"Search error: {err}", exc_info=True)
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
                    text=f"שלום, {name_param}! This is a test message from the Jewish Library server."
                )]
            except Exception as err:
                logger.error(f"Hello tool error: {err}", exc_info=True)
                return [types.TextContent(
                    type="text",
                    text=f"Error: {str(err)}"
                )]
                
        else:
            raise ValueError(f"Unknown tool: {name}")
            
    except Exception as e:
        logger.error(f"Tool execution error: {e}", exc_info=True)
        return [types.TextContent(
            type="text",
            text=f"Error: {str(e)}"
        )]
    
async def main():
    try:
        logger.info("Starting Jewish Library MCP server...")
            
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
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        raise
