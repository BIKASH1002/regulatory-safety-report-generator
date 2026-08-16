"""Gemini API client for grounded generation."""

import json
import os

from google import genai
from google.genai import types
from dotenv import load_dotenv


GEMINI_MODEL = "gemini-2.5-flash"


def initialize_client():
    """Initialize and return Gemini client, or error if API key missing."""
    client = None
    error = None

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        error = "GEMINI_API_KEY environment variable not set. Please provide a valid API key."
        return client, error

    try:
        client = genai.Client(api_key=api_key)
    except Exception as error:
        error = "Failed to initialize Gemini client: " + str(error)
        return client, error

    return client, error


def generate_section(client, system_prompt, user_prompt, max_tokens=2048):
    """Generate a single report section using Gemini."""
    generated_text = None
    error = None

    if client is None:
        error = "Gemini client not initialized"
        return generated_text, error

    if not system_prompt or not user_prompt:
        error = "System prompt and user prompt required"
        return generated_text, error

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.3,
                top_p=0.9,
                top_k=40,
                max_output_tokens=max_tokens,
                safety_settings=[
                    {
                        "category": "HARM_CATEGORY_HARASSMENT",
                        "threshold": "BLOCK_ONLY_HIGH",
                    },
                    {
                        "category": "HARM_CATEGORY_HATE_SPEECH",
                        "threshold": "BLOCK_ONLY_HIGH",
                    },
                    {
                        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                        "threshold": "BLOCK_ONLY_HIGH",
                    },
                    {
                        "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                        "threshold": "BLOCK_ONLY_HIGH",
                    },
                ],
            ),
        )

        if not response.text:
            error = "Gemini returned empty response"
            return generated_text, error

        generated_text = response.text.strip()
    except Exception as error:
        error = "Gemini generation failed: " + str(error)
        return generated_text, error

    return generated_text, error


def check_gemini_connection():
    """Verify Gemini connectivity when this module is run directly."""
    load_dotenv()
    client, error = initialize_client()
    if error:
        print(json.dumps({"error": error}))
        return 1

    response, error = generate_section(
        client,
        "You are a helpful assistant.",
        "Respond with: 'Gemini connection successful.'",
        max_tokens=50,
    )
    if error:
        print(json.dumps({"error": error}))
        return 1

    print(json.dumps({"success": True, "response": response}))
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(check_gemini_connection())