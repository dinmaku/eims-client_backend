# models.py

import hashlib
from .db import get_db_connection
import logging
from datetime import date, time, datetime



logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def check_user(identifier, password):
    """
    Checks if the user exists using either email or username.
    :param identifier: email or username of the user
    :param password: plaintext password to verify
    :return: Tuple (is_valid, user_type)
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    hashed_password = hash_password(password)

    try:
        # Check for user by email or username
        cursor.execute(
            "SELECT password, user_type FROM users WHERE email = %s OR username = %s",
            (identifier, identifier)
        )
        user = cursor.fetchone()

        # Ensure user exists and password matches
        if user and user[0] == hashed_password:
            return True, user[1]  # Return True and user_type (e.g., admin, staff, client)
        return False, None
    finally:
        cursor.close()
        conn.close()

def create_user(first_name, last_name, username, email, contact_number, password, user_type='Client', address=''):
    conn = get_db_connection()
    cursor = conn.cursor()
    hashed_password = hash_password(password)
    
    try:
        # Check if email exists
        cursor.execute("SELECT email FROM users WHERE email = %s", (email,))
        if cursor.fetchone():
            return False  # Email exists
        
        # Insert new user
        cursor.execute(
            """INSERT INTO users (firstname, lastname, username, email, contactnumber, password, user_type, address)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",  # Correct number of placeholders
            (first_name, last_name, username, email, contact_number, hashed_password, user_type, address)
        )
        conn.commit()
        return True
    finally:
        cursor.close()
        conn.close()





def get_user_wishlist(userid):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            WITH outfit_details AS (
                SELECT 
                    wo.wishlist_id,
                    ARRAY_AGG(
                        ARRAY[
                            COALESCE(o.outfit_id::text, gpo.outfit_id::text),
                            COALESCE(o.outfit_name, gpo_outfit.outfit_name),
                            COALESCE(o.outfit_type, gpo_outfit.outfit_type),
                            COALESCE(o.outfit_color, gpo_outfit.outfit_color),
                            COALESCE(o.outfit_desc, gpo_outfit.outfit_desc),
                            COALESCE(wo.price::text, gpo_outfit.rent_price::text),
                            COALESCE(o.outfit_img, gpo_outfit.outfit_img),
                            COALESCE(wo.status, 'Pending'),
                            COALESCE(wo.remarks, '')
                        ]
                    ) as outfit_details
                FROM wishlist_outfits wo
                LEFT JOIN outfits o ON wo.outfit_id = o.outfit_id
                LEFT JOIN gown_package gp ON wo.gown_package_id = gp.gown_package_id
                LEFT JOIN gown_package_outfits gpo ON gp.gown_package_id = gpo.gown_package_id
                LEFT JOIN outfits gpo_outfit ON gpo.outfit_id = gpo_outfit.outfit_id
                GROUP BY wo.wishlist_id
            ),
            supplier_details AS (
                SELECT 
                    ws.wishlist_id,
                    array_agg(s.supplier_id ORDER BY s.supplier_id) as supplier_ids,
                    array_agg(u.firstname || ' ' || u.lastname ORDER BY s.supplier_id) as supplier_names,
                    array_agg(s.service ORDER BY s.supplier_id) as services,
                    array_agg(ws.price ORDER BY s.supplier_id) as prices,
                    array_agg(ws.status ORDER BY s.supplier_id) as statuses,
                    array_agg(ws.remarks ORDER BY s.supplier_id) as remarks
                FROM wishlist_suppliers ws
                JOIN suppliers s ON ws.supplier_id = s.supplier_id
                JOIN users u ON s.userid = u.userid
                GROUP BY ws.wishlist_id
            ),
            additional_service_details AS (
                SELECT 
                    was.wishlist_id,
                    array_agg(ads.add_service_id ORDER BY ads.add_service_id) as service_ids,
                    array_agg(ads.add_service_name ORDER BY ads.add_service_id) as service_names,
                    array_agg(ads.add_service_description ORDER BY ads.add_service_id) as service_descriptions,
                    array_agg(was.price ORDER BY ads.add_service_id) as service_prices,
                    array_agg(was.status ORDER BY ads.add_service_id) as service_statuses,
                    array_agg(was.remarks ORDER BY ads.add_service_id) as service_remarks
                FROM wishlist_additional_services was
                JOIN additional_services ads ON was.add_service_id = ads.add_service_id
                GROUP BY was.wishlist_id
            ),
            venue_details AS (
                SELECT 
                    wv.wishlist_id,
                    v.venue_id,
                    v.venue_name,
                    v.location,
                    wv.price as venue_price,
                    v.description as venue_description,
                    v.venue_capacity,
                    wv.status as venue_status,
                    wv.remarks as venue_remarks
                FROM wishlist_venues wv
                JOIN venues v ON wv.venue_id = v.venue_id
            )
            SELECT 
                e.events_id, e.event_name, e.event_type, e.event_theme, e.event_color, 
                e.schedule, e.start_time, e.end_time, e.status as event_status,
                wp.wishlist_id, wp.package_name, wp.capacity, wp.description as package_description,
                wp.total_price, wp.additional_capacity_charges, wp.charge_unit, wp.status as package_status,
                vd.venue_id, vd.venue_name, vd.location, vd.venue_price, vd.venue_description,
                vd.venue_capacity, vd.venue_status, vd.venue_remarks,
                gp.gown_package_name, gp.gown_package_price,
                od.outfit_details,
                sd.supplier_ids, sd.supplier_names, sd.services, sd.prices as supplier_prices,
                sd.statuses as supplier_statuses, sd.remarks as supplier_remarks,
                asd.service_ids, asd.service_names, asd.service_descriptions,
                asd.service_prices, asd.service_statuses, asd.service_remarks
            FROM events e
            JOIN wishlist_packages wp ON e.events_id = wp.events_id
            LEFT JOIN venue_details vd ON wp.wishlist_id = vd.wishlist_id
            LEFT JOIN gown_package gp ON wp.gown_package_id = gp.gown_package_id
            LEFT JOIN outfit_details od ON wp.wishlist_id = od.wishlist_id
            LEFT JOIN supplier_details sd ON wp.wishlist_id = sd.wishlist_id
            LEFT JOIN additional_service_details asd ON wp.wishlist_id = asd.wishlist_id
            WHERE e.userid = %s AND wp.status != 'Cancelled'
            ORDER BY wp.created_at DESC
        """, (userid,))

        columns = [desc[0] for desc in cursor.description]
        wishlist = cursor.fetchall()

        result = []
        for item in wishlist:
            item_dict = dict(zip(columns, item))
            
            # Format time objects
            if isinstance(item_dict['start_time'], time):
                item_dict['start_time'] = item_dict['start_time'].strftime("%H:%M:%S")
            if isinstance(item_dict['end_time'], time):
                item_dict['end_time'] = item_dict['end_time'].strftime("%H:%M:%S")
            
            # Format venue data
            if item_dict.get('venue_id'):
                item_dict['venue'] = {
                    'venue_id': item_dict['venue_id'],
                    'venue_name': item_dict['venue_name'],
                    'location': item_dict['location'],
                    'venue_price': float(item_dict['venue_price']) if item_dict['venue_price'] else 0,
                    'description': item_dict['venue_description'],
                    'venue_capacity': item_dict['venue_capacity'],
                    'status': item_dict['venue_status'],
                    'remarks': item_dict['venue_remarks']
                }
            else:
                item_dict['venue'] = None
            
            # Format outfit details with enhanced logging
            logger.info(f"Processing event {item_dict.get('event_name')} (ID: {item_dict.get('events_id')})")
            logger.info(f"Gown package info - Name: {item_dict.get('gown_package_name')}, Price: {item_dict.get('gown_package_price')}")
            
            if item_dict.get('outfit_details'):
                try:
                    logger.info(f"Raw outfit_details: {item_dict['outfit_details']}")
                    if isinstance(item_dict['outfit_details'], list):
                        outfits = []
                        for details in item_dict['outfit_details']:
                            if details is not None:
                                outfit = {
                                    'outfit_id': details[0] if len(details) > 0 else None,
                                    'outfit_name': details[1] if len(details) > 1 else None,
                                    'outfit_type': details[2] if len(details) > 2 else None,
                                    'outfit_color': details[3] if len(details) > 3 else None,
                                    'outfit_desc': details[4] if len(details) > 4 else None,
                                    'rent_price': details[5] if len(details) > 5 else None,
                                    'outfit_img': details[6] if len(details) > 6 else None,
                                    'status': details[7] if len(details) > 7 else None,
                                    'remarks': details[8] if len(details) > 8 else None
                                }
                                logger.info(f"Processed outfit: {outfit}")
                                outfits.append(outfit)
                        item_dict['outfits'] = outfits
                        logger.info(f"Total outfits processed: {len(outfits)}")
                    else:
                        logger.warning(f"outfit_details is not a list: {type(item_dict['outfit_details'])}")
                        item_dict['outfits'] = []
                except Exception as e:
                    logger.error(f"Error processing outfit details: {str(e)}")
                    item_dict['outfits'] = []
            else:
                logger.info("No outfit_details found for this event")
                item_dict['outfits'] = []

            # Format supplier details
            if item_dict.get('supplier_ids'):
                item_dict['suppliers'] = [
                    {
                        'supplier_id': supplier_id,
                        'name': name,
                        'service': service,
                        'price': price,
                        'status': status,
                        'remarks': remarks
                    }
                    for supplier_id, name, service, price, status, remarks in zip(
                        item_dict['supplier_ids'],
                        item_dict['supplier_names'],
                        item_dict['services'],
                        item_dict['supplier_prices'],
                        item_dict['supplier_statuses'],
                        item_dict['supplier_remarks']
                    )
                ]
            else:
                item_dict['suppliers'] = []

            # Format additional services
            if item_dict.get('service_ids'):
                item_dict['additional_services'] = [
                    {
                        'add_service_id': service_id,
                        'add_service_name': name,
                        'add_service_description': description,
                        'add_service_price': price,
                        'status': status,
                        'remarks': remarks
                    }
                    for service_id, name, description, price, status, remarks in zip(
                        item_dict['service_ids'],
                        item_dict['service_names'],
                        item_dict['service_descriptions'],
                        item_dict['service_prices'],
                        item_dict['service_statuses'],
                        item_dict['service_remarks']
                    )
                ]
            else:
                item_dict['additional_services'] = []

            # Clean up temporary fields
            fields_to_remove = [
                'outfit_details',
                'supplier_ids', 'supplier_names', 'services', 'supplier_prices',
                'supplier_statuses', 'supplier_remarks',
                'service_ids', 'service_names', 'service_descriptions',
                'service_prices', 'service_statuses', 'service_remarks',
                'venue_id', 'venue_name', 'location', 'venue_price', 'venue_description',
                'venue_capacity', 'venue_status', 'venue_remarks'
            ]
            for field in fields_to_remove:
                item_dict.pop(field, None)

            result.append(item_dict)

        return result

    except Exception as e:
        logger.error(f"Error in get_user_wishlist: {str(e)}")
        raise e
    finally:
        cursor.close()
        conn.close()

def add_event_entry(wishlist_id, schedule, start_time, end_time, status):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            INSERT INTO events (wishlist_id, schedule, start_time, end_time, status)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (wishlist_id, schedule, start_time, end_time, status)
        )
        conn.commit()
        return True
    except Exception as e:
        # Use logger instead of app.logger
        logger.error(f"Error adding event: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()
    
        

def check_user_exists(userid):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT userid FROM users WHERE userid = %s", (userid,))
        user = cursor.fetchone()
        return user is not None
    finally:
        cursor.close()
        conn.close()


def get_user_id_by_email(email):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT userid FROM users WHERE email = %s", (email,))
        result = cursor.fetchone()
        return result[0] if result else None
    except Exception as e:
        logger.error(f"Error getting user ID by email: {str(e)}")
        raise
    finally:
        cursor.close()
        conn.close()

        # Outfit Model
def create_outfit(outfit_name, outfit_type, outfit_color, outfit_desc, rent_price, status, outfit_img):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO outfits (outfit_name, outfit_type, outfit_color, outfit_desc, rent_price, status, outfit_img)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (outfit_name, outfit_type, outfit_color, outfit_desc, rent_price, status, outfit_img))
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Error creating outfit: {e}")
        return False
    finally:
        cursor.close()
        conn.close()

# Outfit Archive Model
def create_outfit_archive(outfit_id, creation_address, creation_date, owner, retail_price):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO outfit_archive (outfit_id, creation_address, creation_date, owner, retail_price)
            VALUES (%s, %s, %s, %s, %s)
        """, (outfit_id, creation_address, creation_date, owner, retail_price))
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Error creating outfit archive: {e}")
        return False
    finally:
        cursor.close()
        conn.close()

