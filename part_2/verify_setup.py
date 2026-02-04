"""
Quick verification script to check if project is set up correctly
"""
import os
import sys

print("=" * 60)
print("MEDICAL CHATBOT - SETUP VERIFICATION")
print("=" * 60)

errors = []
warnings = []
success = []

# Check 1: Environment variables
print("\n1. Checking Environment Variables...")
from dotenv import load_dotenv

load_dotenv()

required_vars = [
    "AZURE_OPENAI_ENDPOINT",
    "AZURE_OPENAI_KEY",
    "AZURE_OPENAI_API_VERSION",
    "AZURE_OPENAI_DEPLOYMENT_NAME"
]

for var in required_vars:
    value = os.getenv(var)
    if value:
        success.append(f"   ✅ {var} is set")
    else:
        errors.append(f"   ❌ {var} is MISSING")

# Check 2: Knowledge base folder
print("\n2. Checking Knowledge Base...")
if os.path.exists("phase2_data"):
    success.append("   ✅ phase2_data/ folder exists")

    html_files = [f for f in os.listdir("phase2_data") if f.endswith(".html")]
    if len(html_files) >= 6:
        success.append(f"   ✅ Found {len(html_files)} HTML files")
        for f in html_files:
            print(f"      - {f}")
    else:
        errors.append(f"   ❌ Only {len(html_files)} HTML files found (need 6)")
else:
    errors.append("   ❌ phase2_data/ folder NOT FOUND")

# Check 3: Required Python files
print("\n3. Checking Python Files...")
required_files = ["main.py", "app.py", "processor.py", "prompts.py", "logger.py"]
for f in required_files:
    if os.path.exists(f):
        success.append(f"   ✅ {f} exists")
    else:
        errors.append(f"   ❌ {f} is MISSING")

# Check 4: Check processor.py has correct path
print("\n4. Checking processor.py configuration...")
try:
    with open("processor.py", "r", encoding="utf-8") as f:
        content = f.read()
        if 'data_dir = "phase2_data"' in content or "data_dir = 'phase2_data'" in content:
            success.append('   ✅ processor.py uses correct path "phase2_data"')
        elif 'data_dir = "phase2_data"' in content or "data_dir = 'phase2_data'" in content:
            errors.append('   ❌ processor.py still uses wrong path "phase2_data"')
        else:
            warnings.append('   ⚠️  Could not verify data_dir path in processor.py')
except Exception as e:
    errors.append(f"   ❌ Error reading processor.py: {e}")

# Check 5: Test knowledge base loading
print("\n5. Testing Knowledge Base Loading...")
try:
    from processor import get_all_medical_context

    context = get_all_medical_context()

    if "SOURCE FILE" in context and "not found" not in context.lower():
        success.append("   ✅ Knowledge base loads successfully")
        # Count how many files were loaded
        file_count = context.count("SOURCE FILE")
        success.append(f"   ✅ Loaded {file_count} knowledge files")
    else:
        errors.append("   ❌ Knowledge base failed to load")
        print(f"      Error: {context[:200]}")
except Exception as e:
    errors.append(f"   ❌ Error loading knowledge base: {e}")

# Check 6: Logs directory
print("\n6. Checking Logs Directory...")
if not os.path.exists("logs"):
    os.makedirs("logs")
    success.append("   ✅ Created logs/ directory")
else:
    success.append("   ✅ logs/ directory exists")

# Print Summary
print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)

if success:
    print(f"\n✅ SUCCESS ({len(success)} items):")
    for s in success:
        print(s)

if warnings:
    print(f"\n⚠️  WARNINGS ({len(warnings)} items):")
    for w in warnings:
        print(w)

if errors:
    print(f"\n❌ ERRORS ({len(errors)} items):")
    for e in errors:
        print(e)
    print("\n🔧 Fix these errors before starting the chatbot!")
    sys.exit(1)
else:
    print("\n🎉 ALL CHECKS PASSED!")
    print("\n📋 NEXT STEPS:")
    print("   1. Start backend:  python main.py")
    print("   2. In new terminal, start frontend: streamlit run app.py")
    print("   3. Open browser to: http://localhost:8501")
    sys.exit(0)