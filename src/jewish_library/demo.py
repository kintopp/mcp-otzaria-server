from tantivy_search_agent import TantivySearchAgent
import os
import asyncio

# Initialize TantivySearchAgent with the index path
current_dir = os.path.dirname(os.path.abspath(__file__))
index_path = os.path.join(os.path.dirname(os.path.dirname(current_dir)), "index")
search_agent = TantivySearchAgent(index_path)

import os

async def print_search   ():
    results = await search_agent.search("גזלן קונה בשינוי")
    
    print(results)
    
async def main():
    print ("searchoing...")
    await print_search()
    
if __name__ == "__main__":
    asyncio.run(main())
    
