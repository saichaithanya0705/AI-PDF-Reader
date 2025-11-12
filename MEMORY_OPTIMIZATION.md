# Memory Optimization for Render Free Tier

## Current Memory Issues
Your app is using too much memory because it loads:
- torch (~1GB)
- sentence-transformers models (~500MB)
- faiss indexes
- spacy models (~500MB)

## Quick Fixes to Reduce Memory:

### 1. Use Smaller Models
Replace `all-MiniLM-L6-v2` with `paraphrase-MiniLM-L3-v2` (smaller, faster):

```python
# In main.py, change:
model = SentenceTransformer('paraphrase-MiniLM-L3-v2')  # 61MB vs 90MB
```

### 2. Disable Torch Multiprocessing
Add to main.py at the top:
```python
import torch
torch.set_num_threads(1)  # Reduce memory usage
```

### 3. Use CPU-only Torch (Already Done)
You're already using CPU version, which is good.

### 4. Lazy Load Everything
Only load models when first needed (already implemented).

### 5. Reduce Worker Processes
In your start command:
```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1
```

### 6. Use Render Paid Plan ($7/month)
- 512MB RAM → 2GB RAM
- Worth it for production

## Alternative: Switch to Railway
Railway's free tier is more generous and handles memory better.
