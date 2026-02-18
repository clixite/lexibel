"""Infrastructure connectivity test script."""
import asyncio
import sys
import os

# Set test environment variables
os.environ.setdefault("NEO4J_PASSWORD", "testpass123")
os.environ.setdefault("QDRANT_URL", "http://localhost:6333")

async def test_neo4j():
    """Test Neo4j connectivity."""
    try:
        from apps.api.services.neo4j_client import get_neo4j_client
        print(f"[*] Connecting to Neo4j at {os.getenv('NEO4J_URI', 'bolt://localhost:7687')}...")
        client = await get_neo4j_client()
        print("[*] Neo4j client obtained, checking health...")
        health = await client.health_check()
        if health:
            print("[+] Neo4j: Connected and healthy")
            return True
        else:
            print("[-] Neo4j: Health check failed")
            return False
    except Exception as e:
        print(f"[-] Neo4j: Connection error - {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_qdrant():
    """Test Qdrant connectivity."""
    try:
        from apps.api.services.qdrant_client import get_qdrant_client
        print(f"[*] Connecting to Qdrant at {os.getenv('QDRANT_URL', 'http://localhost:6333')}...")
        client = await get_qdrant_client()
        print("[*] Qdrant client obtained, checking health...")
        health = await client.health_check()
        if health:
            print("[+] Qdrant: Connected and healthy")
            return True
        else:
            print("[-] Qdrant: Health check failed")
            return False
    except Exception as e:
        print(f"[-] Qdrant: Connection error - {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run all infrastructure tests."""
    print("[*] Testing Infrastructure Connectivity\n")

    results = await asyncio.gather(
        test_neo4j(),
        test_qdrant(),
        return_exceptions=True
    )

    success_count = sum(1 for r in results if r is True)
    total = len(results)

    print(f"\n[*] Results: {success_count}/{total} services healthy")

    if success_count == total:
        print("[+] All infrastructure services operational!")
        sys.exit(0)
    else:
        print("[!] Some services need attention")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
