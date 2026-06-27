# EasyOCR Setup Guide

## Overview

EasyOCR has been integrated into the invoice parser for better accuracy. It provides:
- ✅ Better accuracy than Tesseract for invoices
- ✅ Handles rotated text and complex layouts
- ✅ Supports 80+ languages
- ✅ GPU acceleration (automatic fallback to CPU)
- ✅ Better table extraction

## Installation

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

This will install:
- `easyocr>=1.7.0` - Main OCR library
- `torch>=2.0.0` - PyTorch (required for EasyOCR)
- `opencv-python-headless` - Image processing
- `pdf2image` - PDF to image conversion
- `pillow` - Image handling

### 2. First Run (Downloads Models)

On first run, EasyOCR will automatically download language models. This happens once:
- English model: ~200MB
- Additional languages: ~200MB each

**Note**: The first initialization may take 1-2 minutes while models download.

## Configuration

### Language Support

Edit your `.env` file to specify languages:

```bash
# Single language (English - default)
OCR_LANGUAGES=en

# Multiple languages (comma-separated)
OCR_LANGUAGES=en,hi,ta
```

### Supported Languages

Common Indian languages:
- `en` - English
- `hi` - Hindi
- `ta` - Tamil
- `te` - Telugu
- `kn` - Kannada
- `mr` - Marathi
- `gu` - Gujarati
- `pa` - Punjabi
- `bn` - Bengali
- `ml` - Malayalam
- `or` - Odia
- `as` - Assamese

**Full list**: EasyOCR supports 80+ languages. Check [EasyOCR documentation](https://github.com/JaidedAI/EasyOCR) for complete list.

## GPU vs CPU

### Automatic Detection

EasyOCR automatically detects and uses GPU if available:
- **GPU available**: Uses CUDA (faster)
- **GPU not available**: Falls back to CPU (slower but works)

### For 4GB RTX 3050

Your GPU will be used automatically. If you encounter memory issues:
1. EasyOCR will automatically fall back to CPU
2. Or you can force CPU by setting environment variable (not recommended)

## Performance

### Speed Comparison

| Setup | Speed | Accuracy |
|-------|-------|----------|
| EasyOCR (GPU) | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| EasyOCR (CPU) | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Tesseract | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |

### Typical Processing Times

- **Single page invoice (GPU)**: 2-5 seconds
- **Single page invoice (CPU)**: 5-10 seconds
- **Multi-page PDF (GPU)**: 2-5 seconds per page
- **Multi-page PDF (CPU)**: 5-10 seconds per page

## Usage

The OCR is automatically initialized at startup. No code changes needed!

### API Usage

```bash
POST /parse-invoice
Content-Type: multipart/form-data

file: <invoice.pdf>
```

The system will:
1. Extract text using EasyOCR
2. Parse with Groq LLM
3. Return structured JSON

## Troubleshooting

### Issue: "CUDA out of memory"

**Solution**: EasyOCR will automatically fall back to CPU. This is normal for 4GB GPUs with large images.

### Issue: Slow first run

**Solution**: Normal! EasyOCR downloads models on first run. Subsequent runs are faster.

### Issue: Model download fails

**Solution**: 
1. Check internet connection
2. Models are downloaded to: `~/.EasyOCR/model/`
3. You can manually download from: https://github.com/JaidedAI/EasyOCR/releases

### Issue: Poor accuracy

**Solutions**:
1. Ensure image quality is good (300 DPI minimum)
2. Try preprocessing images (brightness, contrast)
3. Use appropriate languages in `OCR_LANGUAGES`
4. Check if text is rotated (EasyOCR handles this better than Tesseract)

### Issue: "No module named 'easyocr'"

**Solution**: 
```bash
pip install easyocr
```

### Issue: PDF conversion fails

**Solution**: Install Poppler:
- **Windows**: Download from https://github.com/oschwartz10612/poppler-windows/releases
- **Linux**: `sudo apt-get install poppler-utils`
- **Mac**: `brew install poppler`

Set path in `.env`:
```bash
POPPLER_PATH=C:\path\to\poppler\bin
```

## Advanced Configuration

### Custom Confidence Threshold

Edit `app/ocr.py` line ~95:
```python
if confidence > 0.3:  # Adjust threshold (0.0 to 1.0)
```

Lower = more text (may include errors)
Higher = less text (more accurate)

### Enable Debug Mode

Edit `app/ocr.py` line ~50:
```python
verbose=True  # Shows detailed EasyOCR output
```

## Comparison with Tesseract

| Feature | EasyOCR | Tesseract |
|---------|---------|-----------|
| Accuracy (invoices) | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| Rotated text | ✅ Excellent | ⚠️ Limited |
| Complex layouts | ✅ Excellent | ⚠️ Limited |
| Tables | ✅ Good | ❌ Poor |
| Speed (GPU) | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Speed (CPU) | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Language support | 80+ | 100+ |
| Setup complexity | Easy | Medium |

## Migration from Tesseract

If you were using Tesseract before:
1. ✅ No code changes needed - everything is automatic
2. ✅ Remove Tesseract installation (optional)
3. ✅ Update `.env` - remove `TESSERACT_CMD` (not needed)
4. ✅ Keep `POPPLER_PATH` if using PDFs

## Next Steps

1. Test with a sample invoice
2. Adjust `OCR_LANGUAGES` if needed
3. Monitor accuracy and adjust confidence threshold if needed
4. Enjoy better extraction results! 🎉
