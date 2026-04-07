import requests
response = requests.get("http://localhost:8880/v1/audio/voices")
voices = response.json()["voices"]

# # Example 1: Simple voice combination (50%/50% mix)
# response = requests.post(
#     "http://localhost:8880/v1/audio/speech",
#     json={
#         "input": "Hello world!",
#         "voice": "af_bella+af_sky",  # Equal weights
#         "response_format": "mp3"
#     }
# )

# Example 2: Weighted voice combination (67%/33% mix)
response = requests.post(
    "http://localhost:8880/v1/audio/speech",
    json={
        "input": "Hello world!",
        "voice": "af_bella(2)+af_sky(1)",  # 2:1 ratio = 67%/33%
        "response_format": "mp3"
    }
)

# Example 3: Download combined voice as .pt file
response = requests.post(
    "http://localhost:8880/v1/audio/voices/combine",
    json="af_heart(3)+af_bella(1)"  # 2:1 ratio = 67%/33%
)

# Save the .pt file
with open("combined_voice.pt", "wb") as f:
    f.write(response.content)

# Use the downloaded voice file
response = requests.post(
    "http://localhost:8880/v1/audio/speech",
    json={
        "input": "Key Principles and Practices: Iterative and Incremental Development: Instead of large, infrequent releases, agile cybersecurity emphasizes smaller, more frequent iterations of security solutions. This allows for quicker feedback, adaptation, and refinement of security measures. Collaboration and Communication: Agile encourages close collaboration between security teams, development teams, and other stakeholders, fostering a shared responsibility for cybersecurity. This breaks down silos and",
        "voice": "combined_voice",  # Use the saved voice file
        "response_format": "mp3"
    }
)
