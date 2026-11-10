import asyncio, sys
from . import ingest, transform, publish

async def main():
    while True:
        for step in (ingest.run_once, transform.run_once, publish.run_once):
            try:
                await step()
            except Exception as e:
                print(f"{step.__module__}: {e}", file=sys.stderr)
        await asyncio.sleep(20)

if __name__ == "__main__":
    asyncio.run(main())