# Booked Outfit Model
def book_outfit(userid, outfit_id, pickup_date, return_date, status, additional_charges):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO booked_outfit (userid, outfit_id, pickup_date, return_date, status, additional_charges)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (userid, outfit_id, pickup_date, return_date, status, additional_charges))
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Error booking outfit: {e}")
        return False
    finally:
        cursor.close()
        conn.close()

# Fetch outfits
def get_outfits():
    conn = get_db_connection()  # Assuming you have a function to get the DB connection
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM outfits")
        outfits = cursor.fetchall()
        if outfits:
            return [
                {
                    'outfit_id': item[0],
                    'outfit_name': item[1],
                    'outfit_type': item[2],
                    'outfit_color': item[3],
                    'outfit_desc': item[4],
                    'rent_price': item[5],
                    'status': item[6],
                    'outfit_img': item[7],
                    'size': item[8],
                    'weight': item[9],
                }
                for item in outfits
            ]
        else:
            return []  # No outfits found
    except Exception as e:
        logger.error(f"Error fetching outfits: {e}")
        return []
    finally:
        cursor.close()
        conn.close()

# Fetch a specific outfit by ID
def get_outfit_by_id(outfit_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT * FROM outfits WHERE outfit_id = %s", (outfit_id,))
        outfit = cursor.fetchone()
        if outfit:
            return {
                'outfit_id': outfit[0],
                'outfit_name': outfit[1],
                'outfit_type': outfit[2],
                'outfit_color': outfit[3],
                'outfit_desc': outfit[4],
                'rent_price': outfit[5],
                'status': outfit[6],
                'outfit_img': outfit[7],
            }
        return None
    finally:
        cursor.close()
        conn.close()

# Fetch wishlist by users
def get_booked_wishlist_by_user(userid):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT events_id, userid, event_name, event_type, event_theme, event_color, venue, schedule, start_time, end_time, status
            FROM events
            WHERE userid = %s
        """, (userid,))
        events = cursor.fetchall()
        if events:
            return [
                {
                    'events_id': item[0],
                    'userid': item[1],
                    'event_name': item[2],
                    'event_type': item[3],
                    'event_theme': item[4],
                    'event_color': item[5],
                    'venue': item[6],
                    'schedule': item[7],
                    'start_time': item[8],
                    'end_time': item[9],
                    'status': item[10]
                }
                for item in events
            ]
        else:
            return []  # No events found for the user
    except Exception as e:
        logger.error(f"Error fetching events for user {userid}: {e}")
        return []
    finally:
        cursor.close()
        conn.close()

# Delete wishlist and related events
def delete_booked_wishlist(events_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # First, delete related events (to avoid foreign key violation)
        cursor.execute("""DELETE FROM events WHERE events_id = %s""", (events_id,))
        conn.commit()

        return True
    except Exception as e:
        logger.error(f"Error deleting event item {events_id}: {e}")
        conn.rollback()  # Rollback in case of error
        return False
    finally:
        cursor.close()
        conn.close()



def get_booked_outfits():
    conn = get_db_connection()  # Assuming you have a function to get the DB connection
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM booked_outfit")
        booked_outfits = cursor.fetchall()
        
        if booked_outfits:
            return [
                {
                    'outfit_booked_id': item[0],
                    'userid': item[1],
                    'outfit_id': item[2],
                    'pickup_date': item[3],
                    'return_date': item[4],
                    'status': item[5],
                    'additional_charges': item[6]
                }
                for item in booked_outfits
            ]
        else:
            return []  # No booked outfits found
    except Exception as e:
        logger.error(f"Error fetching booked outfits: {e}")
        return []
    finally:
        cursor.close()
        conn.close()

def get_booked_outfits_by_user(userid):
    booked_outfits = get_booked_outfits()
    return [outfit for outfit in booked_outfits if outfit['userid'] == userid]



#package models

def get_client_packages():
    """
    Get packages formatted for the client-side application.
    Only returns active packages regardless of venue and gown package status.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
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
        """)
        rows = cursor.fetchall()
        
        if not rows:
            print("No packages found")
            return []
            
        # Convert rows to dictionaries
        packages = []
        for row in rows:
            package = {
                'package_id': row[0],
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
                'status': row[14],
                'suppliers': [],
                'additional_services': []
            }
            
            # Get suppliers for this package (include all suppliers regardless of status)
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
            
            supplier_rows = cursor.fetchall()
            for supplier_row in supplier_rows:
                try:
                    if supplier_row[0] is not None:  # Only add if supplier_id is not NULL
                        package['suppliers'].append({
                            'supplier_id': supplier_row[0],
                            'name': f"{supplier_row[1]} {supplier_row[2]}".strip(),
                            'service': supplier_row[3],
                            'price': float(supplier_row[4]) if supplier_row[4] else 0,
                            'remarks': supplier_row[5]
                        })
                except Exception as e:
                    print(f"Error processing supplier row: {e}")
                    continue
                
            # Get additional services for this package (include all services regardless of status)
            cursor.execute("""
                SELECT 
                    a.add_service_id,
                    COALESCE(a.add_service_name, 'Unknown Service') as add_service_name,
                    COALESCE(a.add_service_price, 0) as add_service_price
                FROM event_package_additional_services epas
                LEFT JOIN additional_services a ON epas.add_service_id = a.add_service_id
                WHERE epas.package_id = %s
            """, (row[0],))
            
            service_rows = cursor.fetchall()
            for service_row in service_rows:
                try:
                    if service_row[0] is not None:  # Only add if service_id is not NULL
                        package['additional_services'].append({
                            'service_id': service_row[0],
                            'name': service_row[1],
                            'price': float(service_row[2]) if service_row[2] else 0
                        })
                except Exception as e:
                    print(f"Error processing service row: {e}")
                    continue
            
            packages.append(package)
        
        return packages
    except Exception as e:
        print(f"Error fetching packages: {e}")
        raise e
    finally:
        cursor.close()
        conn.close()



def get_package_details_by_id(package_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT ep.package_id, ep.package_name, et.event_type_name, ep.capacity, ep.description, ep.total_price,
                   ep.additional_capacity_charges, ep.charge_unit,
                   v.venue_id, v.venue_name, v.location, v.venue_price,
                   gp.gown_package_name, gp.gown_package_price,
                   array_agg(ps.package_service_id) AS package_service_ids,
                   array_agg(ps.supplier_id) AS supplier_ids,
                   array_agg(s.service) AS services,
                   array_agg(s.price) AS service_prices,
                   array_agg(u.firstname) AS supplier_firstnames,
                   array_agg(u.lastname) AS supplier_lastnames,
                   array_agg(u.email) AS supplier_emails,
                   array_agg(ps.external_supplier_name) AS external_supplier_names,
                   array_agg(ps.external_supplier_contact) AS external_supplier_contacts,
                   array_agg(ps.external_supplier_price) AS external_supplier_prices,
                   array_agg(ps.remarks) AS remarks
            FROM event_packages ep
            LEFT JOIN event_type et ON ep.event_type_id = et.event_type_id
            LEFT JOIN venues v ON ep.venue_id = v.venue_id
            LEFT JOIN gown_package gp ON ep.gown_package_id = gp.gown_package_id
            LEFT JOIN event_package_services eps ON ep.package_id = eps.package_id
            LEFT JOIN package_service ps ON eps.package_service_id = ps.package_service_id
            LEFT JOIN suppliers s ON ps.supplier_id = s.supplier_id
            LEFT JOIN users u ON s.userid = u.userid
            WHERE ep.package_id = %s
            GROUP BY ep.package_id, et.event_type_name, v.venue_id, v.venue_name, v.location, v.venue_price, 
                     gp.gown_package_name, gp.gown_package_price
        """, (package_id,))
        
        row = cursor.fetchone()
        if row:
            return {
                'package_id': row[0],
                'package_name': row[1],
                'event_type_name': row[2],
                'capacity': row[3],
                'description': row[4],
                'total_price': float(row[5]) if row[5] else 0,
                'additional_capacity_charges': float(row[6]) if row[6] else 0,
                'charge_unit': row[7],
                'venue_id': row[8],
                'venue_name': row[9],
                'venue_location': row[10],
                'venue_price': float(row[11]) if row[11] else 0,
                'gown_package_name': row[12],
                'gown_package_price': float(row[13]) if row[13] else 0,
                'package_service_ids': row[14] if row[14] and row[14][0] is not None else [],
                'supplier_ids': row[15] if row[15] and row[15][0] is not None else [],
                'services': row[16] if row[16] and row[16][0] is not None else [],
                'service_prices': [float(p) if p else 0 for p in row[17]] if row[17] and row[17][0] is not None else [],
                'supplier_firstnames': row[18] if row[18] and row[18][0] is not None else [],
                'supplier_lastnames': row[19] if row[19] and row[19][0] is not None else [],
                'supplier_emails': row[20] if row[20] and row[20][0] is not None else [],
                'external_supplier_names': row[21] if row[21] and row[21][0] is not None else [],
                'external_supplier_contacts': row[22] if row[22] and row[22][0] is not None else [],
                'external_supplier_prices': [float(p) if p else 0 for p in row[23]] if row[23] and row[23][0] is not None else [],
                'remarks': row[24] if row[24] and row[24][0] is not None else []
            }
        return None
    finally:
        cursor.close()
        conn.close()



