import requests


response = requests.get("http://localhost:8880/v1/audio/voices")
voices = response.json()["voices"]

# Generate audio
response = requests.post(
    "http://localhost:8880/v1/audio/speech",
    json={
        "model": "kokoro",  
        "input": "Key Principles and Practices: Iterative and Incremental Development: Instead of large, infrequent releases, agile cybersecurity emphasizes smaller, more frequent iterations of security solutions. This allows for quicker feedback, adaptation, and refinement of security measures. Collaboration and Communication: Agile encourages close collaboration between security teams, development teams, and other stakeholders, fostering a shared responsibility for cybersecurity. This breaks down silos and improves communication, leading to more aligned priorities and faster response times to security issues. Continuous Improvement: Agile principles promote a culture of continuous improvement, where teams regularly reflect on their performance and identify areas for optimization. This ensures that security practices evolve to meet the changing threat landscape.",
        "voice": "af_heart",
        "response_format": "mp3",  # Supported: mp3, wav, opus, flac
        "speed": 1.0
    }
)

# Save audio
with open("output.mp3", "wb") as f:
    f.write(response.content)