from app.db import get_db_connection

def debug_get_packages():
    """Test version of get_packages for debugging"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get basic package information with event type
        cursor.execute("""
            SELECT 
                p.package_id,
                p.package_name,
                COALESCE(et.event_type_name, 'Unknown') as event_type_name,
                p.event_type_id
            FROM event_packages p
            LEFT JOIN event_type et ON p.event_type_id = et.event_type_id
            LIMIT 1
        """)
        rows = cursor.fetchall()
        
        if not rows:
            print("No packages found")
            return []
            
        print(f"Found {len(rows)} packages")
        print(f"First package: {rows[0]}")
        
        # Try just a simple package object
        packages = []
        for row in rows:
            try:
                package = {
                    'packageId': row[0],
                    'package_name': row[1],
                    'event_type_name': row[2],
                    'event_type_id': row[3]
                }
                packages.append(package)
            except Exception as e:
                print(f"Error processing package row: {e}")
                continue
        
        print("Successfully created package objects")
        return packages
    except Exception as e:
        print(f"Error in debug_get_packages: {e}")
        raise e
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    try:
        print("Starting debug test...")
        packages = debug_get_packages()
        print(f"Packages: {packages}")
        print("Debug test completed successfully")
    except Exception as e:
        print(f"Debug test failed: {e}") 