import json
import time
import requests


URL = "http://localhost:8000/moderation/check"

HEADERS = {
    "x-internal-secret": "ml_secret_key"
}


def run_test():

    with open(
        "tests/test_dataset.json",
        "r",
        encoding="utf-8"
    ) as f:

        dataset = json.load(f)

    total = len(dataset)

    correct = 0

    latency_list = []

    for item in dataset:

        text = item["text"]

        expected = item["expected"]

        start = time.time()

        response = requests.post(
            URL,
            json={
                "text": text,
                "stopwords": [],
                "streamer_id": "test_streamer",
            },
            headers=HEADERS,
        )

        latency = time.time() - start

        latency_list.append(latency)

        result = response.json()

        predicted = "toxic" if result.get("verdict") == "blocked" else "ok"

        if predicted == expected:
            correct += 1

        print("Text:", text)
        print("Expected:", expected)
        print("Predicted:", predicted)
        print("Verdict:", result.get("verdict"))
        print("Toxicity score:", result.get("toxicity_score"))
        print("Latency:", latency)

    accuracy = correct / total

    avg_latency = sum(latency_list) / len(latency_list)

    print("\nRESULT")
    print("Accuracy:", accuracy)
    print("Avg latency:", avg_latency)


if __name__ == "__main__":
    run_test()
