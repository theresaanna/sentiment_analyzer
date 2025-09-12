# Batch Inference Deployment Checklist for Railway

## Pre-Deployment Verification

### ✅ Code Changes Committed
- [x] `app/ml/batch_processor.py` - Core batch processing module
- [x] `app/ml/ml_sentiment_analyzer.py` - Enhanced with batch methods
- [x] `app/science/fast_sentiment_analyzer.py` - GPU optimization methods
- [x] `app/main/batch_routes.py` - New API endpoints
- [x] `app/config.py` - Batch processing configuration
- [x] `app/main/__init__.py` - Route registration
- [x] `requirements.txt` - Added psutil dependency

### ✅ Dependencies Added
- [x] `psutil==7.0.0` - For memory monitoring

## Railway Deployment Considerations

### Memory Management
The batch processing system includes automatic memory management:
- Dynamic batch sizing based on available memory
- Memory threshold set to 80% by default
- Automatic fallback to smaller batches if memory is limited

### Environment Variables (Optional Configuration)
You can set these in Railway's environment variables if needed:

```bash
# Batch Processing Configuration
BATCH_PROCESSING_ENABLED=true       # Enable/disable batch processing
DEFAULT_BATCH_SIZE=32                # Default batch size
MAX_BATCH_SIZE=128                   # Maximum batch size
MIN_BATCH_SIZE=8                     # Minimum batch size
DYNAMIC_BATCHING_ENABLED=true       # Enable dynamic batch sizing

# Memory Management
MEMORY_THRESHOLD=0.8                # Max memory usage (80%)
ENABLE_MEMORY_MONITORING=true       # Enable memory monitoring

# Performance Tuning
MAX_WORKERS=4                        # Parallel processing workers
PREFETCH_SIZE=2                      # Data prefetch buffer size
BUFFER_SIZE=100                      # Streaming buffer size
FLUSH_INTERVAL=1.0                   # Streaming flush interval (seconds)

# GPU (Railway doesn't have GPU by default)
ENABLE_GPU_OPTIMIZATION=false       # Disable GPU on Railway
ENABLE_MIXED_PRECISION=false        # Disable mixed precision
```

### Railway Resource Considerations

1. **CPU Usage**: Batch processing will use more CPU. Monitor usage and scale if needed.

2. **Memory Usage**: The system automatically adapts to available memory, but consider:
   - Railway's free tier has 512MB RAM limit
   - Hobby tier has 8GB RAM
   - Pro tier can go higher

3. **Timeout Settings**: For large batch jobs, ensure timeout is sufficient:
   - Already configured in `railway.json`: `--timeout 120`
   - May need adjustment for very large batches

### New API Endpoints

The following endpoints are now available:

1. **Batch Video Analysis**
   - `POST /api/batch/analyze`
   - Processes multiple YouTube videos in optimized batches
   - Returns batch_id for async processing

2. **Check Batch Status**
   - `GET /api/batch/status/<batch_id>`
   - Check progress of batch processing

3. **Get Batch Results**
   - `GET /api/batch/results/<batch_id>`
   - Retrieve completed batch analysis results

4. **Direct Text Batch Analysis**
   - `POST /api/batch/analyze_texts`
   - Analyze texts directly without YouTube fetching

5. **Streaming Analysis**
   - `POST /api/batch/streaming`
   - Real-time streaming comment analysis

### Testing After Deployment

1. **Basic Health Check**:
```bash
curl https://your-app.railway.app/health
```

2. **Test Batch Text Analysis**:
```bash
curl -X POST https://your-app.railway.app/api/batch/analyze_texts \
  -H "Content-Type: application/json" \
  -d '{
    "texts": ["Great video!", "Not so good", "Amazing content"],
    "batch_size": 32,
    "use_dynamic_batching": true
  }'
```

3. **Test Batch Video Analysis** (requires auth):
```bash
curl -X POST https://your-app.railway.app/api/batch/analyze \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "video_ids": ["VIDEO_ID_1", "VIDEO_ID_2"],
    "max_comments_per_video": 100,
    "batch_size": 32
  }'
```

### Monitoring Recommendations

1. **Check Railway Metrics Dashboard** for:
   - Memory usage spikes during batch processing
   - CPU utilization
   - Response times for batch endpoints

2. **Log Monitoring** - Watch for:
   - "Calculated optimal batch size" messages
   - "Batch inference completed" with throughput metrics
   - Any memory-related warnings

3. **Error Patterns to Watch**:
   - Out of memory errors → Reduce MAX_BATCH_SIZE
   - Timeout errors → Increase timeout or reduce batch size
   - Slow performance → Check if dynamic batching is enabled

### Rollback Plan

If issues occur:
1. The batch processing is isolated - core functionality remains intact
2. Set `BATCH_PROCESSING_ENABLED=false` to disable batch features
3. Previous single-item processing endpoints remain available
4. Can revert to previous commit if needed

### Post-Deployment Verification

1. Monitor first 24 hours for:
   - Memory usage patterns
   - Batch processing performance
   - Error rates

2. Optimize if needed:
   - Adjust batch sizes based on Railway's available memory
   - Tune worker counts for optimal performance
   - Consider caching frequently analyzed content

## Deployment Command

Railway will automatically deploy from the main branch when you push. If manual deployment is needed:

```bash
railway up
```

## Success Metrics

- ✅ Batch endpoints responding with 200 status
- ✅ Memory usage stays below 80% threshold
- ✅ Throughput improvement visible in logs (target: 5-10x)
- ✅ No increase in error rates
- ✅ Response times acceptable for batch operations

## Notes

- GPU optimization is included but won't be active on Railway (no GPU available)
- The system will automatically fall back to CPU processing
- Dynamic batching will adapt to Railway's container memory limits
- Consider using Railway's Pro tier for production workloads with high volume