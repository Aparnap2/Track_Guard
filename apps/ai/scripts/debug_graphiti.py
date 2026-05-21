import asyncio
from dotenv import load_dotenv
load_dotenv()

import os

async def debug():
    print("=== ENV CHECK ===")
    print(f"NEO4J_URI:      {os.environ.get('NEO4J_URI', 'NOT SET')}")
    print(f"NEO4J_USER:     {os.environ.get('NEO4J_USER', 'NOT SET')}")
    print(f"NEO4J_PASSWORD: {'SET' if os.environ.get('NEO4J_PASSWORD') else 'NOT SET'}")
    print(f"OLLAMA_BASE_URL:{os.environ.get('OLLAMA_BASE_URL', 'NOT SET')}")

    print("\n=== NEO4J DIRECT CONNECTION ===")
    try:
        from neo4j import AsyncGraphDatabase
        uri  = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
        user = os.environ.get("NEO4J_USER", "neo4j")
        pw   = os.environ.get("NEO4J_PASSWORD", "")
        driver = AsyncGraphDatabase.driver(uri, auth=(user, pw))
        async with driver.session() as session:
            result = await session.run("RETURN 1 AS n")
            record = await result.single()
            print(f"✅ Neo4j direct: RETURN 1 = {record['n']}")
        await driver.close()
    except Exception as e:
        print(f"❌ Neo4j direct connection failed: {e}")

    print("\n=== GRAPHITI CLIENT ===")
    try:
        from graphiti_core import Graphiti
        g = Graphiti(
            uri=os.environ["NEO4J_URI"],
            user=os.environ["NEO4J_USER"],
            password=os.environ["NEO4J_PASSWORD"]
        )
        await g.build_indices_and_constraints()
        print("✅ Graphiti client initialised")
        print("✅ Indices and constraints built")
    except Exception as e:
        print(f"❌ Graphiti init failed: {e}")

    print("\n=== OLLAMA EMBEDDING (nomic-embed-text) ===")
    try:
        import httpx
        base = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        r = httpx.post(
            f"{base}/api/embeddings",
            json={"model": "nomic-embed-text", "prompt": "test"},
            timeout=10.0
        )
        emb = r.json().get("embedding", [])
        print(f"✅ nomic-embed-text: {len(emb)}-dim embedding")
    except Exception as e:
        print(f"❌ Ollama embedding failed: {e}")

asyncio.run(debug())