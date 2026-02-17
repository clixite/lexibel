# Legal RAG System - Quick Start Guide

Get your Legal RAG system running in 5 minutes!

## Prerequisites

- Python 3.11+
- Node.js 18+
- Docker (for Qdrant)
- OpenAI API key

## Step 1: Install Dependencies

```bash
# Backend dependencies
pip install qdrant-client sentence-transformers openai httpx

# Optional: For cross-encoder re-ranking
pip install sentence-transformers
```

## Step 2: Environment Setup

Create `.env` file in `F:\LexiBel\`:

```bash
# Qdrant Configuration
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=

# OpenAI Configuration (for embeddings and LLM)
OPENAI_API_KEY=sk-your-key-here
LLM_API_KEY=sk-your-key-here
LLM_MODEL=gpt-4-turbo

# Optional: Cross-encoder model
CROSS_ENCODER_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2

# Optional: Enable quantization for large scale
ENABLE_QUANTIZATION=false
```

## Step 3: Start Qdrant

```bash
# Using Docker (recommended)
docker run -d -p 6333:6333 -p 6334:6334 \
  -v $(pwd)/qdrant_storage:/qdrant/storage:z \
  qdrant/qdrant

# Verify it's running
curl http://localhost:6333
```

## Step 4: Index Legal Documents

```bash
# Navigate to project root
cd F:\LexiBel

# Index all sample documents
python -m apps.api.scripts.index_legal_documents --source all

# Output should show:
# ✓ Collection ready
# 📄 Indexing: Code Civil - Article 1382...
# ✅ Indexing complete!
```

## Step 5: Start Backend API

```bash
# Development mode
uvicorn apps.api.main:app --reload --port 8000

# API available at: http://localhost:8000
# Docs available at: http://localhost:8000/docs
```

## Step 6: Start Frontend

```bash
# Navigate to web app
cd apps/web

# Install dependencies (if not already done)
npm install

# Start development server
npm run dev

# Frontend available at: http://localhost:3000
```

## Step 7: Test the System

### Option A: Via Frontend UI

1. Open browser: `http://localhost:3000/dashboard/legal`
2. Try a search: "Article 1382 responsabilité"
3. Switch to Chat tab and ask: "Explique-moi l'article 1382"
4. Try Article Explanation tab

### Option B: Via API

```bash
# Test search endpoint
curl "http://localhost:8000/api/v1/legal/search?q=Article%201382&limit=5" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Test chat endpoint
curl -X POST "http://localhost:8000/api/v1/legal/chat" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "message": "Quels sont les délais de prescription?",
    "max_tokens": 2000
  }'
```

## Verify Installation

### Check 1: Qdrant Collection
```bash
curl http://localhost:6333/collections/belgian_legal_docs
```

Expected: Collection exists with documents

### Check 2: Search Endpoint
```bash
curl "http://localhost:8000/api/v1/legal/search?q=contrat" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

Expected: JSON response with search results

### Check 3: Frontend
Open `http://localhost:3000/dashboard/legal`

Expected: Beautiful UI with search interface

## Troubleshooting

### Problem: Qdrant Connection Error

**Solution:**
```bash
# Check Qdrant is running
docker ps | grep qdrant

# Restart if needed
docker restart <qdrant-container-id>

# Check logs
docker logs <qdrant-container-id>
```

### Problem: No Search Results

**Solution:**
```bash
# Re-index documents
python -m apps.api.scripts.index_legal_documents --source all

# Check collection
curl http://localhost:6333/collections/belgian_legal_docs/points/scroll
```

### Problem: OpenAI API Errors

**Solution:**
```bash
# Verify API key
echo $OPENAI_API_KEY

# Test API key
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

### Problem: Frontend Not Loading

**Solution:**
```bash
# Check Next.js is running
ps aux | grep next

# Clear cache and restart
rm -rf apps/web/.next
cd apps/web && npm run dev
```

## Next Steps

### 1. Customize Data Sources

Edit `F:\LexiBel\apps\api\scripts\index_legal_documents.py`:
- Add your own legal documents
- Adjust chunking parameters
- Configure metadata

### 2. Fine-tune Search

Edit `F:\LexiBel\apps\api\config\qdrant_config.py`:
- Adjust hybrid search weights
- Configure re-ranking
- Optimize HNSW parameters

### 3. Customize UI

Edit `F:\LexiBel\apps\web\app\dashboard\legal\page.tsx`:
- Modify colors and styling
- Add custom filters
- Integrate with your case system

### 4. Production Deployment

See `LEGAL_RAG_SYSTEM.md` for:
- Production configuration
- Performance optimization
- Monitoring setup
- Security hardening

## Common Use Cases

### Search for Legal Articles
```bash
curl "http://localhost:8000/api/v1/legal/search?q=divorce%20procédure&document_type=code_judiciaire"
```

### Ask Legal Questions
```bash
curl -X POST "http://localhost:8000/api/v1/legal/chat" \
  -d '{"message": "Quelles sont les conditions pour un divorce?"}'
```

### Explain Complex Articles
```bash
curl -X POST "http://localhost:8000/api/v1/legal/explain-article" \
  -d '{
    "article_text": "Article 1382: Tout fait quelconque...",
    "simplification_level": "basic"
  }'
```

### Predict Case Outcomes
```bash
curl -X POST "http://localhost:8000/api/v1/legal/predict-jurisprudence" \
  -d '{
    "case_facts": "Un patient poursuit un médecin...",
    "relevant_articles": ["1382"]
  }'
```

## Performance Benchmarks

After setup, you should see:

| Metric | Expected Value |
|--------|---------------|
| Search Latency | 25-50ms |
| Search + Re-ranking | 75-100ms |
| Chat Response | 1-3s |
| Indexing Speed | 100 docs/sec |
| Memory Usage | ~2-4GB |

## Support

- **Documentation**: See `LEGAL_RAG_SYSTEM.md`
- **API Reference**: `http://localhost:8000/docs`
- **Issues**: Check logs in `apps/api/logs/`

## Success Checklist

- [ ] Qdrant running and accessible
- [ ] Legal documents indexed (5+ documents)
- [ ] Backend API responding
- [ ] Frontend UI loads
- [ ] Search returns results
- [ ] Chat generates responses
- [ ] Re-ranking improves relevance
- [ ] Citations are tracked

## You're Ready! 🚀

Start searching Belgian legal documents with AI-powered semantic search!

Try these example queries:
- "Article 1382 responsabilité civile"
- "Divorce procédure Belgique"
- "Contrat de travail préavis"
- "Code Civil obligations"

---

**Need help?** See full documentation in `LEGAL_RAG_SYSTEM.md`
