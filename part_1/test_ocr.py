"""
Standalone test script for Azure Document Intelligence OCR
Run this to verify your OCR setup is working correctly
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ocr_service import DocumentOCRService
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def test_ocr_initialization():
    """Test if OCR service can be initialized"""
    print("=" * 60)
    print("TEST 1: OCR Service Initialization")
    print("=" * 60)

    try:
        ocr_service = DocumentOCRService()
        print("✅ OCR Service initialized successfully!")
        print(f"   Endpoint: {ocr_service.endpoint}")
        return ocr_service
    except Exception as e:
        print(f"❌ Failed to initialize OCR service: {e}")
        return None


def test_ocr_with_sample(ocr_service, sample_file_path):
    """Test OCR with a sample file"""
    print("\n" + "=" * 60)
    print("TEST 2: OCR Document Processing")
    print("=" * 60)

    if not os.path.exists(sample_file_path):
        print(f"⚠️  Sample file not found: {sample_file_path}")
        print("   Please provide a PDF or image file to test")
        return False

    try:
        print(f"Processing: {sample_file_path}")
        result = ocr_service.process_file(sample_file_path)

        if result["success"]:
            print("\n✅ OCR Processing Successful!")
            print(f"\n📄 Extracted Text Statistics:")
            print(f"   - Total characters: {len(result['full_text'])}")
            print(f"   - Total pages: {len(result['structured_content']['pages'])}")
            print(f"   - Paragraphs: {len(result['structured_content']['paragraphs'])}")
            print(f"   - Tables: {len(result['structured_content']['tables'])}")

            # Show first few lines
            lines = result['full_text'].split('\n')
            print(f"\n📝 First 10 lines of extracted text:")
            print("-" * 60)
            for i, line in enumerate(lines[:10], 1):
                print(f"{i:2}. {line[:70]}{'...' if len(line) > 70 else ''}")

            # Show page details
            if result['structured_content']['pages']:
                print(f"\n📃 Page Details:")
                for page in result['structured_content']['pages']:
                    print(f"   Page {page['page_number']}: {len(page['lines'])} lines")

            return True
        else:
            print(f"\n❌ OCR Processing Failed!")
            print(f"   Error: {result['error']}")
            return False

    except Exception as e:
        print(f"\n❌ Error during OCR test: {e}")
        import traceback
        traceback.print_exc()
        return False


def interactive_test():
    """Interactive test mode - ask user for file path"""
    print("\n" + "=" * 60)
    print("INTERACTIVE MODE: Test with Your Own File")
    print("=" * 60)

    file_path = input("\nEnter path to PDF or image file (or press Enter to skip): ").strip()

    if not file_path:
        print("Skipping interactive test")
        return None

    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return None

    return file_path


def main():
    """Main test function"""
    print("\n" + "=" * 70)
    print("🧪  AZURE DOCUMENT INTELLIGENCE OCR - TEST SUITE")
    print("=" * 70)

    # Test 1: Initialize OCR service
    ocr_service = test_ocr_initialization()

    if not ocr_service:
        print("\n❌ Cannot proceed with tests - initialization failed")
        print("\n💡 Make sure your .env file has:")
        print("   - AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
        print("   - AZURE_DOCUMENT_INTELLIGENCE_KEY")
        return

    # Test 2: Check for sample files in phase1_data folder
    pdf_files = ['283_ex1.pdf', '283_ex2.pdf', '283_ex3.pdf', '283_raw.pdf']
    for file in pdf_files:
        print('TEST OCR ' + file)
        test_ocr_with_sample(ocr_service, 'data/' + file)
        # Try interactive mode
        user_file = interactive_test()
        if user_file:
            test_ocr_with_sample(ocr_service, user_file)

    # Summary
    print("\n" + "=" * 70)
    print("📊 TEST SUMMARY")
    print("=" * 70)
    print("✅ OCR service is ready to use!")
    print("\n📚 Next Steps:")
    print("   1. Place your test PDFs in the phase1_data folder")
    print("   2. Run this script again to test OCR extraction")
    print("   3. Proceed to build the extraction service with GPT-4o")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()