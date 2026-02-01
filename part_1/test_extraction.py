"""
End-to-End Test: OCR + Field Extraction
Tests the complete pipeline from PDF to structured JSON
"""

import os
import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ocr_service import DocumentOCRService
from extraction_service import FieldExtractionService
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def print_separator(char="=", length=70):
    """Print a separator line"""
    print(char * length)


def print_section(title):
    """Print a section header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def test_single_file(file_path: str):
    """Test OCR + Extraction on a single file"""
    print_section(f"Processing: {os.path.basename(file_path)}")

    # Step 1: OCR
    print("\n📄 Step 1: Running OCR...")
    ocr_service = DocumentOCRService()
    ocr_result = ocr_service.process_file(file_path)

    if not ocr_result["success"]:
        print(f"❌ OCR Failed: {ocr_result['error']}")
        return None

    print(f"✅ OCR Complete: {len(ocr_result['full_text'])} characters extracted")

    # Show first 500 characters of OCR text
    print("\n📝 OCR Text Preview (first 500 chars):")
    print("-" * 70)
    print(ocr_result['full_text'][:500])
    print("-" * 70)

    # Step 2: Field Extraction
    print("\n🤖 Step 2: Extracting Fields with GPT-4o...")
    extraction_service = FieldExtractionService()
    extraction_result = extraction_service.extract_from_file(ocr_result)

    if not extraction_result["success"]:
        print(f"❌ Extraction Failed: {extraction_result['error']}")
        return None

    print("✅ Extraction Complete!")

    # Step 3: Display Results
    print("\n📊 Extracted Fields (JSON):")
    print("=" * 70)
    print(json.dumps(extraction_result["data"], indent=2, ensure_ascii=False))
    print("=" * 70)

    # Count non-empty fields
    def count_filled_fields(data, path=""):
        count = 0
        for key, value in data.items():
            current_path = f"{path}.{key}" if path else key
            if isinstance(value, dict):
                count += count_filled_fields(value, current_path)
            elif value and value != "":
                count += 1
        return count

    filled_count = count_filled_fields(extraction_result["data"])
    total_fields = 29  # Total number of leaf fields in schema

    print(f"\n✅ Field Extraction Summary:")
    print(f"   - Fields filled: {filled_count}/{total_fields}")
    print(f"   - Completion rate: {(filled_count / total_fields) * 100:.1f}%")

    return extraction_result


def test_all_samples():
    """Test all sample files in the data folder"""
    print_separator("=")
    print("🧪  END-TO-END TEST: OCR + GPT-4o FIELD EXTRACTION")
    print_separator("=")

    # Find sample files
    data_folders = ['data', '../phase1_data', 'phase1_data']
    sample_files = []

    for folder in data_folders:
        if os.path.exists(folder):
            files = [
                os.path.join(folder, f)
                for f in os.listdir(folder)
                if f.lower().endswith('.pdf')
            ]
            sample_files.extend(files)
            if files:
                break

    if not sample_files:
        print("\n⚠️  No PDF files found in data folders")
        print("Please add PDF files to the 'data' folder")
        return

    print(f"\nFound {len(sample_files)} PDF files to process")

    # Process each file
    results = []
    for file_path in sample_files:
        result = test_single_file(file_path)
        if result:
            results.append({
                "file": os.path.basename(file_path),
                "result": result
            })

    # Final Summary
    print_section("📈 FINAL SUMMARY")

    print(f"\n✅ Successfully processed: {len(results)}/{len(sample_files)} files")

    for item in results:
        filled = sum(
            1 for v in str(item['result']['data']).split('"')
            if v and v not in ['', ':', '{', '}', ',', '[', ']']
        )
        print(f"   - {item['file']}: Extraction successful")

    print("\n" + "=" * 70)
    print("🎉 Testing Complete!")
    print("=" * 70)


def interactive_test():
    """Interactive mode - ask user for file"""
    print_section("📁 INTERACTIVE MODE")

    file_path = input("\nEnter path to PDF file: ").strip()

    if not file_path:
        print("No file specified")
        return

    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return

    test_single_file(file_path)


def main():
    """Main test function"""

    # Check if a file path was provided as argument
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        if os.path.exists(file_path):
            test_single_file(file_path)
        else:
            print(f"❌ File not found: {file_path}")
    else:
        # Run batch test on all samples
        test_all_samples()

        # Offer interactive mode
        print("\n" + "=" * 70)
        response = input("Would you like to test another file? (y/n): ").strip().lower()
        if response == 'y':
            interactive_test()


if __name__ == "__main__":
    main()