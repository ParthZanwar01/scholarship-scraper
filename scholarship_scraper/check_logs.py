import paramiko
import sys

# Configuration
HOSTNAME = "64.23.231.89"
USERNAME = "root"
PASSWORD = "ParthyPoo123Here" 

def check_logs():
    print(f"Connecting to {HOSTNAME}...")
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(HOSTNAME, username=USERNAME, password=PASSWORD)
        print("Connected.")
    except Exception as e:
        print(f"Failed to connect: {e}")
        return

    # Check worker logs
    cmd = "cd scholarship-scraper && docker compose logs --tail=100 worker"
    print(f"[REMOTE] {cmd}")
    stdin, stdout, stderr = client.exec_command(cmd)
    
    out = stdout.read().decode()
    err = stderr.read().decode()
    
    print("--- WORKER LOGS ---")
    print(out)
    print("-------------------")
    if err:
        print("STDERR:", err)
    
    client.close()

if __name__ == "__main__":
    check_logs()
