import paramiko
import time
import sys

# Configuration
HOSTNAME = "64.23.231.89"
USERNAME = "root"
PASSWORD = "ParthyPoo123Here" # Provided by user

def deploy():
    print(f"Connecting to {HOSTNAME}...")
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(HOSTNAME, username=USERNAME, password=PASSWORD)
        print("Connected successfully!")
    except Exception as e:
        print(f"Failed to connect: {e}")
        return

    # Chain commands to preserve state (cd)
    full_command = (
        "if [ ! -d 'scholarship-scraper' ]; then git clone https://github.com/ParthZanwar01/scholarship-scraper.git; fi && "
        "cd scholarship-scraper && "
        "if [ ! -d '.git' ]; then cd .. && rm -rf scholarship-scraper && git clone https://github.com/ParthZanwar01/scholarship-scraper.git && cd scholarship-scraper; fi && "
        "echo '>>> Pulling latest code...' && "
        "git fetch origin && "
        "git reset --hard origin/main && "
        "echo '>>> Creating .env file...' && "
        "echo 'INSTAGRAM_USERNAME=parthzanwar112gmail.com' > .env && "
        "echo 'INSTAGRAM_PASSWORD=Parthtanish00!' >> .env && "
        "echo 'DATABASE_URL=sqlite:///./scholarships.db' >> .env && "
        "echo 'REDIS_URL=redis://redis:6379/0' >> .env && "
        "echo '>>> Restarting Docker Containers...' && "
        "docker compose down && "
        "docker compose up -d --build && "
        "echo '>>> Checking status...' && "
        "sleep 5 && "
        "docker compose ps"
    )

    print(f"\n[REMOTE] Executing deployment sequence...")
    stdin, stdout, stderr = client.exec_command(full_command)
    
    # stream output
    while not stdout.channel.exit_status_ready():
        if stdout.channel.recv_ready():
            sys.stdout.write(stdout.channel.recv(1024).decode())
        if stderr.channel.recv_ready():
            sys.stderr.write(stderr.channel.recv(1024).decode())
    
    # flush remaining
    print(stdout.read().decode())
    print(stderr.read().decode())
    
    if stdout.channel.recv_exit_status() == 0:
        print("\n--------------------------")
        print("DEPLOYMENT COMPLETE!")
        print("--------------------------")
    else:
        print("\nDeployment Failed.")
    
    client.close()

if __name__ == "__main__":
    deploy()