def add_event_item(userid, event_name, event_type, event_theme, event_color, 
                  package_id, suppliers, schedule=None, start_time=None, 
                  end_time=None, status='Wishlist', total_price=0, outfits=None, 
                  services=None, additional_items=None, booking_type='Online'):
    """Add a new event with its package configuration"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("BEGIN")

        # Ensure numeric values are properly formatted
        total_price = float(total_price) if total_price is not None else 0

        # Insert into events table
        cursor.execute("""
            INSERT INTO events (
                userid, event_name, event_type, event_theme, event_color, 
                package_id, schedule, start_time, end_time, status,
                total_price, booking_type
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) 
            RETURNING events_id
        """, (
            userid, event_name, event_type, event_theme, event_color, 
            package_id, schedule, start_time, end_time, status,
            total_price, booking_type
        ))
        events_id = cursor.fetchone()[0]

        # Create package configuration if package_id is provided
        if package_id:
            cursor.execute("""
                INSERT INTO event_package_configurations (events_id, package_id)
                VALUES (%s, %s)
                RETURNING config_id
            """, (events_id, package_id))
            config_id = cursor.fetchone()[0]

            # Store package suppliers
            if suppliers:
                for supplier in suppliers:
                    if not supplier:  # Skip if supplier is None
                        continue
                    cursor.execute("""
                        INSERT INTO event_package_suppliers (
                            config_id, supplier_id, original_price, modified_price,
                            is_modified, is_removed, remarks
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (
                        config_id,
                        supplier.get('supplier_id'),
                        float(supplier.get('original_price', 0) or 0),
                        float(supplier.get('modified_price', 0) or 0),
                        supplier.get('is_modified', False),
                        supplier.get('is_removed', False),
                        supplier.get('remarks', '')
                    ))

            # Store package outfits
            if outfits:
                for outfit in outfits:
                    if not outfit:  # Skip if outfit is None
                        continue
                    cursor.execute("""
                        INSERT INTO event_package_outfits (
                            config_id, outfit_id, gown_package_id,
                            original_price, modified_price,
                            is_modified, is_removed, remarks
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        config_id,
                        outfit.get('outfit_id'),
                        outfit.get('gown_package_id'),
                        float(outfit.get('original_price', 0) or 0),
                        float(outfit.get('modified_price', 0) or 0),
                        outfit.get('is_modified', False),
                        outfit.get('is_removed', False),
                        outfit.get('remarks', '')
                    ))

            # Store package services
            if services:
                for service in services:
                    if not service:  # Skip if service is None
                        continue
                    if 'package_service_id' in service:
                        cursor.execute("""
                            INSERT INTO event_package_services (package_id, package_service_id)
                            VALUES (%s, %s)
                        """, (
                            package_id,
                            service.get('package_service_id')
                        ))
                    else:
                        cursor.execute("""
                            INSERT INTO package_service (supplier_id, remarks)
                            VALUES (%s, %s)
                            RETURNING package_service_id
                        """, (
                            service.get('supplier_id'),
                            service.get('remarks', '')
                        ))
                        package_service_id = cursor.fetchone()[0]
                        cursor.execute("""
                            INSERT INTO event_package_services (package_id, package_service_id)
                            VALUES (%s, %s)
                        """, (
                            package_id,
                            package_service_id
                        ))

        # Store additional (non-package) items
        if additional_items:
            for item in additional_items:
                if not item:  # Skip if item is None
                    continue
                cursor.execute("""
                    INSERT INTO event_additional_items (
                        events_id, item_type, item_id, price, remarks
                    )
                    VALUES (%s, %s, %s, %s, %s)
                """, (
                    events_id,
                    item.get('item_type'),
                    item.get('item_id'),
                    float(item.get('price', 0) or 0),
                    item.get('remarks', '')
                ))

        cursor.execute("COMMIT")
        return events_id

    except Exception as e:
        cursor.execute("ROLLBACK")
        print(f"Error in add_event_item: {str(e)}")  # Add debug print
        raise e
    finally:
        cursor.close()
        conn.close()

def get_user_id_by_email(email):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT userid FROM users WHERE email = %s", (email,))
        result = cursor.fetchone()
        return result[0] if result else None
    finally:
        cursor.close()
        conn.close()

def get_available_suppliers():
    """Get a list of all available suppliers"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT s.supplier_id, u.firstname, u.lastname, s.service, s.price, 
                   u.email, u.contactnumber, u.address, u.user_img
            FROM suppliers s
            JOIN users u ON s.userid = u.userid
            WHERE s.status = 'Active'
            ORDER BY s.service, u.lastname
        """)
        suppliers = cursor.fetchall()
        
        suppliers_list = []
        for supplier in suppliers:
            supplier_data = {
                'supplier_id': supplier[0],
                'firstname': supplier[1],
                'lastname': supplier[2],
                'service': supplier[3],
                'price': float(supplier[4]) if supplier[4] else 0,
                'email': supplier[5],
                'contactnumber': supplier[6],
                'address': supplier[7],
                'user_img': supplier[8] if supplier[8] else None,
                'name': f"{supplier[1]} {supplier[2]}"
            }
            
            # Get social media for this supplier
            try:
                cursor.execute("""
                    SELECT platform, handle, url 
                    FROM supplier_social_media 
                    WHERE supplier_id = %s
                """, (supplier[0],))
                social_media = cursor.fetchall()
                
                supplier_data['social_media'] = [
                    {
                        'platform': sm[0],
                        'handle': sm[1],
                        'url': sm[2]
                    } for sm in social_media
                ]
            except Exception as e:
                print(f"Error fetching social media for supplier {supplier[0]}: {str(e)}")
                supplier_data['social_media'] = []
                
            suppliers_list.append(supplier_data)
            
        return suppliers_list
    finally:
        cursor.close()
        conn.close()

def get_available_venues():
    """Get a list of all available venues"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT venue_id, venue_name, location, venue_price, description, venue_capacity 
            FROM venues 
            WHERE status = 'Active' 
            ORDER BY venue_name
        """)
        venues = cursor.fetchall()
        
        return [
            {
                'venue_id': venue[0],
                'venue_name': venue[1],
                'location': venue[2],
                'venue_price': float(venue[3]) if venue[3] else 0,
                'description': venue[4],
                'venue_capacity': venue[5] if venue[5] else 0
            }
            for venue in venues
        ]
    finally:
        cursor.close()
        conn.close()

def get_available_gown_packages():
    """Get a list of all available gown packages"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT gown_package_id, gown_package_name, gown_package_price, description 
            FROM gown_package 
            WHERE status = 'Active' 
            ORDER BY gown_package_name
        """)
        gown_packages = cursor.fetchall()
        
        return [
            {
                'gown_package_id': package[0],
                'gown_package_name': package[1],
                'gown_package_price': float(package[2]) if package[2] else 0,
                'description': package[3]
            }
            for package in gown_packages
        ]
    finally:
        cursor.close()
        conn.close()


# Function to fetch all additional services from the additional_services table
def get_all_additional_services():
    """Get all additional services that are active"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT add_service_id, add_service_name, add_service_description, add_service_price 
            FROM additional_services 
            WHERE status = 'Active'
            ORDER BY add_service_name
        """)
        services = cursor.fetchall()
        
        return [
            {
                'add_service_id': service[0],
                'add_service_name': service[1],
                'add_service_description': service[2],
                'add_service_price': float(service[3]) if service[3] else 0
            }
            for service in services
        ]
    finally:
        cursor.close()
        conn.close()




def get_event_types():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT event_type_id, event_type_name 
            FROM event_type 
            ORDER BY event_type_name
        """)
        rows = cursor.fetchall()
        event_types = [
            {
                'event_type_id': row[0],
                'event_type_name': row[1]
            }
            for row in rows
        ]
        return event_types
    except Exception as e:
        print(f"Error fetching event types: {e}")
        raise e
    finally:
        cursor.close()
        conn.close()

