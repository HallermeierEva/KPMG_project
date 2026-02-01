"""
Test script to verify Azure connections
Run this to ensure everything is configured correctly
"""

import os
from dotenv import load_dotenv
from openai import AzureOpenAI
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential

# Load environment variables
load_dotenv()


def test_document_intelligence():
    """Test Azure Document Intelligence connection"""
    print("🔍 Testing Document Intelligence...")

    try:
        endpoint = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
        key = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY")

        if not endpoint or not key:
            print("❌ Missing Document Intelligence credentials in .env")
            return False

        client = DocumentIntelligenceClient(
            endpoint=endpoint,
            credential=AzureKeyCredential(key)
        )

        print(f"✅ Document Intelligence connected: {endpoint}")
        return True

    except Exception as e:
        print(f"❌ Document Intelligence error: {e}")
        return False


def test_openai_gpt():
    """Test Azure OpenAI GPT connection"""
    print("\n🤖 Testing Azure OpenAI GPT-4o...")

    try:
        client = AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
        )

        # Test with a simple completion
        response = client.chat.completions.create(
            model=os.getenv("AZURE_OPENAI_GPT4O_DEPLOYMENT"),
            messages=[
                {"role": "user", "content": "Say 'Connection successful!' if you receive this."}
            ],
            max_tokens=50
        )

        result = response.choices[0].message.content
        print(f"✅ GPT-4o Response: {result}")
        return True

    except Exception as e:
        print(f"❌ Azure OpenAI error: {e}")
        return False


def test_openai_embeddings():
    """Test Azure OpenAI Embeddings connection"""
    print("\n📊 Testing Azure OpenAI Embeddings...")

    try:
        client = AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
        )

        # Test embedding
        response = client.embeddings.create(
            model=os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT"),
            input="Test embedding"
        )

        embedding_length = len(response.data[0].embedding)
        print(f"✅ Embeddings working! Vector dimension: {embedding_length}")
        return True

    except Exception as e:
        print(f"❌ Embeddings error: {e}")
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("🚀 KPMG GenAI Assessment - Azure Connection Tests")
    print("=" * 60)

    results = {
        "Document Intelligence": test_document_intelligence(),
        "OpenAI GPT-4o": test_openai_gpt(),
        "OpenAI Embeddings": test_openai_embeddings()
    }

    print("\n" + "=" * 60)
    print("📋 Test Results Summary:")
    print("=" * 60)

    for service, status in results.items():
        status_icon = "✅" if status else "❌"
        print(f"{status_icon} {service}: {'PASSED' if status else 'FAILED'}")

    all_passed = all(results.values())

    if all_passed:
        print("\n🎉 All tests passed! You're ready to start development!")
    else:
        print("\n⚠️ Some tests failed. Please check your .env configuration.")

    print("=" * 60)

    return all_passed


if __name__ == "__main__":
    main()