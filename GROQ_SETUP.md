# Groq API Setup Guide

## Quick Start

### 1. Get Your Groq API Key

1. Go to [https://console.groq.com](https://console.groq.com)
2. Sign up or log in
3. Navigate to API Keys section
4. Create a new API key
5. Copy the API key

### 2. Configure Environment Variables

Add to your `.env` file:

```bash
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.1-8b-instant
MAX_NEW_TOKENS=1024
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

The `groq` package will be installed automatically.

### 4. Run the Application

```bash
uvicorn app.main:app --reload
```

## Available Groq Models

### Recommended Models for Invoice Parsing:

1. **llama-3.1-8b-instant** (RECOMMENDED - Default)
   - Fastest inference
   - Good accuracy for structured JSON extraction
   - Excellent at following instructions
   - Currently available and actively supported

2. **mixtral-8x7b-32768**
   - Good balance of speed and accuracy
   - Large context window (32k tokens)
   - Great for complex invoices
   - Fallback option if default fails

3. **llama-3.1-70b-versatile** (DEPRECATED)
   - ⚠️ This model has been decommissioned
   - Do not use - will cause errors

### Model Comparison

| Model | Speed | Accuracy | Context | Best For | Status |
|-------|-------|----------|---------|----------|--------|
| llama-3.1-8b-instant | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 8k | All invoices, recommended | ✅ Active |
| mixtral-8x7b-32768 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 32k | Very long invoices | ✅ Active |
| llama-3.1-70b-versatile | - | - | - | - | ❌ Decommissioned |

## Advantages of Groq API

✅ **No GPU Required** - All inference happens on Groq's servers  
✅ **Ultra-Fast** - Groq's LPU (Language Processing Unit) provides extremely fast inference  
✅ **No Memory Constraints** - Your 4GB GPU limitation doesn't apply  
✅ **Always Updated** - Access to latest models without downloading  
✅ **Cost-Effective** - Pay per use, no infrastructure costs  

## Testing Your Setup

After configuration, test with:

```python
from app.llm_parser import init_model, parse_invoice_text

# Initialize (validates API key)
init_model()

# Test parsing
test_text = "Invoice #INV-001 Date: 2024-01-15 Total: $100.00"
result = parse_invoice_text(test_text)
print(result)
```

## Troubleshooting

### Error: "GROQ_API_KEY not configured"
- Make sure your `.env` file has `GROQ_API_KEY=your_key`
- Check that `.env` is in the project root directory
- Restart your application after adding the key

### Error: "Invalid API key"
- Verify your API key at [console.groq.com](https://console.groq.com)
- Make sure there are no extra spaces in the `.env` file
- Check that the key starts with `gsk_`

### Model Not Found / Decommissioned
- The code now automatically tries fallback models if the primary fails
- If you see "decommissioned" errors, the code will try: `llama-3.1-8b-instant` → `mixtral-8x7b-32768`
- Check available models at [console.groq.com/docs/models](https://console.groq.com/docs/models)
- Update `GROQ_MODEL` in `.env` to a valid model name (recommended: `llama-3.1-8b-instant`)

### Rate Limiting
- Groq has rate limits based on your plan
- Free tier: ~30 requests/minute
- If you hit limits, add retry logic or upgrade your plan

## API Usage Limits

- **Free Tier**: Limited requests per minute
- **Paid Plans**: Higher rate limits
- Check your usage at [console.groq.com](https://console.groq.com)

## Next Steps

1. Test with a sample invoice
2. Monitor extraction accuracy
3. Adjust `GROQ_MODEL` if needed
4. Consider fine-tuning prompts for your specific invoice formats