def initialize_event_types():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # First check if we already have event types
        cursor.execute("SELECT COUNT(*) FROM event_type")
        count = cursor.fetchone()[0]
        logging.info(f"Current event type count: {count}")
        
        if count == 0:
            # Insert default event types
            event_types = [
                'Wedding',
                'Birthday',
                'Corporate Event',
                'Anniversary',
                'Graduation',
                'Family Gathering',
                'Reunion',
                'Conference',
                'Seminar',
                'Other'
            ]
            
            for event_type in event_types:
                logging.info(f"Inserting event type: {event_type}")
                cursor.execute(
                    "INSERT INTO event_type (event_type_name) VALUES (%s)",
                    (event_type,)
                )
            
            conn.commit()
            logging.info("Default event types initialized successfully")
        else:
            logging.info("Event types already exist, skipping initialization")
        
    except Exception as e:
        conn.rollback()
        logging.error(f"Error initializing event types: {e}")
        raise e
    finally:
        cursor.close()
        conn.close()

def get_booked_schedules():
    """
    Get all booked event schedules that are not cancelled
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        query = """
            SELECT schedule, start_time, end_time 
            FROM events 
            WHERE schedule IS NOT NULL 
            AND start_time IS NOT NULL 
            AND end_time IS NOT NULL 
            AND schedule >= CURRENT_DATE 
            AND (status = 'Wishlist' OR status IS NULL)
            ORDER BY schedule, start_time
        """
        
        cursor.execute(query)
        schedules = cursor.fetchall()
        
        if schedules:
            return [
                {
                    'schedule': schedule.strftime('%Y-%m-%d') if schedule else None,
                    'start_time': start_time.strftime('%H:%M') if start_time else None,
                    'end_time': end_time.strftime('%H:%M') if end_time else None
                }
                for schedule, start_time, end_time in schedules
            ]
        return []
        
    except Exception as e:
        logger.error(f"Error fetching booked schedules: {e}")
        return []
    finally:
        cursor.close()
        conn.close()


def track_service_modification(events_id, package_service_id, modification_type, original_price=None, modified_price=None, remarks=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO modified_event_services 
            (event_id, package_service_id, modification_type, original_price, modified_price, remarks)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING modification_id
        """, (events_id, package_service_id, modification_type, original_price, modified_price, remarks))
        
        modification_id = cursor.fetchone()[0]
        conn.commit()
        return modification_id
    except Exception as e:
        conn.rollback()
        logger.error(f"Error tracking service modification: {str(e)}")
        raise
    finally:
        cursor.close()
        conn.close()

