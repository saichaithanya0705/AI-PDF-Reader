@echo off
echo =============================================
echo   Digital Ocean Deployment - Upload Files
echo =============================================
echo.

set SSH_KEY=C:\Users\SAI\.ssh\id_ed25519
set DROPLET_IP=64.227.179.63
set DROPLET_USER=root
set REMOTE_PATH=/var/www/pdfapp

echo [1] Creating temporary deployment folder...
if exist deploy_temp rmdir /s /q deploy_temp
mkdir deploy_temp

echo [2] Copying application files (excluding venv_new and node_modules)...
xcopy /E /I /Y backend deploy_temp\backend\ /EXCLUDE:exclude.txt
xcopy /E /I /Y frontend deploy_temp\frontend\ /EXCLUDE:exclude.txt
copy *.sh deploy_temp\
copy *.service deploy_temp\
copy *.conf deploy_temp\
copy *.txt deploy_temp\
copy *.py deploy_temp\
copy .env deploy_temp\
copy .env.production deploy_temp\
copy DEPLOY_DIGITALOCEAN.md deploy_temp\

echo [3] Uploading files to droplet...
scp -i %SSH_KEY% -r -o StrictHostKeyChecking=no deploy_temp/* %DROPLET_USER%@%DROPLET_IP%:%REMOTE_PATH%/

echo [4] Cleaning up...
rmdir /s /q deploy_temp

echo.
echo ✅ Upload complete!
echo.
echo Next steps:
echo 1. SSH into droplet: ssh -i %SSH_KEY% %DROPLET_USER%@%DROPLET_IP%
echo 2. Run setup: cd /var/www/pdfapp && sudo bash setup_droplet.sh
echo.
