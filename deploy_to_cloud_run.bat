@echo off
echo Deploying Echo Mind to Google Cloud Run...

REM Build and deploy to Cloud Run
gcloud run deploy echo-mind ^
  --source . ^
  --platform managed ^
  --region us-central1 ^
  --allow-unauthenticated ^
  --port 8080 ^
  --memory 1Gi ^
  --cpu 1 ^
  --timeout 300 ^
  --project echo-mind-472808

echo Deployment complete!
echo Your backend will be available at: https://echo-mind-[hash]-uc.a.run.app

pause