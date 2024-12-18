from typing import List, Dict, Any, Optional
from tantivy import Index, Searcher
import logging
import os
import re
import asyncio
from functools import partial


class TantivySearchAgent:
    def __init__(self, index_path: str):
        """Initialize the Tantivy search agent with the index path"""
        self.index_path = index_path
        self.logger = logging.getLogger(__name__)
        self.index = None
        self.searcher = None
        try:
            self.index = Index.open(index_path)            
            self.searcher = self.index.searcher()
            self.logger.info(f"Successfully opened Tantivy index at {index_path}")
        except Exception as e:
            self.logger.error(f"Failed to open Tantivy index: {e}")
            raise

    async def _run_in_executor(self, func, *args):
        """Run blocking operations in a thread pool executor"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, partial(func, *args))

    async def search(self, query: str, num_results: int = 10) -> List[Dict[str, Any]]:
        """Search the Tantivy index with the given query using Tantivy's query syntax"""
        if not self.searcher:
            self.logger.error("Searcher not initialized")
            return []

        try:
            # Parse and execute the query
            try:
                # First try with lenient parsing in the thread pool
                query_parser = await self._run_in_executor(self.index.parse_query_lenient, query)
                search_results = await self._run_in_executor(
                    self.searcher.search, query_parser[0], num_results
                )
                search_results = search_results.hits
                
            except Exception as query_error:
                self.logger.error(f"Lenient query parsing failed: {query_error}")
                return []
            
            # Process results
            results = []
            for score, doc_address in search_results:
                # Get document in thread pool
                doc = await self._run_in_executor(self.searcher.doc, doc_address)
                text = doc.get_first("text")
                if not text:
                    continue
                
                # Extract highlighted snippets based on query terms
                # Remove special syntax for highlighting while preserving Hebrew
                highlight_terms = re.sub(
                    r'[:"()[\]{}^~*\\]|\b(AND|OR|NOT|TO|IN)\b|[-+]', 
                    ' ', 
                    query
                ).strip()
                highlight_terms = [term for term in highlight_terms.split() if len(term) > 1]
                
                # Create regex pattern for highlighting
                if highlight_terms:
                    # Escape regex special chars but preserve Hebrew
                    patterns = [re.escape(term) for term in highlight_terms]
                    pattern = '|'.join(patterns)
                    # Get surrounding context for matches
                    matches = list(re.finditer(pattern, text, re.IGNORECASE))
                    if matches:
                        highlights = []
                        for match in matches:
                            start = max(0, match.start() - 50)
                            end = min(len(text), match.end() + 50)
                            highlight = text[start:end]
                            if start > 0:
                                highlight = f"...{highlight}"
                            if end < len(text):
                                highlight = f"{highlight}..."
                            highlights.append(highlight)
                    else:
                        highlights = [text[:100] + "..." if len(text) > 100 else text]
                else:
                    highlights = [text[:100] + "..." if len(text) > 100 else text]
                
                result = {
                    "score": float(score),
                    "title": doc.get_first("title") or os.path.basename(doc.get_first("filePath") or ""),
                    "reference": doc.get_first("reference"),
                    "topics": doc.get_first("topics"),
                    "file_path": doc.get_first("filePath"),
                    "line_number": doc.get_first("segment"),
                    "is_pdf": doc.get_first("isPdf"),
                    "text": text,
                    "highlights": highlights
                }
                results.append(result)
            
            self.logger.info(f"Found {len(results)} results for query: {query}")
            return results
            
        except Exception as e:
            self.logger.error(f"Error during search: {str(e)}")
            return []

    async def validate_index(self) -> bool:
        """Validate that the index exists and is accessible"""
        if not self.searcher:
            return False
            
        try:
            # Parse and execute a simple query in the thread pool
            query_parser = await self._run_in_executor(self.index.parse_query, "*")
            await self._run_in_executor(self.searcher.search, query_parser, 1)
            return True
        except Exception as e:
            self.logger.error(f"Index validation failed: {e}")
            return False

    def __del__(self):
        """Cleanup resources"""
        if self.searcher:
            try:
                self.searcher.close()
            except:
                pass
