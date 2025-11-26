from flask import Flask, jsonify, request
from app.models import get_packages
import logging
import json

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create a Flask application for testing
app = Flask(__name__)

@app.route('/test-packages', methods=['GET'])
def test_packages_route():
    try:
        # Get packages directly from the model
        packages = get_packages()
        # Return them directly without additional processing
        return jsonify(packages), 200
    except Exception as e:
        logger.error(f"Error fetching packages: {e}")
        return jsonify({
            'message': 'An error occurred while fetching packages',
            'error': str(e)
        }), 500

if __name__ == '__main__':
    # Run the Flask application with debugging
    with app.test_client() as client:
        print("Testing /test-packages endpoint...")
        response = client.get('/test-packages')
        
        print(f"Status code: {response.status_code}")
        if response.status_code == 200:
            print("Success!")
            print(f"Response length: {len(response.data)}")
        else:
            print(f"Error: {response.data.decode('utf-8')}")
            
    print("Done!") 