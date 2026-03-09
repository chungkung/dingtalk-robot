import os
import sys
import time
import logging
import requests

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

import config.config as cfg


def check_health():
    try:
        url = f"http://localhost:{cfg.FLASK_PORT}/health"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            logger = logging.getLogger(__name__)
            logger.info(f"Health check: {data}")
            return True
        return False
    except Exception as e:
        print(f"Health check failed: {e}")
        return False


def restart_service():
    print("Restarting service...")
    os.system(f"taskkill /F /IM python.exe 2>nul")
    time.sleep(2)
    
    python_exe = os.path.join(PROJECT_ROOT, "venv", "Scripts", "python.exe")
    app_path = os.path.join(PROJECT_ROOT, "src", "app.py")
    
    if os.path.exists(python_exe):
        os.system(f'start "" "{python_exe}" "{app_path}"')
    else:
        os.system(f'start "" python "{app_path}"')


def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger = logging.getLogger(__name__)
    logger.info("Starting health check monitor...")
    
    while True:
        if not check_health():
            logger.warning("Service not healthy, attempting restart...")
            restart_service()
        
        time.sleep(cfg.HEALTH_CHECK_INTERVAL)


if __name__ == "__main__":
    main()
