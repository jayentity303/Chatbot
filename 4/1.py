"""
OpenAI API Testing Suite
------------------------
This script tests various capabilities of the OpenAI API through a custom endpoint.
"""

import base64
from datetime import datetime
from openai import OpenAI

# ====================== API CONFIGURATION ======================
API_KEY = "ddc-beta-owt4ux3idq-aVQGkekXPETsicuyoDq8Ub6Heww0zoMVYva"
BASE_URL = "https://beta.sree.shop/v1"

client = OpenAI(
    api_key=API_KEY,
    base_url=BASE_URL
)

# ====================== TEST 1: IMAGE GENERATION ======================
def test_image_generation():
    """Test image generation capabilities and save the result"""
    print("\n" + "="*60)
    print("🖼️  TEST: IMAGE GENERATION")
    print("="*60)
    
    image_prompt = """Lord krisna playing flute"""
    
    response = client.images.generate(
        model="Provider-5/flux-schnell",
        prompt=image_prompt,
        n=5,
        size="1024x1024",
        response_format="b64_json"
    )
    
    # Save the generated image
    image_data = response.data[0].b64_json
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    image_filename = f"generated_image_{timestamp}.png"
    
    with open(image_filename, "wb") as image_file:
        image_file.write(base64.b64decode(image_data))
    
    print(f"✅ Image generated and saved as: {image_filename}")

# ====================== TEST 2: CHAT COMPLETION (STANDARD) ======================
def test_chat_completion_standard():
    """Test standard (non-streaming) chat completion"""
    print("\n" + "="*60)
    print("💬 TEST: CHAT COMPLETION (STANDARD)")
    print("="*60)
    
    response = client.chat.completions.create(
        model="Provider-5/gpt-4o-mini",
        messages=[
            {"role": "user", "content": "Hello!"}
        ],
        stream=False
    )
    
    print(f"📊 Response: {response}")

# ====================== TEST 3: CHAT COMPLETION (STREAMING) ======================
def test_chat_completion_streaming():
    """Test streaming chat completion and convert it into a readable format"""
    print("\n" + "="*60)
    print("📡 TEST: CHAT COMPLETION (STREAMING)")
    print("="*60)
    
    stream = client.chat.completions.create(
        model="Provider-5/qwen-2.5-coder-32b",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Write 10 lines about India ??"}
        ],
        stream=True
    )
    
    print("📊 Streaming Response:")
    readable_response = ""
    for chunk in stream:
        # Access the actual content from the chunk
        if chunk.choices[0].delta.content is not None:
            readable_response += chunk.choices[0].delta.content
    
    print(readable_response.strip())

# ====================== RUN ALL TESTS ======================
if __name__ == "__main__":
    print("\n🧪 STARTING API TESTS 🧪\n")
    
    #test_image_generation()
    #test_chat_completion_standard()
    test_chat_completion_streaming()
    
    print("\n✨ ALL TESTS COMPLETED ✨")
