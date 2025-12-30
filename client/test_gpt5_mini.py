#!/usr/bin/env python3
"""
Test GPT-5-mini API directly to debug empty responses
"""

import os
from openai import OpenAI

def test_gpt5_mini_text():
    """Test GPT-5-mini with simple text prompt"""
    print("🧪 Testing GPT-5-mini with text-only prompt...")
    
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ OPENAI_API_KEY not found")
        return
    
    print(f"✓ API Key found: {api_key[:10]}...")
    
    client = OpenAI(api_key=api_key)
    
    try:
        response = client.chat.completions.create(
            model="gpt-5-mini",
            messages=[
                {
                    "role": "user",
                    "content": "Hello! Please respond with a simple JSON: {\"test\": \"success\", \"message\": \"GPT-5-mini is working\"}"
                }
            ],
            max_completion_tokens=100
        )
        
        print(f"✓ Response received")
        print(f"  ID: {response.id}")
        print(f"  Model: {response.model}")
        print(f"  Usage: {response.usage}")
        print(f"  Finish reason: {response.choices[0].finish_reason}")
        print(f"  Content: {response.choices[0].message.content}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_gpt5_mini_vision():
    """Test GPT-5-mini with vision (base64 image)"""
    print("\n🧪 Testing GPT-5-mini with vision...")
    
    # Create a simple test image (1x1 pixel PNG)
    import base64
    
    # Minimal 1x1 red pixel PNG (base64 encoded)
    test_image = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
    
    api_key = os.getenv('OPENAI_API_KEY')
    client = OpenAI(api_key=api_key)
    
    try:
        response = client.chat.completions.create(
            model="gpt-5-mini",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Describe this image and return JSON: {\"description\": \"your description\", \"color\": \"detected color\"}"
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{test_image}"
                            }
                        }
                    ]
                }
            ],
            max_completion_tokens=100
        )
        
        print(f"✓ Vision response received")
        print(f"  ID: {response.id}")
        print(f"  Model: {response.model}")
        print(f"  Usage: {response.usage}")
        print(f"  Finish reason: {response.choices[0].finish_reason}")
        print(f"  Content: {response.choices[0].message.content}")
        
        return True
        
    except Exception as e:
        print(f"❌ Vision error: {e}")
        return False

if __name__ == "__main__":
    print("🔍 GPT-5-mini Debugging Test")
    print("=" * 50)
    
    # Test 1: Text only
    text_ok = test_gpt5_mini_text()
    
    # Test 2: Vision
    vision_ok = test_gpt5_mini_vision()
    
    print("\n📊 Results:")
    print(f"  Text API: {'✅ Working' if text_ok else '❌ Failed'}")
    print(f"  Vision API: {'✅ Working' if vision_ok else '❌ Failed'}")
    
    if not text_ok:
        print("\n💡 Suggestions:")
        print("  - Check OPENAI_API_KEY is valid")
        print("  - Check you have access to gpt-5-mini model")
        print("  - Try gpt-4o-mini instead")
    
    if text_ok and not vision_ok:
        print("\n💡 Vision Issue:")
        print("  - GPT-5-mini might not support vision")
        print("  - Try gpt-4o for vision tasks")
