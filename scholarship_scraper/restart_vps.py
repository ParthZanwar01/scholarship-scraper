import paramiko
import sys

HOSTNAME = "64.23.231.89"
USERNAME = "root"
PASSWORD = "ParthyPoo123Here" 

def restart_containers():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOSTNAME, username=USERNAME, password=PASSWORD)
    
    print("Restarting containers...")
    stdin, stdout, stderr = client.exec_command("cd scholarship-scraper && docker compose up -d")
    
    out = stdout.read().decode()
    err = stderr.read().decode()
    
    print("STDOUT:", out)
    print("STDERR:", err)
    
    client.close()

if __name__ == "__main__":
    restart_containers()