def add_service_customization(events_id, package_service_id, custom_price=None, custom_details=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO event_service_customizations 
            (event_id, package_service_id, custom_price, custom_details)
            VALUES (%s, %s, %s, %s)
            RETURNING customization_id
        """, (events_id, package_service_id, custom_price, custom_details))
        
        customization_id = cursor.fetchone()[0]
        conn.commit()
        return customization_id
    except Exception as e:
        conn.rollback()
        logger.error(f"Error adding service customization: {str(e)}")
        raise
    finally:
        cursor.close()
        conn.close()

def get_event_modifications(events_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get all modifications for the event
        cursor.execute("""
            SELECT m.modification_id, m.package_service_id, m.modification_type,
                   m.original_price, m.modified_price, m.remarks,
                   COALESCE(ps.supplier_id::text, ps.external_supplier_name) as supplier_identifier,
                   ps.external_supplier_contact, ps.external_supplier_price
            FROM modified_event_services m
            JOIN package_service ps ON m.package_service_id = ps.package_service_id
            WHERE m.event_id = %s
            ORDER BY m.created_at
        """, (events_id,))
        
        modifications = cursor.fetchall()
        
        # Get all customizations for the event
        cursor.execute("""
            SELECT c.customization_id, c.package_service_id, c.custom_price,
                   c.custom_details,
                   COALESCE(ps.supplier_id::text, ps.external_supplier_name) as supplier_identifier
            FROM event_service_customizations c
            JOIN package_service ps ON c.package_service_id = ps.package_service_id
            WHERE c.event_id = %s
            ORDER BY c.created_at
        """, (events_id,))
        
        customizations = cursor.fetchall()
        
        return {
            'modifications': [{
                'modification_id': m[0],
                'package_service_id': m[1],
                'modification_type': m[2],
                'original_price': float(m[3]) if m[3] else None,
                'modified_price': float(m[4]) if m[4] else None,
                'remarks': m[5],
                'supplier_identifier': m[6],
                'external_supplier_contact': m[7],
                'external_supplier_price': float(m[8]) if m[8] else None
            } for m in modifications],
            'customizations': [{
                'customization_id': c[0],
                'package_service_id': c[1],
                'custom_price': float(c[2]) if c[2] else None,
                'custom_details': c[3],
                'supplier_identifier': c[4]
            } for c in customizations]
        }
    finally:
        cursor.close()
        conn.close()

def create_wishlist_package(events_id, package_data):
    """Create a new wishlist package for an event"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Extract gown_package_id from inclusions
        gown_package_id = None
        if 'inclusions' in package_data:
            outfit_inclusion = next((item for item in package_data['inclusions'] if item['type'] == 'outfit'), None)
            if outfit_inclusion and 'data' in outfit_inclusion:
                outfit_data = outfit_inclusion['data']
                gown_package_id = outfit_data.get('gown_package_id')  # Get gown_package_id directly

        # Get venue_id from inclusions if available
        venue_id = None
        venue_data = None
        logger.info(f"Processing package data: {package_data}")
        if 'inclusions' in package_data:
            logger.info(f"Found inclusions in package data: {package_data['inclusions']}")
            venue_inclusion = next((item for item in package_data['inclusions'] if item['type'] == 'venue'), None)
            logger.info(f"Venue inclusion found: {venue_inclusion}")
            if venue_inclusion and 'data' in venue_inclusion:
                venue_data = venue_inclusion['data']
                venue_id = venue_data.get('venue_id')
                logger.info(f"Extracted venue data: {venue_data}")
                logger.info(f"Extracted venue_id: {venue_id}")
        elif package_data.get('venue'):
            venue_data = package_data['venue']
            venue_id = venue_data.get('venue_id')
            logger.info(f"Using venue data from package: {venue_data}")
        
        # Insert the main wishlist package
        cursor.execute("""
            INSERT INTO wishlist_packages (
                events_id, package_name, capacity, description, venue_id,
                gown_package_id, additional_capacity_charges, charge_unit,
                total_price, event_type_id, status, venue_status
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            ) RETURNING wishlist_id
        """, (
            events_id,
            package_data.get('package_name'),
            package_data.get('capacity'),
            package_data.get('description'),
            venue_id,
            gown_package_id,
            package_data.get('additional_capacity_charges', 0),
            package_data.get('charge_unit', 1),
            package_data.get('total_price', 0),
            package_data.get('event_type_id'),
            package_data.get('status', 'Active'),
            'Pending'  # Default venue_status
        ))
        
        wishlist_id = cursor.fetchone()[0]
        logger.info(f"Created wishlist package with ID: {wishlist_id}")
        
        # Add venue to wishlist_venues table if venue data is available
        if venue_data:
            # Try to get the price from various possible fields
            venue_price = float(
                venue_data.get('venue_price') or  # Try venue_price first
                venue_data.get('price') or        # Then try price
                0                                 # Default to 0 if neither exists
            )
            venue_remarks = venue_data.get('remarks', '')
            
            logger.info(f"Inserting venue data: id={venue_id}, price={venue_price}, remarks={venue_remarks}")
            cursor.execute("""
                INSERT INTO wishlist_venues (
                    wishlist_id, venue_id, price, remarks, status, has_been_updated
                ) VALUES (
                    %s, %s, %s, %s, %s, %s
                )
            """, (
                wishlist_id,
                venue_id,
                venue_price,
                venue_remarks,
                'Pending',  # Default status
                False  # Default has_been_updated
            ))
            
            logger.info(f"Inserted venue {venue_id} with price {venue_price} into wishlist_venues")

        # Add gown package to wishlist_outfits if available
        if gown_package_id:
            outfit_data = next((item['data'] for item in package_data.get('inclusions', []) 
                              if item['type'] == 'outfit' and 'data' in item), None)
            if outfit_data:
                cursor.execute("""
                    INSERT INTO wishlist_outfits (
                        wishlist_id, gown_package_id, price, remarks, status, has_been_updated
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s
                    )
                """, (
                    wishlist_id,
                    gown_package_id,
                    float(outfit_data.get('price', 0)),
                    outfit_data.get('remarks', ''),
                    outfit_data.get('status', 'Pending'),
                    outfit_data.get('has_been_updated', False)
                ))
                logger.info(f"Inserted gown package {gown_package_id} into wishlist_outfits")

        # Add services from inclusions first (preferred method)
        if 'inclusions' in package_data:
            for inclusion in package_data['inclusions']:
                if inclusion['type'] == 'service' and 'data' in inclusion:
                    service_data = inclusion['data']
                    service_id = service_data.get('service_id') or service_data.get('add_service_id')
                    
                    if service_id:
                        price = service_data.get('price', 0)
                        remarks = service_data.get('remarks', '')
                        
                        cursor.execute("""
                            INSERT INTO wishlist_additional_services (wishlist_id, add_service_id, price, remarks)
                            VALUES (%s, %s, %s, %s)
                        """, (
                            wishlist_id,
                            service_id,
                            price,
                            remarks
                        ))
                        logger.info(f"Added service {service_id} with price {price} from inclusions")
        
        # Fall back to services array if inclusions didn't contain services
        elif package_data.get('services'):
            for service in package_data['services']:
                # Check if service has required fields
                service_id = service.get('service_id') or service.get('add_service_id')
                if service and service_id:
                    cursor.execute("""
                        INSERT INTO wishlist_additional_services (wishlist_id, add_service_id, price, remarks)
                        VALUES (%s, %s, %s, %s)
                    """, (
                        wishlist_id, 
                        service_id,
                        service.get('price', 0),
                        service.get('remarks', '')
                    ))
                    logger.info(f"Added service {service_id} with price {service.get('price', 0)} from services array")
        
        # Add suppliers if provided
        if package_data.get('suppliers'):
            for supplier in package_data['suppliers']:
                # Check if supplier has required fields
                if supplier and 'supplier_id' in supplier:
                    cursor.execute("""
                        INSERT INTO wishlist_suppliers (wishlist_id, supplier_id, price, remarks)
                        VALUES (%s, %s, %s, %s)
                    """, (
                        wishlist_id,
                        supplier['supplier_id'],
                        supplier.get('price', 0),
                        supplier.get('remarks', '')
                    ))
        
        conn.commit()
        return wishlist_id
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Error creating wishlist package: {str(e)}")
        raise e
    finally:
        cursor.close()
        conn.close()

def initialize_test_suppliers():
    """Initialize test suppliers for development purposes"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # First, create test users
        test_users = [
            ('John', 'Doe', 'john.doe@test.com', '+1234567890', 'password123', 'Supplier', None, '123 Main St', 'johndoe'),
            ('Jane', 'Smith', 'jane.smith@test.com', '+1234567891', 'password123', 'Supplier', None, '456 Oak St', 'janesmith'),
            ('Mike', 'Johnson', 'mike.j@test.com', '+1234567892', 'password123', 'Supplier', None, '789 Pine St', 'mikej')
        ]

        for user in test_users:
            cursor.execute("""
                INSERT INTO users (firstname, lastname, email, contactnumber, password, user_type, user_img, address, username)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (email) DO NOTHING
                RETURNING userid
            """, user)
            
            userid = cursor.fetchone()
            if userid:
                # Add supplier entry
                cursor.execute("""
                    INSERT INTO suppliers (userid, service, price, status)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                    RETURNING supplier_id
                """, (userid[0], f"Event Service by {user[0]}", 5000.00, 'active'))
                
                supplier_id = cursor.fetchone()
                if supplier_id:
                    # Add social media for the supplier
                    social_media = [
                        ('facebook', f'{user[8]}', f'https://facebook.com/{user[8]}'),
                        ('instagram', f'{user[8]}_events', f'https://instagram.com/{user[8]}_events'),
                    ]
                    
                    for platform, handle, url in social_media:
                        cursor.execute("""
                            INSERT INTO supplier_social_media (supplier_id, platform, handle, url)
                            VALUES (%s, %s, %s, %s)
                            ON CONFLICT DO NOTHING
                        """, (supplier_id[0], platform, handle, url))

        conn.commit()
        logging.info("Test suppliers initialized successfully")
        return True
    except Exception as e:
        conn.rollback()
        logging.error(f"Error initializing test suppliers: {e}")
        return False
    finally:
        cursor.close()
        conn.close()

def get_user_by_email(email):
    """
    Get user details by email.
    :param email: User's email address
    :return: User details as dictionary or None if not found
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            """SELECT userid, firstname, lastname, email, contactnumber, address, 
                     user_type, user_img, username
               FROM users 
               WHERE email = %s""", 
            (email,)
        )
        user = cursor.fetchone()
        
        if user:
            return {
                'userid': user[0],
                'firstname': user[1],
                'lastname': user[2],
                'email': user[3],
                'contactnumber': user[4],
                'address': user[5],
                'user_type': user[6],
                'user_img': user[7],
                'username': user[8]
            }
        return None
    except Exception as e:
        logger.error(f"Error getting user by email: {e}")
        return None
    finally:
        cursor.close()
        conn.close()

