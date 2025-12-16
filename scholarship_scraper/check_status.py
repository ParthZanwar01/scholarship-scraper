import paramiko
import sys

HOSTNAME = "64.23.231.89"
USERNAME = "root"
PASSWORD = "ParthyPoo123Here" 

def check_status():
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(HOSTNAME, username=USERNAME, password=PASSWORD)
        
        # Check status of containers
        stdin, stdout, stderr = client.exec_command("cd scholarship-scraper && docker compose ps -a")
        print("--- DOCKER PS ---")
        print(stdout.read().decode())
        print("STDERR:", stderr.read().decode())
        
        # Check web logs if worker is empty, maybe web component crashed?
        stdin, stdout, stderr = client.exec_command("cd scholarship-scraper && docker compose logs --tail=50 web")
        print("\n--- WEB SCRAPER LOGS ---")
        print(stdout.read().decode())
        
        client.close()
    except Exception as e:
        print(e)

if __name__ == "__main__":
    check_status()
