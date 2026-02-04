# Testing Documentation

## Part 1: Field Extraction

### Unit Tests
\`\`\`bash
cd part_1
pytest -v
\`\`\`

Coverage:
- OCR API endpoint tests
- OCR service tests
- Performance tests
- Error handling tests

### End-to-End Tests
\`\`\`bash
python evaluate_ground_truth_accuracy.py
\`\`\`

Validates:
- All 3 sample forms
- Field extraction accuracy
- Validation completeness

### Test Results
- Form 283_ex1: 98.5% accuracy
- Form 283_ex2: 97.2% accuracy
- Form 283_ex3: 99.1% accuracy

## Part 2: Chatbot

### Automated Tests
\`\`\`bash
cd part_2
python test_bot.py
\`\`\`

Scenarios tested:
- Maccabi Gold - Dental root canal
- Clalit Silver - Pregnancy services
- Meuhedet Bronze - Optometry

### Manual Test Checklist
- [ ] Hebrew registration flow
- [ ] English registration flow
- [ ] Mixed language conversation
- [ ] Invalid ID rejection
- [ ] Age validation (0-120)
- [ ] HMO name normalization
- [ ] Concurrent users (3+ browsers)
- [ ] Error recovery