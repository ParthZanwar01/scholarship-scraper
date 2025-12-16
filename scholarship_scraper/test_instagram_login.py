import instaloader
import traceback
import requests

USERNAME = "parthzanwar112@gmail.com"
PASSWORD = "Parthtanish00!"

def test_login():
    print(f"Testing login for: {USERNAME}")
    print("-" * 50)
    
    # First, let's check if Instagram is even reachable
    print("Checking Instagram connectivity...")
    try:
        r = requests.get("https://www.instagram.com/", timeout=10)
        print(f"Instagram reachable: {r.status_code}")
    except Exception as e:
        print(f"Cannot reach Instagram: {e}")
        return
    
    L = instaloader.Instaloader()
    
    try:
        L.login(USERNAME, PASSWORD)
        print("SUCCESS! Login worked.")
    except instaloader.exceptions.BadCredentialsException as e:
        print(f"BAD CREDENTIALS: {e}")
    except instaloader.exceptions.ConnectionException as e:
        print(f"CONNECTION ERROR: {e}")
    except instaloader.exceptions.TwoFactorAuthRequiredException as e:
        print(f"2FA REQUIRED: {e}")
    except Exception as e:
        print(f"UNKNOWN ERROR TYPE: {type(e).__name__}")
        print(f"ERROR MESSAGE: {e}")
        print("-" * 50)
        print("This usually means:")
        print("1. Instagram flagged this login as suspicious")
        print("2. You need to open Instagram app/web and approve 'Was this you?'")
        print("3. Or try logging in manually once first to 'warm up' the account")

if __name__ == "__main__":
    test_login()
