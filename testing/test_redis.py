from app.cache.redis import config
import asyncio
import json

async def main():
    doc = await config.get_last_n_messages("guest")
    print(json.dumps(doc, indent=2))
    # searched_doc = await config.semantic_search_messages("guest", "xavier acamdey was the best chocie of my life which i got by god", top_k=5)
    # print(json.dumps(searched_doc, indent=2))

    # user = await config.get_user_details("guest")
    # print(json.dumps(user, indent=2))

if __name__ == "__main__":
    asyncio.run(main())      