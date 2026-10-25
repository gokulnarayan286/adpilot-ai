
import os
from google import genai

# Check that the API key exists without displaying it
if not os.getenv("GEMINI_API_KEY"):
    raise SystemExit(
        "API key missing. Configure GEMINI_API_KEY in this terminal."
    )

# Connect to Gemini
client = genai.Client()

# Send a small test request
response = client.models.generate_content(
    model="gemini-3.8-flash",
    contents="Reply with exactly: AdPilot AI Gemini connection successful."
)

print("\n===== GEMINI CONNECTION TEST =====")
print(response.text)
