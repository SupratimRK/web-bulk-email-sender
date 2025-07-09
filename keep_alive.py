import requests
import time
import os
import threading
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class KeepAliveService:
    def __init__(self, app_url=None, ping_interval=300):  # 5 minutes
        self.app_url = app_url or os.getenv('RENDER_EXTERNAL_URL')
        self.ping_interval = ping_interval
        self.running = False
        self.thread = None
        
    def start(self):
        """Start the keep-alive service"""
        if not self.app_url:
            logger.warning("No app URL provided, keep-alive service not started")
            return
            
        if self.running:
            logger.info("Keep-alive service already running")
            return
            
        self.running = True
        self.thread = threading.Thread(target=self._ping_loop, daemon=True)
        self.thread.start()
        logger.info(f"Keep-alive service started, pinging {self.app_url} every {self.ping_interval} seconds")
    
    def stop(self):
        """Stop the keep-alive service"""
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)
        logger.info("Keep-alive service stopped")
    
    def _ping_loop(self):
        """Main ping loop"""
        while self.running:
            try:
                # Wait first, then ping
                time.sleep(self.ping_interval)
                if not self.running:
                    break
                    
                # Send a simple GET request to keep the app alive
                response = requests.get(
                    f"{self.app_url}/", 
                    timeout=30,
                    headers={'User-Agent': 'KeepAlive-Service'}
                )
                
                if response.status_code == 200:
                    logger.info(f"Keep-alive ping successful: {response.status_code}")
                else:
                    logger.warning(f"Keep-alive ping returned: {response.status_code}")
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"Keep-alive ping failed: {e}")
            except Exception as e:
                logger.error(f"Unexpected error in keep-alive service: {e}")

# Global instance
keep_alive_service = KeepAliveService()

def start_keep_alive():
    """Start the keep-alive service if in production"""
    if os.getenv('FLASK_ENV') == 'production' and os.getenv('RENDER_EXTERNAL_URL'):
        keep_alive_service.start()

def stop_keep_alive():
    """Stop the keep-alive service"""
    keep_alive_service.stop()
