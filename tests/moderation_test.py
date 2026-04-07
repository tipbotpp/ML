import json
import time
import requests


URL = "http://localhost:8000/moderation/check"

HEADERS = {
    "x-api-key": "ml_secret_key"
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
                "text": text
            },

            headers=HEADERS

        )

        latency = time.time() - start

        latency_list.append(latency)

        result = response.json()

        blocked = result.get("blocked", False)

        predicted = "toxic" if blocked else "ok"

        if predicted == expected:
            correct += 1

        print("Text:", text)
        print("Expected:", expected)
        print("Predicted:", predicted)
        print("Latency:", latency)

    accuracy = correct / total

    avg_latency = sum(latency_list) / len(latency_list)

    print("\nRESULT")
    print("Accuracy:", accuracy)
    print("Avg latency:", avg_latency)


if __name__ == "__main__":
    run_test()
