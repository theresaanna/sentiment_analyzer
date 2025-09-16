# URGENT: Fix Worker Healthcheck Failure

## The Problem
The worker service is failing because Railway is trying to run a healthcheck on it. Workers don't have web servers, so healthchecks will always fail.

## Quick Fix (Do This Now)

1. **Go to Railway Dashboard**
   https://railway.app/project/7cfed323-856d-48bc-9135-4040df5d83ef

2. **Click on the worker service** (triumphant-peace)

3. **Go to Settings → Deploy tab**

4. **Disable the Healthcheck:**
   - Find "Healthcheck Path"
   - Clear it (leave it empty)
   - Or set "Healthcheck" toggle to OFF if available

5. **Set the Start Command:**
   - Custom Start Command: `python analysis_worker.py`
   - This overrides the Dockerfile CMD

6. **Redeploy the service:**
   - Click "Redeploy" or
   - The service will auto-redeploy when you save settings

## Alternative: Use Different Builder

If the above doesn't work, in the worker service settings:

1. **Change Build Settings:**
   - Builder: NIXPACKS (not Dockerfile)
   - Start Command: `python analysis_worker.py`
   - No healthcheck

## Verification

After fixing:
- Worker logs should show: "Analysis worker started"
- No healthcheck attempts in logs
- Jobs should process from the queue

## Long-term Solution

We should create a separate Dockerfile.worker without the web server CMD, but the above fix will work immediately.