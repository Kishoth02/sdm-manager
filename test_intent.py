import requests

response = requests.post("http://localhost:11434/api/generate", json={
    "model": "sdm-intent",
    "prompt": "add Yes as option D in Q17 in group 1",
    "stream": False
})

raw = response.json()["response"]
print(repr(raw))