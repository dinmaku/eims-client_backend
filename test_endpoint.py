from flask import Flask
from app import create_app
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

try:
    app = create_app()
    
    with app.test_client() as client:
        print("Testing /created-packages endpoint...")
        response = client.get('/created-packages')
        print(f"Status code: {response.status_code}")
        if response.status_code == 200:
            print("Success!")
            print(f"Response length: {len(response.data)}")
        else:
            print(f"Error: {response.data.decode('utf-8')}")
except Exception as e:
    print(f"Exception: {e}")
    import traceback
    traceback.print_exc() 