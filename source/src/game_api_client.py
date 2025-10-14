import urllib.request
import urllib.error

TARGET_HOST = "http://localhost:1464"

def fetch_data(path: str):
    """Fetches data from the target OSRS API (localhost:1464)."""
    try:
        with urllib.request.urlopen(f"{TARGET_HOST}{path}") as response:
            return response.read().decode('utf-8')
    except urllib.error.URLError as e:
        print(f"Error connecting to {TARGET_HOST}: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None
