from app.db import get_db_connection
import traceback

def debug_get_packages_step_by_step():
    """Test each step of the get_packages function for debugging"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        print("Step 1: Basic query execution")
        # Get basic package information with event type
        cursor.execute("""
            SELECT 
                p.package_id,
                p.package_name,
                COALESCE(et.event_type_name, 'Unknown') as event_type_name,
                p.event_type_id,
                COALESCE(p.capacity, 0) as capacity,
                COALESCE(p.description, '') as description,
                p.venue_id,
                COALESCE(v.venue_name, 'No Venue') as venue_name,
                p.gown_package_id,
                COALESCE(gp.gown_package_name, 'No Gown Package') as gown_package_name,
                COALESCE(p.additional_capacity_charges, 0) as additional_capacity_charges,
                COALESCE(p.charge_unit, 1) as charge_unit,
                COALESCE(p.total_price, 0) as total_price,
                p.created_at,
                COALESCE(p.status, 'Active') as status
            FROM event_packages p
            LEFT JOIN venues v ON p.venue_id = v.venue_id
            LEFT JOIN gown_package gp ON p.gown_package_id = gp.gown_package_id
            LEFT JOIN event_type et ON p.event_type_id = et.event_type_id
            WHERE UPPER(COALESCE(p.status, 'Active')) = 'ACTIVE'
            ORDER BY p.created_at DESC
            LIMIT 1
        """)
        rows = cursor.fetchall()
        
        if not rows:
            print("No packages found")
            return []
            
        print(f"Found {len(rows)} packages")
        print(f"First package: {rows[0]}")
        
        print("\nStep 2: Creating package objects")
        # Try just a simple package object
        packages = []
        for row in rows:
            try:
                package = {
                    'packageId': row[0],
                    'package_name': row[1],
                    'event_type_name': row[2],
                    'event_type_id': row[3],
                    'capacity': row[4],
                    'description': row[5],
                    'venue_id': row[6],
                    'venue_name': row[7],
                    'gown_package_id': row[8],
                    'gown_package_name': row[9],
                    'additional_capacity_charges': float(row[10]) if row[10] else 0,
                    'charge_unit': row[11],
                    'total_price': float(row[12]) if row[12] else 0,
                    'created_at': row[13].strftime('%Y-%m-%d') if row[13] else None,
                    'status': row[14]
                }
                print(f"Created package: {package}")
            except Exception as e:
                print(f"Error creating package: {e}")
                traceback.print_exc()
                continue
            
            print("\nStep 3: Getting suppliers")
            # Get suppliers for this package
            try:
                cursor.execute("""
                    SELECT 
                        s.supplier_id,
                        COALESCE(u.firstname, '') as firstname,
                        COALESCE(u.lastname, '') as lastname,
                        COALESCE(s.service, 'Unknown') as service,
                        COALESCE(s.price, 0) as price,
                        COALESCE(ps.remarks, '') as remarks
                    FROM event_package_services eps
                    LEFT JOIN package_service ps ON eps.package_service_id = ps.package_service_id
                    LEFT JOIN suppliers s ON ps.supplier_id = s.supplier_id
                    LEFT JOIN users u ON s.userid = u.userid
                    WHERE eps.package_id = %s
                """, (row[0],))
                
                package['suppliers'] = []
                supplier_rows = cursor.fetchall()
                print(f"Found {len(supplier_rows)} suppliers")
                for supplier_row in supplier_rows:
                    try:
                        supplier = {
                            'supplier_id': supplier_row[0],
                            'name': f"{supplier_row[1]} {supplier_row[2]}".strip(),
                            'service': supplier_row[3],
                            'price': float(supplier_row[4]) if supplier_row[4] else 0,
                            'remarks': supplier_row[5]
                        }
                        package['suppliers'].append(supplier)
                        print(f"Added supplier: {supplier}")
                    except Exception as e:
                        print(f"Error processing supplier row: {e}")
                        traceback.print_exc()
                        continue
            except Exception as e:
                print(f"Error querying suppliers: {e}")
                traceback.print_exc()
                
            print("\nStep 4: Getting additional services")
            # Get additional services for this package
            try:
                cursor.execute("""
                    SELECT 
                        a.add_service_id,
                        COALESCE(a.add_service_name, 'Unknown Service') as add_service_name,
                        COALESCE(a.add_service_price, 0) as add_service_price
                    FROM event_package_additional_services epas
                    LEFT JOIN additional_services a ON epas.add_service_id = a.add_service_id
                    WHERE epas.package_id = %s
                """, (row[0],))
                
                package['additional_services'] = []
                service_rows = cursor.fetchall()
                print(f"Found {len(service_rows)} additional services")
                for service_row in service_rows:
                    try:
                        service = {
                            'service_id': service_row[0],
                            'name': service_row[1],
                            'price': float(service_row[2]) if service_row[2] else 0
                        }
                        package['additional_services'].append(service)
                        print(f"Added service: {service}")
                    except Exception as e:
                        print(f"Error processing service row: {e}")
                        traceback.print_exc()
                        continue
            except Exception as e:
                print(f"Error querying additional services: {e}")
                traceback.print_exc()
            
            packages.append(package)
        
        print("\nStep 5: Final result")
        print(f"Total packages: {len(packages)}")
        return packages
    except Exception as e:
        print(f"Main function error: {e}")
        traceback.print_exc()
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    try:
        print("Starting detailed debug test...")
        packages = debug_get_packages_step_by_step()
        print("\nDebug test completed successfully")
    except Exception as e:
        print(f"Debug test failed: {e}")
        traceback.print_exc() 