def update_user_profile(userid, firstname, lastname, username, contactnumber, address):
    """
    Update user profile information.
    :param userid: User ID
    :param firstname: First name
    :param lastname: Last name
    :param username: Username
    :param contactnumber: Contact number
    :param address: Address
    :return: True if successful, False otherwise
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            """UPDATE users 
               SET firstname = %s, lastname = %s, username = %s, contactnumber = %s, address = %s
               WHERE userid = %s""",
            (firstname, lastname, username, contactnumber, address, userid)
        )
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"Error updating user profile: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()

def update_user_profile_picture(userid, image_path):
    """
    Update user profile picture.
    :param userid: User ID
    :param image_path: Path to the uploaded image
    :return: True if successful, False otherwise
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Log the update attempt
        logger.info(f"Updating profile picture for user {userid} with path {image_path}")
        
        cursor.execute(
            """UPDATE users 
               SET user_img = %s
               WHERE userid = %s
               RETURNING user_img""",
            (image_path, userid)
        )
        
        # Get the updated value to confirm it worked
        updated_path = cursor.fetchone()
        
        conn.commit()
        
        if updated_path:
            logger.info(f"Successfully updated profile picture for user {userid}")
            return True
        
        logger.warning(f"Failed to update profile picture: no rows updated for user {userid}")
        return False
        
    except Exception as e:
        logger.error(f"Error updating user profile picture: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()

def get_user_profile_by_id(userid):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT 
                userid,
                firstname,
                lastname,
                username,
                email,
                contactnumber,
                address,
                user_type,
                user_img
            FROM users 
            WHERE userid = %s
        """, (userid,))
        
        row = cursor.fetchone()
        
        if row:
            user_data = {
                'userid': row[0],
                'firstname': row[1],
                'lastname': row[2],
                'username': row[3],
                'email': row[4],
                'contactnumber': row[5],
                'address': row[6],
                'user_type': row[7].lower() if row[7] else None,
                'user_img': row[8]
            }
            
            logger.info(f"Raw user data from database: {user_data}")
            
            # If there's no profile picture, use the default
            if not user_data['user_img']:
                user_data['user_img'] = "/static/uploads/profile_pics/default-profile.jpg"
                logger.info("Using default profile picture")
            
            logger.info(f"Final user data: {user_data}")
            return user_data
            
        logger.warning(f"No user found with ID: {userid}")
        return None

    except Exception as e:
        logger.error(f"Error in get_user_profile_by_id: {e}")
        return None
    finally:
        cursor.close()
        conn.close()

def change_password(user_id, current_password, new_password):
    """
    Changes the user's password after verifying the current password.
    :param user_id: ID of the user
    :param current_password: Current password to verify
    :param new_password: New password to set
    :return: Tuple (success, message)
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    current_password_hash = hash_password(current_password)
    new_password_hash = hash_password(new_password)

    try:
        # First verify the current password
        cursor.execute(
            "SELECT password FROM users WHERE userid = %s",
            (user_id,)
        )
        user = cursor.fetchone()
        
        if not user:
            return False, "User not found"
            
        if user[0] != current_password_hash:
            return False, "Current password is incorrect"
            
        # Update the password
        cursor.execute(
            "UPDATE users SET password = %s WHERE userid = %s",
            (new_password_hash, user_id)
        )
        conn.commit()
        return True, "Password changed successfully"
        
    except Exception as e:
        print(f"Error in change_password: {str(e)}")
        return False, "An error occurred while changing password"
    finally:
        cursor.close()
        conn.close()

def get_supplier_booked_events(user_email):
    try:
        print(f"DEBUG: Getting events for supplier email: {user_email}")
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # First check if the user exists and is a supplier
        cursor.execute("""
            SELECT u.userid, u.email, s.supplier_id, s.service 
            FROM users u
            JOIN suppliers s ON u.userid = s.userid
            WHERE u.email = %s
        """, (user_email,))
        supplier_info = cursor.fetchone()
        print(f"DEBUG: Supplier info: {supplier_info}")
        
        if not supplier_info:
            print(f"DEBUG: No supplier found for email {user_email}")
            return []
            
        # Query to get events where the supplier is booked
        query = """
            WITH outfit_info AS (
                SELECT 
                    wo.wishlist_id,
                    array_agg(
                        json_build_object(
                            'wishlist_outfit_id', wo.wishlist_outfit_id,
                            'outfit_id', o.outfit_id,
                            'outfit_name', o.outfit_name,
                            'outfit_type', o.outfit_type,
                            'outfit_color', o.outfit_color,
                            'outfit_desc', o.outfit_desc,
                            'outfit_img', o.outfit_img,
                            'gown_package_id', wo.gown_package_id,
                            'gown_package_name', gp.gown_package_name,
                            'gown_package_price', gp.gown_package_price,
                            'price', wo.price,
                            'status', wo.status,
                            'remarks', wo.remarks,
                            'created_at', wo.created_at,
                            'has_been_updated', wo.has_been_updated
                        )
                    ) as outfit_details
                FROM wishlist_outfits wo
                LEFT JOIN outfits o ON wo.outfit_id = o.outfit_id
                LEFT JOIN gown_package gp ON wo.gown_package_id = gp.gown_package_id
                GROUP BY wo.wishlist_id
            )
            SELECT 
                e.events_id,
                e.event_name,
                e.event_type,
                e.event_theme,
                e.event_color,
                e.schedule,
                e.start_time,
                e.end_time,
                e.status as event_status,
                e.total_price as event_total_price,
                e.booking_type,
                client.firstname as client_firstname,
                client.lastname as client_lastname,
                client.contactnumber as client_contact,
                client.address as client_address,
                ws.status as booking_status,
                ws.price as supplier_price,
                ws.remarks as booking_remarks,
                supp.service as supplier_service,
                u.username as supplier_username,
                wp.package_name,
                wp.venue_status,
                v.venue_id,
                v.venue_name,
                v.location as venue_location,
                v.venue_price,
                v.description as venue_description,
                v.venue_capacity,
                v.image as venue_image,
                wv.price as booked_venue_price,
                oi.outfit_details
            FROM events e
            JOIN users client ON e.userid = client.userid
            JOIN wishlist_packages wp ON e.events_id = wp.events_id
            JOIN wishlist_suppliers ws ON wp.wishlist_id = ws.wishlist_id
            JOIN suppliers supp ON ws.supplier_id = supp.supplier_id
            JOIN users u ON supp.userid = u.userid
            LEFT JOIN wishlist_venues wv ON wp.wishlist_id = wv.wishlist_id
            LEFT JOIN venues v ON wp.venue_id = v.venue_id OR wv.venue_id = v.venue_id
            LEFT JOIN outfit_info oi ON wp.wishlist_id = oi.wishlist_id
            WHERE supp.supplier_id = %s
            AND UPPER(ws.status) = 'APPROVED'
            ORDER BY 
                CASE 
                    WHEN e.schedule > CURRENT_DATE THEN 1
                    WHEN e.schedule = CURRENT_DATE THEN 2
                    ELSE 3
                END,
                e.schedule ASC,
                e.start_time ASC
        """
        print(f"DEBUG: Executing query with supplier_id: {supplier_info['supplier_id']}")
        cursor.execute(query, (supplier_info['supplier_id'],))
        
        events = cursor.fetchall()
        print(f"DEBUG: Raw events count: {len(events)}")
        
        # Convert the results to a list of dictionaries
        formatted_events = []
        for event in events:
            formatted_event = dict(event)
            
            # Convert time objects to string format
            if formatted_event['start_time']:
                formatted_event['start_time'] = formatted_event['start_time'].strftime('%H:%M:%S')
            if formatted_event['end_time']:
                formatted_event['end_time'] = formatted_event['end_time'].strftime('%H:%M:%S')
            
            # Convert date object to string format
            if formatted_event.get('schedule'):
                formatted_event['schedule'] = formatted_event['schedule'].strftime('%Y-%m-%d')
            
            # Format created_at timestamp in outfit details if it exists
            if formatted_event.get('outfit_details'):
                for outfit in formatted_event['outfit_details']:
                    if outfit.get('created_at'):
                        # Check if created_at is already a string
                        if not isinstance(outfit['created_at'], str):
                            outfit['created_at'] = outfit['created_at'].strftime('%Y-%m-%d %H:%M:%S')
            
            # Add is_upcoming field by comparing with current date
            current_date = datetime.now().date()
            event_date = datetime.strptime(formatted_event['schedule'], '%Y-%m-%d').date() if formatted_event.get('schedule') else None
            formatted_event['is_upcoming'] = event_date >= current_date if event_date else False
            
            formatted_events.append(formatted_event)

        print(f"DEBUG: Returning {len(formatted_events)} formatted events")
        cursor.close()
        conn.close()
        
        return formatted_events
    except Exception as e:
        print(f"Error in get_supplier_booked_events: {e}")
        import traceback
        traceback.print_exc()
        return []

def get_gown_package_outfits(gown_package_id):
    """Get all outfits that belong to a specific gown package"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT o.outfit_id, o.outfit_name, o.outfit_type, o.outfit_color, 
                   o.outfit_desc, o.rent_price, o.status, o.outfit_img, o.size
            FROM gown_package_outfits gpo
            JOIN outfits o ON gpo.outfit_id = o.outfit_id
            WHERE gpo.gown_package_id = %s
            ORDER BY o.outfit_name
        """, (gown_package_id,))
        outfits = cursor.fetchall()
        
        return [
            {
                'outfit_id': outfit[0],
                'outfit_name': outfit[1],
                'outfit_type': outfit[2],
                'outfit_color': outfit[3],
                'outfit_desc': outfit[4],
                'rent_price': float(outfit[5]) if outfit[5] else 0,
                'status': outfit[6],
                'outfit_img': outfit[7],
                'size': outfit[8]
            }
            for outfit in outfits
        ]
    finally:
        cursor.close()
        conn.close()

