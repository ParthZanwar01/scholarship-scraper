#!/bin/bash
# VPS Setup Script for Scholarship Scraper
# Run this on your DigitalOcean Droplet (Ubuntu 22.04)

set -e

echo ">>> Updating System..."
sudo apt-get update && sudo apt-get upgrade -y

echo ">>> Installing Docker..."
# Add Docker's official GPG key:
sudo apt-get install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# Add the repository to Apt sources:
echo \
  "deb [arch=\"$(dpkg --print-architecture)\" signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo \"$VERSION_CODENAME\") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

echo ">>> Verifying Docker..."
sudo docker --version

echo ">>> Setup Complete!"
echo "Next steps:"
echo "1. Clone your repository: git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git"
echo "2. CD into it: cd YOUR_REPO"
echo "3. Run: docker compose up -d --build"
