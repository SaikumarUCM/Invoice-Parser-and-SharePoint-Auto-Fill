# Model Recommendations for Invoice Parsing (4GB RTX 3050)

## LLM Models (Best to Good)

### 1. **Microsoft Phi-2** (RECOMMENDED)
- **Model**: `microsoft/phi-2`
- **Size**: 2.7B parameters
- **Memory**: ~2-3GB VRAM
- **Why**: Excellent instruction following, good at structured JSON extraction, optimized for small GPUs
- **Setup**: 
  ```bash
  MODEL_NAME=microsoft/phi-2
  ```

### 2. **Qwen2-0.5B-Instruct**
- **Model**: `Qwen/Qwen2-0.5B-Instruct`
- **Size**: 0.5B parameters
- **Memory**: ~1-1.5GB VRAM
- **Why**: Very small, fast inference, decent instruction following
- **Setup**:
  ```bash
  MODEL_NAME=Qwen/Qwen2-0.5B-Instruct
  ```

### 3. **Qwen2-1.5B-Instruct**
- **Model**: `Qwen/Qwen2-1.5B-Instruct`
- **Size**: 1.5B parameters
- **Memory**: ~2GB VRAM
- **Why**: Better accuracy than 0.5B, still fits in 4GB
- **Setup**:
  ```bash
  MODEL_NAME=Qwen/Qwen2-1.5B-Instruct
  ```

### 4. **TinyLlama-1.1B-Chat**
- **Model**: `TinyLlama/TinyLlama-1.1B-Chat-v1.0`
- **Size**: 1.1B parameters
- **Memory**: ~1.5GB VRAM
- **Why**: Very fast, lightweight, good for simple extraction
- **Setup**:
  ```bash
  MODEL_NAME=TinyLlama/TinyLlama-1.1B-Chat-v1.0
  ```

### 5. **Google Flan-T5-Base** (Current Default)
- **Model**: `google/flan-t5-base`
- **Size**: 250M parameters
- **Memory**: ~1GB VRAM
- **Why**: Seq2seq model, good for structured tasks, very efficient
- **Note**: Already configured, but may need better prompting

## OCR Models

### 1. **EasyOCR** (RECOMMENDED)
- **Library**: `easyocr`
- **Why**: 
  - Supports 80+ languages
  - Better accuracy than Tesseract for invoices
  - Handles rotated text and complex layouts
  - GPU acceleration support
- **Installation**:
  ```bash
  pip install easyocr
  ```
- **Memory**: ~1-2GB VRAM when using GPU

### 2. **PaddleOCR**
- **Library**: `paddlepaddle`, `paddleocr`
- **Why**: 
  - Excellent for structured documents
  - Good at table extraction
  - Fast inference
- **Installation**:
  ```bash
  pip install paddlepaddle paddleocr
  ```
- **Memory**: ~1-2GB VRAM

### 3. **Tesseract OCR** (Current)
- **Library**: `pytesseract`
- **Why**: 
  - Lightweight
  - Good for simple documents
  - Already integrated
- **Limitations**: Struggles with complex layouts, rotated text

## Recommended Configuration

### For Best Accuracy (if you can fit it):
```bash
# LLM
MODEL_NAME=microsoft/phi-2
MAX_NEW_TOKENS=512

# OCR - Use EasyOCR
```

### For Best Performance (fits comfortably):
```bash
# LLM
MODEL_NAME=Qwen/Qwen2-1.5B-Instruct
MAX_NEW_TOKENS=512

# OCR - Use EasyOCR
```

### For Maximum Speed (minimal memory):
```bash
# LLM
MODEL_NAME=google/flan-t5-base
MAX_NEW_TOKENS=512

# OCR - Keep Tesseract or use EasyOCR
```

## Memory Optimization Tips

1. **Use 8-bit quantization** (if supported):
   ```python
   from transformers import BitsAndBytesConfig
   quantization_config = BitsAndBytesConfig(load_in_8bit=True)
   ```

2. **Use CPU offloading** for very large models

3. **Reduce batch size** to 1

4. **Use gradient checkpointing** during inference (if needed)

5. **Clear cache** between inferences:
   ```python
   torch.cuda.empty_cache()
   ```

## Testing Your Setup

After changing models, test with:
```python
python -c "from app.llm_parser import init_model; init_model()"
```

This will load the model and show memory usage.