def add_event_feedback(events_id, userid, rating, feedback_text=None):
    """Add a new feedback for an event"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Check if user has already submitted feedback for this event
        cursor.execute("""
            SELECT feedback_id FROM event_feedbacks 
            WHERE events_id = %s AND userid = %s
        """, (events_id, userid))
        
        if cursor.fetchone():
            return False, "You have already submitted feedback for this event"
            
        # Insert new feedback
        cursor.execute("""
            INSERT INTO event_feedbacks (events_id, userid, rating, feedback_text)
            VALUES (%s, %s, %s, %s)
            RETURNING feedback_id
        """, (events_id, userid, rating, feedback_text))
        
        feedback_id = cursor.fetchone()[0]
        conn.commit()
        return True, feedback_id
        
    except Exception as e:
        logger.error(f"Error adding event feedback: {e}")
        conn.rollback()
        return False, str(e)
    finally:
        cursor.close()
        conn.close()

def get_event_feedback(events_id):
    """Get all feedback for a specific event"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT f.feedback_id, f.userid, f.rating, f.feedback_text, 
                   f.created_at, u.firstname, u.lastname
            FROM event_feedbacks f
            JOIN users u ON f.userid = u.userid
            WHERE f.events_id = %s
            ORDER BY f.created_at DESC
        """, (events_id,))
        
        feedbacks = cursor.fetchall()
        return [{
            'feedback_id': f[0],
            'userid': f[1],
            'rating': f[2],
            'feedback_text': f[3],
            'created_at': f[4].strftime('%Y-%m-%d %H:%M:%S'),
            'user_firstname': f[5],
            'user_lastname': f[6]
        } for f in feedbacks]
        
    except Exception as e:
        logger.error(f"Error getting event feedback: {e}")
        return []
    finally:
        cursor.close()
        conn.close()

def get_supplier_availability(supplier_id, start_date=None, end_date=None):
    """
    Get supplier availability for a date range
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        query = """
            SELECT 
                availability_id,
                supplier_id,
                date,
                is_available,
                reason,
                created_at,
                updated_at
            FROM supplier_availability 
            WHERE supplier_id = %s
        """
        params = [supplier_id]
        
        if start_date and end_date:
            query += " AND date BETWEEN %s AND %s"
            params.extend([start_date, end_date])
        elif start_date:
            query += " AND date >= %s"
            params.append(start_date)
        elif end_date:
            query += " AND date <= %s"
            params.append(end_date)
            
        query += " ORDER BY date ASC"
        
        cursor.execute(query, params)
        availability = cursor.fetchall()
        
        return availability
    except Exception as e:
        logger.error(f"Error getting supplier availability: {e}")
        raise
    finally:
        cursor.close()
        conn.close()

