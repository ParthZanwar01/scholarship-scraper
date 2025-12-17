#!/usr/bin/env python3
"""Deploy new files to Digital Ocean server."""

import paramiko
import os

# Configuration
HOSTNAME = "64.23.231.89"
USERNAME = "root"
PASSWORD = "ParthyPoo123Here"
REMOTE_BASE = "/root/scholarship-scraper/scholarship_scraper"

# Files to upload
LOCAL_BASE = "/Users/parthzanwar/Desktop/Webscraper for Scholarships/scholarship_scraper"
FILES = [
    ("processors/url_filter.py", "processors/url_filter.py"),
    ("processors/content_classifier.py", "processors/content_classifier.py"),
    ("processors/media_processor.py", "processors/media_processor.py"),
    ("scrapers/tor_media_scraper.py", "scrapers/tor_media_scraper.py"),
    ("scrapers/instagram_enhanced.py", "scrapers/instagram_enhanced.py"),
    ("scrapers/facebook_enhanced.py", "scrapers/facebook_enhanced.py"),
    ("scrapers/tiktok_enhanced.py", "scrapers/tiktok_enhanced.py"),
    ("scrapers/rss_feeds.py", "scrapers/rss_feeds.py"),
    ("app/main.py", "app/main.py"),
    ("app/tasks.py", "app/tasks.py"),
]

def deploy():
    print(f"Connecting to {HOSTNAME}...")
    
    # SSH connection
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOSTNAME, username=USERNAME, password=PASSWORD)
    print("✓ Connected!")
    
    # SFTP for file transfer
    sftp = ssh.open_sftp()
    
    # Upload files
    for local_rel, remote_rel in FILES:
        local_path = os.path.join(LOCAL_BASE, local_rel)
        remote_path = f"{REMOTE_BASE}/{remote_rel}"
        
        print(f"Uploading {local_rel}...")
        try:
            sftp.put(local_path, remote_path)
            print(f"  ✓ {remote_rel}")
        except Exception as e:
            print(f"  ✗ Failed: {e}")
    
    sftp.close()
    
    # Restart docker
    print("\nRestarting Docker containers...")
    stdin, stdout, stderr = ssh.exec_command(
        "cd /root/scholarship-scraper && docker compose restart"
    )
    print(stdout.read().decode())
    print(stderr.read().decode())
    
    # Check status
    print("\nChecking container status...")
    stdin, stdout, stderr = ssh.exec_command(
        "cd /root/scholarship-scraper && docker compose ps"
    )
    print(stdout.read().decode())
    
    ssh.close()
    print("\n✓ Deployment complete!")

if __name__ == "__main__":
    deploy()
