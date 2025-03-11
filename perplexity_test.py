import requests
import json
import sys

def test_perplexity_api(api_key: str):
    """
    Simple test function that connects to Perplexity API with a hardcoded question
    and prints the response to the console.
    
    Args:
        api_key: Your Perplexity API key
    """
    print(f"Testing Perplexity API with key starting with {api_key[:5]}...")
    
    # Hardcoded test question
    test_question = "What is the price of gold in dollars?"
    
    # API endpoint
    url = "https://api.perplexity.ai/chat/completions"
    
    # Headers with API key
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    # Request payload
    data = {
        "model": "sonar",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": test_question}
        ],
        "temperature": 0.7,
        "max_tokens": 1000
    }
    
    print(f"Sending request to {url}...")
    print(f"Headers: {json.dumps(headers, indent=2).replace(api_key, f'{api_key[:5]}...')}")
    print(f"Data: {json.dumps(data, indent=2)}")
    
    try:
        # Make the API request
        response = requests.post(
            url,
            headers=headers,
            data=json.dumps(data),
            timeout=30
        )
        
        print(f"\nReceived response with status code: {response.status_code}")
        
        # Check if the request was successful
        if response.status_code == 200:
            try:
                response_data = response.json()
                print("\nSUCCESS! Here's the response content:")
                print("-" * 50)
                print(response_data['choices'][0]['message']['content'])
                print("-" * 50)
                return True
            except Exception as e:
                print(f"Error parsing JSON response: {e}")
                print(f"Raw response: {response.text[:500]}...")
        else:
            print(f"Error response status code: {response.status_code}")
            try:
                error_content = response.json()
                print(f"Error details: {json.dumps(error_content, indent=2)}")
            except:
                print(f"Raw error response: {response.text[:500]}...")
    
    except requests.exceptions.RequestException as e:
        print(f"Request exception: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")
    
    return False

if __name__ == "__main__":
    # If API key is provided as command line argument, use it
    if len(sys.argv) > 1:
        api_key = sys.argv[1]
    else:
        # Otherwise prompt for it
        api_key = input("Enter your Perplexity API key: ")
    
    # Test the API connection
    success = test_perplexity_api(api_key)
    
    if success:
        print("\nAPI test completed successfully!")
    else:
        print("\nAPI test failed. Please check your API key and network connection.")