def set_supplier_availability(supplier_id, date, is_available=True, reason=None):
    """
    Set supplier availability for a specific date
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Use UPSERT to handle both insert and update
        query = """
            INSERT INTO supplier_availability (supplier_id, date, is_available, reason)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (supplier_id, date) 
            DO UPDATE SET 
                is_available = EXCLUDED.is_available,
                reason = EXCLUDED.reason,
                updated_at = CURRENT_TIMESTAMP
        """
        
        cursor.execute(query, (supplier_id, date, is_available, reason))
        conn.commit()
        
        return True
    except Exception as e:
        logger.error(f"Error setting supplier availability: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

def delete_supplier_availability(supplier_id, date):
    """
    Delete supplier availability for a specific date
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = """
            DELETE FROM supplier_availability 
            WHERE supplier_id = %s AND date = %s
        """
        
        cursor.execute(query, (supplier_id, date))
        conn.commit()
        
        return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"Error deleting supplier availability: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

def get_supplier_id_by_email(email):
    """
    Get supplier ID by email
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = """
            SELECT s.supplier_id 
            FROM suppliers s
            JOIN users u ON s.userid = u.userid
            WHERE u.email = %s
        """
        
        cursor.execute(query, (email,))
        result = cursor.fetchone()
        
        return result[0] if result else None
    except Exception as e:
        logger.error(f"Error getting supplier ID by email: {e}")
        raise
    finally:
        cursor.close()
        conn.close()