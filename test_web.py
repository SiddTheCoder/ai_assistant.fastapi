from app.tools.web import search,scrape
from app.features.search_web.fetch_web_result import fetch_web_results_with_selenium,fetch_bing_results_with_selenium
import asyncio
import json

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

async def main ():
  web_search_tool = search.WebSearchTool()
  result = await web_search_tool.execute({"query": "who is siddthecoder", "max_results": 4})
  print(json.dumps(result.data, indent=2))
  # result = web_scrape("https://www.github.com/siddthecoder")
  web_scraper = scrape.WebScraper(max_chars=5000)
  result = web_scraper.scrape_urls(urls = [
        "https://www.github.com/siddthecoder",
       "https://www.siddhantyadav.com.np/",
       "https://www.instragram.com/siddthecoder/",
    ])
  print(json.dumps(result, indent=2))

if __name__ == "__main__":
  asyncio.run(main()) 
 