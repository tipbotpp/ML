import asyncio

from app.services.latency import LatencyTest


DATASET = [
    "Спасибо за донат",
    "Лучший стример",
    "Привет чат",
    "Спасибо за стрим"
] * 20


async def main():

    tester = LatencyTest(
        url="http://localhost:8000/generate/audio",
        api_key="ml_secret_key"
    )

    result = await tester.run(DATASET)

    print(result)


asyncio.run(main())