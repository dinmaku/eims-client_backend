from app.models import get_packages
import json

def is_json_serializable(obj):
    try:
        json.dumps(obj)
        return True
    except (TypeError, OverflowError):
        return False

def find_non_serializable(obj, path=''):
    if isinstance(obj, dict):
        for key, value in obj.items():
            if not is_json_serializable(value):
                new_path = f"{path}.{key}" if path else key
                print(f"Non-serializable value at {new_path}: {type(value)}")
                find_non_serializable(value, new_path)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            if not is_json_serializable(item):
                new_path = f"{path}[{i}]"
                print(f"Non-serializable value at {new_path}: {type(item)}")
                find_non_serializable(item, new_path)

try:
    print("Fetching packages...")
    packages = get_packages()
    
    print(f"Got {len(packages)} packages")
    print("Type of packages:", type(packages))
    
    print("Checking if packages are JSON serializable...")
    if is_json_serializable(packages):
        print("Packages are JSON serializable")
    else:
        print("Packages are NOT JSON serializable")
        print("Finding non-serializable values...")
        find_non_serializable(packages)
        
        # Check each package individually
        for i, package in enumerate(packages):
            print(f"Checking package {i}...")
            if is_json_serializable(package):
                print(f"Package {i} is serializable")
            else:
                print(f"Package {i} is NOT serializable")
                find_non_serializable(package)
                
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc() 