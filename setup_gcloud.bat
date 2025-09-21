@echo off
echo Setting up Google Cloud for Echo Mind deployment...

echo Step 1: Login to Google Cloud
gcloud auth login

echo Step 2: Set the project
gcloud config set project echo-mind-472808

echo Step 3: Enable required APIs
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com

echo Step 4: Configure Docker authentication
gcloud auth configure-docker

echo Setup complete! You can now run deploy_to_cloud_run.bat

pause