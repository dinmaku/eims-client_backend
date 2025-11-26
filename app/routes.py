#routes.py
from flask import request, jsonify, send_from_directory
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from .models import (
    check_user, create_user, get_user_wishlist, 
    get_user_id_by_email, create_outfit, get_outfits, get_outfit_by_id, 
    book_outfit, get_booked_wishlist_by_user, delete_booked_wishlist, 
    get_package_details_by_id, get_booked_outfits_by_user,  
    get_available_suppliers, get_available_venues, get_available_gown_packages, 
    get_event_types, get_all_additional_services, get_booked_schedules, add_event_item,
    create_wishlist_package, initialize_test_suppliers, get_user_profile_by_id,
    change_password, get_db_connection, update_user_profile_picture, get_client_packages,
    get_supplier_booked_events, get_gown_package_outfits, add_event_feedback, get_event_feedback,
    update_user_profile, get_supplier_availability, set_supplier_availability, 
    delete_supplier_availability, get_supplier_id_by_email
)
import logging
import jwt
from functools import wraps
import os
from datetime import datetime, date, time
from werkzeug.utils import secure_filename
import uuid

logging.basicConfig(level=logging.DEBUG)

def init_routes(app):

    @app.route('/login', methods=['POST'])
    def login():
        try:
            # Get the login data
            data = request.json
            identifier = data.get('identifier')  # Can be email or username
            password = data.get('password')

            # Check if identifier and password are provided
            if not identifier or not password:
                return jsonify({'message': 'Username/Email and password are required!'}), 400

            # Check the user credentials
            is_valid, user_type = check_user(identifier, password)
            if is_valid:
                # Generate JWT token with additional claims
                access_token = create_access_token(identity=identifier, additional_claims={"user_type": user_type})

                return jsonify({
                    'message': 'Login successful!',
                    'access_token': access_token,
                    'user_type': user_type
                }), 200
            else:
                return jsonify({'message': 'Invalid username/email or password.'}), 401

        except Exception as e:
            print(f"Error during login: {e}")
            return jsonify({'message': 'An error occurred during login.'}), 500

    @app.route('/register', methods=['POST'])
    def register():
        data = request.json
        print(data)  # Log the incoming data for debugging
        first_name = data.get('firstName')
        last_name = data.get('lastName')
        username = data.get('username')
        email = data.get('email')
        contact_number = data.get('contactNumber')
        password = data.get('password')
        address = data.get('address', '') 
        user_type = data.get('user_type', 'Client')  # Get user_type from request, default to 'Client' if not provided

        # Validate required fields
        if not all([first_name, last_name, username, email, contact_number, password]):
            return jsonify({'message': 'All fields are required!'}), 400

        # Attempt to create the user
        if create_user(first_name, last_name, username, email, contact_number, password, user_type, address):
            return jsonify({'message': 'Registration successful!'}), 201
        else:
            return jsonify({'message': 'Email already exists!'}), 409

    @app.route('/available-suppliers', methods=['GET'])
    @jwt_required()
    def get_available_suppliers_route():
        try:
            suppliers = get_available_suppliers()
            return jsonify(suppliers), 200
        except Exception as e:
            app.logger.error(f"Error fetching available suppliers: {e}")
            return jsonify({'message': 'An error occurred while fetching available suppliers'}), 500

    @app.route('/available-venues', methods=['GET'])
    @jwt_required()
    def get_available_venues_route():
        try:
            venues = get_available_venues()
            return jsonify(venues), 200
        except Exception as e:
            app.logger.error(f"Error fetching available venues: {e}")
            return jsonify({'message': 'An error occurred while fetching available venues'}), 500

    @app.route('/available-gown-packages', methods=['GET'])
    def get_available_gown_packages_route():
        try:
            gown_packages = get_available_gown_packages()
            return jsonify(gown_packages), 200
        except Exception as e:
            app.logger.error(f"Error fetching available gown packages: {e}")
            return jsonify({'message': 'An error occurred while fetching available gown packages'}), 500

    @app.route('/packages/<int:package_id>', methods=['GET'])
    @jwt_required()
    def get_package_details(package_id):
        try:
            package = get_package_details_by_id(package_id)  # Implement this function to fetch package details
            if not package:
                return jsonify({'message': 'Package not found'}), 404
            return jsonify(package), 200
        except Exception as e:
            app.logger.error(f"Error fetching package details: {e}")
            return jsonify({'message': 'An error occurred while fetching package details'}), 500

    @app.route('/wishlist', methods=['GET'])
    @jwt_required()
    def get_wishlist():
        email = get_jwt_identity()
        userid = get_user_id_by_email(email)
        print(f"User ID from email: {userid}")  # Debug statement
        wishlist = get_user_wishlist(userid)

        return jsonify(wishlist), 200

    SECRET_KEY = os.getenv('eims', 'fallback_jwt_secret')

# Decorator to protect routes and check token
    def token_required(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            token = request.headers.get('Authorization')
            if not token:
                return jsonify({'msg': 'Token is missing'}), 403

            try:
                # Remove 'Bearer ' from the token string
                token = token.split(" ")[1]
                # Decode the token using the secret key
                decoded_token = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            except jwt.ExpiredSignatureError:
                return jsonify({'msg': 'Token has expired'}), 401
            except jwt.InvalidTokenError:
                return jsonify({'msg': 'Invalid token'}), 401

            # Token is valid, pass control to the original route function
            return f(decoded_token, *args, **kwargs)

        return decorated_function
    
    @app.route('/check-auth', methods=['GET'])
    @jwt_required()
    def check_auth():
        try:
            # Access the identity from the decoded JWT token
            current_user = get_jwt_identity()  # This is the email (identity) you set in the JWT token
            return jsonify({"msg": f"Token is valid for user: {current_user}"}), 200
        except Exception as e:
            return jsonify({'msg': f'Error: {str(e)}'}), 422
        
    @app.route('/refresh', methods=['POST'])
    @jwt_required(refresh=True)
    def refresh():
        current_user = get_jwt_identity()
        new_access_token = create_access_token(identity=current_user)
        return jsonify(access_token=new_access_token)

    @app.route('/logout', methods=['POST'])
    def logout():
       
        return jsonify({'message': 'Logged out successfully'}), 200

    @app.route('/outfits', methods=['POST'])
    @jwt_required()
    def add_outfit():
        try:
            data = request.json
            outfit_name = data.get('outfit_name')
            outfit_type = data.get('outfit_type')
            outfit_color = data.get('outfit_color')
            outfit_desc = data.get('outfit_desc')
            rent_price = data.get('rent_price')
            status = data.get('status')
            outfit_img = data.get('outfit_img')

            # Validate required fields
            if not all([outfit_name, outfit_type, outfit_color, outfit_desc, rent_price, status, outfit_img]):
                return jsonify({'message': 'All fields are required!'}), 400

            # Create the new outfit
            if create_outfit(outfit_name, outfit_type, outfit_color, outfit_desc, rent_price, status, outfit_img):
                return jsonify({'message': 'Outfit added successfully!'}), 201
            else:
                return jsonify({'message': 'Error adding outfit'}), 500
        except Exception as e:
            return jsonify({'message': f'Error: {str(e)}'}), 500

    @app.route('/outfits', methods=['GET'])
    def get_all_outfits():
        try:
            outfits = get_outfits()
            return jsonify(outfits), 200
        except Exception as e:
            return jsonify({'message': f'Error fetching outfits: {str(e)}'}), 500

    @app.route('/outfits/<int:outfit_id>', methods=['GET'])
    @jwt_required()
    def get_outfit(outfit_id):
        try:
            outfit = get_outfit_by_id(outfit_id)
            if outfit:
                return jsonify(outfit), 200
            else:
                return jsonify({'message': 'Outfit not found'}), 404
        except Exception as e:
            return jsonify({'message': f'Error fetching outfit: {str(e)}'}), 500

    @app.route('/book-outfit', methods=['POST'])
    @jwt_required()
    def book_outfit_route():
        try:
            email = get_jwt_identity()
            userid = get_user_id_by_email(email)  # Assuming this function exists

            data = request.json
            outfit_id = data.get('outfit_id')
            pickup_date = data.get('pickup_date')
            return_date = data.get('return_date')
            status = data.get('status')
            additional_charges = data.get('additional_charges', 0)

            if book_outfit(userid, outfit_id, pickup_date, return_date, status, additional_charges):
                return jsonify({'message': 'Outfit booked successfully!'}), 201
            else:
                return jsonify({'message': 'Error booking outfit'}), 500
        except Exception as e:
            return jsonify({'message': f'Error booking outfit: {str(e)}'}), 500

    @app.route('/booked-wishlist', methods=['GET'])
    @jwt_required()
    def get_user_booked_wishlist():
        try:
            email = get_jwt_identity()
            userid = get_user_id_by_email(email)  # Assuming a function to get user ID by email exists

            # Fetch events for the user from the updated events table
            booked_wishlist = get_booked_wishlist_by_user(userid)
            return jsonify(booked_wishlist), 200
        except Exception as e:
            return jsonify({'message': f'Error fetching booked wishlist: {str(e)}'}), 500

    @app.route('/booked_wishlist/<int:events_id>', methods=['DELETE'])
    @jwt_required()  # Assuming you're using JWT for authorization
    def delete_wishlist_item(events_id):
        try:
            # Call the function to delete the event item by events_id
            if delete_booked_wishlist(events_id):
                return jsonify({"message": "Event item deleted successfully"}), 200
            else:
                return jsonify({"message": "Failed to delete event item"}), 500
        except Exception as e:
            return jsonify({"message": f"Error: {str(e)}"}), 500

    @app.route('/booked-outfits', methods=['GET'])
    @jwt_required()
    def get_user_booked_outfits():
        try:
            # Fetch the current user's email from the JWT token
            email = get_jwt_identity()
            
            # Here, you would fetch the user's ID based on their email (you can create a helper function for this)
            # Assuming you have a function to get the user ID from email
            userid = get_user_id_by_email(email)
            
            # Fetch the booked outfits for the user
            booked_outfits = get_booked_outfits_by_user(userid)
            
            # Return the fetched data as JSON
            return jsonify(booked_outfits), 200
        except Exception as e:
            # If there's an error, return a message with the error details
            return jsonify({'message': f'Error fetching booked outfits: {str(e)}'}), 500

    #packages routes
    @app.route('/created-packages', methods=['GET', 'OPTIONS'])
    def get_packages_route():
        """
        Route for fetching all event packages.
        OPTIONS: Handles CORS preflight requests
        GET: Returns a list of all event packages
        """
        # Handle OPTIONS requests for CORS preflight
        if request.method == 'OPTIONS':
            return jsonify({'message': 'OK'}), 200
            
        try:
            # Get packages formatted for client use
            packages = get_client_packages()
            
            # Format the results
            formatted_packages = []
            for package in packages:
                # Process venue image path if venue exists
                venue_image = None
                if package.get('venue_id'):
                    venue_image = package.get('venue_image')
                    if venue_image:
                        # Handle different path formats
                        if '\\' in venue_image:
                            venue_image = venue_image.split('\\')[-1]
                        elif '/' in venue_image:
                            venue_image = venue_image.split('/')[-1]
                        
                        # If the image is one of our static images, use direct static path
                        static_images = ['grandballroom.png', 'hogwarts.png', 'oceanview.png', 'paseo.png', 'sealavie.png']
                        if any(venue_image.endswith(img) for img in static_images):
                            venue_image = f'/img/venues-img/{venue_image}'
                        # For uploaded images, use API endpoint
                        else:
                            venue_image = f'/api/venue-image/{venue_image}'
                
                formatted_packages.append({
                    'package_id': package['package_id'],
                    'package_name': package['package_name'],
                    'capacity': package['capacity'],
                    'description': package['description'],
                    'additional_capacity_charges': float(package['additional_capacity_charges']) if package['additional_capacity_charges'] else 0,
                    'charge_unit': package['charge_unit'],
                    'total_price': float(package['total_price']) if package['total_price'] else 0,
                    'status': package['status'],
                    'venue': {
                        'name': package['venue_name'],
                        'location': package.get('location'),
                        'price': float(package.get('venue_price', 0)),
                        'capacity': package.get('venue_capacity'),
                        'description': package.get('venue_description'),
                        'image': venue_image
                    } if package.get('venue_name') else None,
                    'event_type': package.get('event_type_name'),
                    'gown_package': {
                        'name': package.get('gown_package_name'),
                        'price': float(package.get('gown_package_price', 0)),
                        'description': package.get('gown_package_description')
                    } if package.get('gown_package_name') else None,
                    'suppliers': package.get('suppliers', []),
                    'additional_services': package.get('additional_services', [])
                })
            
            return jsonify(formatted_packages), 200
        except Exception as e:
            # Log any errors that occur
            app.logger.error(f"Error fetching packages: {str(e)}")
            
            # Return a 500 error with details
            return jsonify({
                'message': 'An error occurred while fetching packages',
                'error': str(e)
            }), 500

    @app.route('/event-types', methods=['GET'])
    def get_event_types_route():
        try:
            event_types = get_event_types()
            return jsonify(event_types), 200
        except Exception as e:
            app.logger.error(f"Error fetching event types: {e}")
            return jsonify({"error": str(e)}), 500

    #additional services routes
    @app.route('/created-services', methods=['GET'])
    @jwt_required()
    def get_services_route():
        try:
            services = get_all_additional_services()
            return jsonify(services), 200
        except Exception as e:
            app.logger.error(f"Error fetching services: {e}")
            return jsonify({'message': 'An error occurred while fetching services'}), 500

    @app.route('/api/events/schedules', methods=['GET'])
    @jwt_required()
    def get_booked_schedules_route():
        try:
            schedules = get_booked_schedules()
            return jsonify(schedules)
        except Exception as e:
            app.logger.error(f"Error in get_booked_schedules route: {str(e)}")
            return jsonify({'error': str(e)}), 422

    @app.route('/events', methods=['POST'])
    @jwt_required()
    def create_event():
        try:
            # Get user ID from JWT token
            email = get_jwt_identity()
            userid = get_user_id_by_email(email)
            
            if not userid:
                return jsonify({
                    'success': False,
                    'message': 'Invalid user token'
                }), 401

            data = request.get_json()

            # Extract base event data
            event_data = {
                'userid': userid,
                'event_name': data.get('event_name'),
                'event_type': data.get('event_type'),
                'event_theme': data.get('event_theme'),
                'event_color': data.get('event_color'),
                'package_id': data.get('package_id'),
                'schedule': data.get('schedule'),
                'start_time': data.get('start_time'),
                'end_time': data.get('end_time'),
                'status': data.get('status', 'Wishlist'),
                'total_price': data.get('total_price', 0),
                'booking_type': data.get('booking_type', 'Online')
            }

            package_config = {
                'suppliers': data.get('suppliers', []),
                'outfits': data.get('outfits', []),
                'services': data.get('services', []),
                'additional_items': data.get('additional_items', [])
            }

            # Process additional services if needed
            if 'additional_services' in data:
                for service in data['additional_services']:
                    if 'service_id' in service and 'add_service_id' not in service:
                        service['add_service_id'] = service['service_id']

            # Extract inclusions
            if 'inclusions' in data:
                # Services
                if not data.get('services'):
                    data['services'] = []
                    for inclusion in data['inclusions']:
                        if inclusion['type'] == 'service' and 'data' in inclusion:
                            svc = inclusion['data']
                            if 'service_id' in svc or 'add_service_id' in svc:
                                data['services'].append(svc)
                # Suppliers
                if not data.get('suppliers'):
                    data['suppliers'] = []
                    for inclusion in data['inclusions']:
                        if inclusion['type'] == 'supplier' and 'data' in inclusion:
                            supplier_data = inclusion['data']
                            if 'supplier_id' in supplier_data:
                                data['suppliers'].append(supplier_data)
                # Outfits
                if not data.get('outfits'):
                    data['outfits'] = []
                    for inclusion in data['inclusions']:
                        if inclusion['type'] == 'outfit' and 'data' in inclusion:
                            outfit_data = inclusion['data']
                            if 'outfit_id' in outfit_data and not outfit_data.get('gown_package_id'):
                                outfit_data['gown_package_id'] = outfit_data['outfit_id']
                            data['outfits'].append(outfit_data)

            if 'services' not in data and 'additional_services' in data:
                data['services'] = data['additional_services']

            events_id = add_event_item(**event_data, **package_config)

            if events_id:
                return jsonify({
                    'success': True,
                    'message': 'Event created successfully',
                    'events_id': events_id
                }), 201
            else:
                return jsonify({
                    'success': False,
                    'message': 'Failed to create event'
                }), 500

        except Exception as e:
            app.logger.error(f"Error creating event: {str(e)}")
            return jsonify({
                'success': False,
                'message': f'Error creating event: {str(e)}'
            }), 500


    @app.route('/wishlist-packages', methods=['POST'])
    @jwt_required()
    def create_wishlist_package_route():
        try:
            email = get_jwt_identity()
            userid = get_user_id_by_email(email)
            
            if userid is None:
                return jsonify({
                    'success': False,
                    'message': 'User not found'
                }), 404

            data = request.get_json()
            app.logger.info(f"Received wishlist package data: {data}")

            # Process venue
            if 'inclusions' in data:
                venue_inclusion = next((item for item in data['inclusions'] if item['type'] == 'venue'), None)
                if venue_inclusion and 'data' in venue_inclusion:
                    venue_data = venue_inclusion['data']
                    data['venue'] = venue_data
                    if 'venue_id' in venue_data and not data.get('venue_id'):
                        data['venue_id'] = venue_data['venue_id']
                    # Attempt to get venue price if missing
                    if 'venue_price' not in venue_data:
                        try:
                            venue_id = venue_data['venue_id']
                            cursor = get_db_connection().cursor()
                            cursor.execute("SELECT venue_price FROM venues WHERE venue_id = %s", (venue_id,))
                            result = cursor.fetchone()
                            if result and result[0]:
                                venue_data['venue_price'] = float(result[0])
                            cursor.close()
                        except Exception as e:
                            app.logger.error(f"Error fetching venue price: {e}")

            # Outfit
            outfit_inclusion = next((item for item in data.get('inclusions', []) if item['type'] == 'outfit'), None)
            if not outfit_inclusion:
                data['gown_package_id'] = None
            elif 'data' in outfit_inclusion:
                outfit_data = outfit_inclusion['data']
                if 'outfit_id' in outfit_data and not outfit_data.get('gown_package_id'):
                    data['gown_package_id'] = outfit_data['outfit_id']
                elif 'gown_package_id' in outfit_data:
                    data['gown_package_id'] = outfit_data['gown_package_id']

            wishlist_id = create_wishlist_package(
                events_id=data.get('events_id'),
                package_data=data
            )

            if wishlist_id:
                return jsonify({
                    'success': True,
                    'message': 'Wishlist package created successfully',
                    'wishlist_id': wishlist_id
                }), 201
            else:
                return jsonify({
                    'success': False,
                    'message': 'Failed to create wishlist package'
                }), 500

        except Exception as e:
            app.logger.error(f"Error creating wishlist package: {str(e)}")
            return jsonify({
                'success': False,
                'message': f'Error creating wishlist package: {str(e)}'
            }), 500


    @app.route('/api/suppliers', methods=['GET'])
    def get_suppliers():
        try:
            suppliers = get_available_suppliers()
            logging.info(f"Suppliers data: {suppliers}")
            return jsonify({
                'status': 'success',
                'data': suppliers
            }), 200
        except Exception as e:
            logging.error(f"Error fetching suppliers: {e}")
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500


    @app.route('/api/init-test-suppliers', methods=['POST'])
    def init_test_suppliers():
        try:
            success = initialize_test_suppliers()
            if success:
                return jsonify({
                    'status': 'success',
                    'message': 'Test suppliers initialized successfully'
                }), 200
            else:
                return jsonify({
                    'status': 'error',
                    'message': 'Failed to initialize test suppliers'
                }), 500
        except Exception as e:
            logging.error(f"Error initializing test suppliers: {e}")
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500

    @app.route('/api/user/profile', methods=['GET'])
    @jwt_required()
    def get_user_profile():
        try:
            # Get the current user's email from JWT token
            email = get_jwt_identity()
            logging.info(f"Fetching profile for user email: {email}")
            
            # Get user ID from email
            userid = get_user_id_by_email(email)
            if not userid:
                logging.warning(f"No user found for email: {email}")
                return jsonify({
                    'status': 'error',
                    'message': 'User not found'
                }), 404

            # Query the database for user profile data
            user_data = get_user_profile_by_id(userid)
            logging.info(f"Retrieved user data: {user_data}")
            
            if not user_data:
                logging.warning(f"No profile found for user ID: {userid}")
                return jsonify({
                    'status': 'error',
                    'message': 'Profile not found'
                }), 404

            # Ensure all required fields are present
            required_fields = ['first_name', 'last_name', 'email', 'contact_number', 'profile_picture_url']
            for field in required_fields:
                if field not in user_data:
                    logging.warning(f"Missing required field in user data: {field}")
                    user_data[field] = None

            response = jsonify({
                'status': 'success',
                'data': user_data
            })
            return response, 200

        except Exception as e:
            logging.error(f"Error fetching user profile: {e}")
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500

    @app.route('/api/user/change-password', methods=['POST'])
    @jwt_required()
    def change_password_route():
        try:
            data = request.json
            current_password = data.get('current_password')
            new_password = data.get('new_password')

            if not current_password or not new_password:
                return jsonify({
                    'status': 'error',
                    'message': 'Current password and new password are required'
                }), 400

            # Get user ID from the JWT token
            email = get_jwt_identity()
            user_id = get_user_id_by_email(email)

            if not user_id:
                return jsonify({
                    'status': 'error',
                    'message': 'User not found'
                }), 404

            # Attempt to change password
            success, message = change_password(user_id, current_password, new_password)

            if success:
                return jsonify({
                    'status': 'success',
                    'message': message
                }), 200
            else:
                return jsonify({
                    'status': 'error',
                    'message': message
                }), 400

        except Exception as e:
            print(f"Error in change_password_route: {e}")
            return jsonify({
                'status': 'error',
                'message': 'An error occurred while changing password'
            }), 500

    @app.route('/api/packages', methods=['GET'])
    def get_packages():
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Get all packages with related information
            cursor.execute("""
                SELECT 
                    ep.package_id,
                    ep.package_name,
                    ep.capacity,
                    ep.description,
                    ep.additional_capacity_charges,
                    ep.charge_unit,
                    ep.total_price,
                    COALESCE(ep.status, 'active') as status,
                    v.venue_name,
                    v.location,
                    v.venue_price,
                    v.venue_capacity,
                    v.description as venue_description,
                    et.event_type_name,
                    gp.gown_package_name,
                    gp.gown_package_price,
                    gp.description as gown_package_description,
                    v.image as venue_image
                FROM event_packages ep
                LEFT JOIN venues v ON ep.venue_id = v.venue_id
                LEFT JOIN event_type et ON ep.event_type_id = et.event_type_id
                LEFT JOIN gown_package gp ON ep.gown_package_id = gp.gown_package_id
                WHERE ep.status IS NULL OR LOWER(ep.status) = 'active'
                ORDER BY ep.package_id DESC
            """)
            
            packages = cursor.fetchall()
            print(f"Found {len(packages)} packages")  # Debug log
            
            # Format the results
            formatted_packages = []
            for package in packages:
                venue_image = package[17]
                if venue_image:
                    if '\\' in venue_image:
                        venue_image = venue_image.split('\\')[-1]
                    elif '/' in venue_image:
                        venue_image = venue_image.split('/')[-1]
                    
                    static_images = ['grandballroom.png', 'hogwarts.png', 'oceanview.png', 'paseo.png', 'sealavie.png']
                    if any(venue_image.endswith(img) for img in static_images):
                        venue_image = f'/img/venues-img/{venue_image}'
                    else:
                        venue_image = f'/api/venue-image/{venue_image}'
                
                formatted_packages.append({
                    'package_id': package[0],
                    'package_name': package[1],
                    'capacity': package[2],
                    'description': package[3],
                    'additional_capacity_charges': float(package[4]) if package[4] else 0,
                    'charge_unit': package[5],
                    'total_price': float(package[6]) if package[6] else 0,
                    'status': package[7],
                    'venue': {
                        'name': package[8],
                        'location': package[9],
                        'price': float(package[10]) if package[10] else 0,
                        'capacity': package[11],
                        'description': package[12],
                        'image': venue_image
                    } if package[8] else None,
                    'event_type': package[13] if package[13] else None,
                    'gown_package': {
                        'name': package[14],
                        'price': float(package[15]) if package[15] else 0,
                        'description': package[16]
                    } if package[14] else None
                })
            
            cursor.close()
            conn.close()
            
            return jsonify({
                'status': 'success',
                'data': formatted_packages
            })
            
        except Exception as e:
            print(f"Error fetching packages: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500


    @app.route('/api/outfits-packages-bg/<path:filename>')
    def serve_outfit_package_background(filename):
        try:
            # Get the absolute path to the project root directory
            root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            bg_img_dir = os.path.join(root_dir, 'saved', 'outfits_packages_bg')
            
            # Check if the requested file exists
            requested_file_path = os.path.join(bg_img_dir, filename)
            if os.path.exists(requested_file_path):
                return send_from_directory(bg_img_dir, filename)
            else:
                # Return the first available background as fallback
                return send_from_directory(bg_img_dir, 'bg1.png')
                
        except Exception as e:
            print(f"Error serving outfit package background image {filename}: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/outfits/image/<path:filename>')
    def serve_outfit_image(filename):
        try:
            # Get the absolute path to the project root directory
            root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            outfit_img_dir = os.path.join(root_dir, 'saved', 'outfits_img')
            
            # Check if the requested file exists
            requested_file_path = os.path.join(outfit_img_dir, filename)
            if os.path.exists(requested_file_path):
                return send_from_directory(outfit_img_dir, filename)
            else:
                # Return default image
                return send_from_directory(outfit_img_dir, 'default_outfit.png')
                
        except Exception as e:
            print(f"Error serving outfit image {filename}: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/user/profile-image/<path:filename>')
    def serve_profile_image(filename):
        """Serve profile images from the users_profile directory"""
        try:
            # Get the absolute path to the project root directory
            root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            profile_img_dir = os.path.join(root_dir, 'saved', 'users_profile')
            
            # Check if the requested file exists
            image_path = os.path.join(profile_img_dir, filename)
            if os.path.exists(image_path):
                return send_from_directory(profile_img_dir, filename)
            
            # If file doesn't exist, return the dummy profile pic
            return send_from_directory(profile_img_dir, 'dummy_profile.png')
        except Exception as e:
            logger.error(f"Error serving profile image: {e}")
            try:
                # As a last resort, try to serve the dummy profile
                return send_from_directory(profile_img_dir, 'dummy_profile.png')
            except:
                return jsonify({
                    'status': 'error',
                    'message': 'Image not found'
                }), 404

    @app.route('/saved/venue_img/<path:filename>')
    def serve_venue_image(filename):
        try:
            # Get the absolute path to the project root directory
            root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            venue_img_dir = os.path.join(root_dir, 'saved', 'venue_img')
            
            # Check if the requested file exists
            requested_file_path = os.path.join(venue_img_dir, filename)
            if os.path.exists(requested_file_path):
                return send_from_directory(venue_img_dir, filename)
            else:
                # Return default venue image
                return send_from_directory(venue_img_dir, 'grandballroom.png')
        except Exception as e:
            app.logger.error(f"Error serving venue image {filename}: {e}")
            return jsonify({'message': 'Image not found'}), 404

    @app.route('/api/supplier/events', methods=['GET'])
    @jwt_required()
    def get_supplier_events():
        try:
            # Get the current user's email from JWT
            email = get_jwt_identity()
            print(f"DEBUG: JWT token contains email: {email}")
            
            # First check if the user is a supplier
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT u.userid, s.supplier_id, s.service
                FROM users u
                JOIN suppliers s ON u.userid = s.userid
                WHERE u.email = %s
            """, (email,))
            supplier_info = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if not supplier_info:
                print(f"DEBUG: User {email} is not a supplier")
                return jsonify({
                    'status': 'error',
                    'message': 'User is not a supplier'
                }), 403
                
            print(f"DEBUG: Found supplier info: {supplier_info}")
            
            # Get the supplier's booked events directly using email
            events = get_supplier_booked_events(email)
            print(f"DEBUG: Found {len(events)} events for supplier email: {email}")
            
            # Log the first event if any
            if events:
                print(f"DEBUG: First event: {events[0]}")
            else:
                print("DEBUG: No events found")
            
            return jsonify({
                'status': 'success',
                'data': events
            }), 200
            
        except Exception as e:
            print(f"Error fetching supplier events: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500

    @app.route('/api/gown-package/<int:package_id>/outfits', methods=['GET'])
    @jwt_required()
    def get_gown_package_outfits_route(package_id):
        """Get all outfits for a specific gown package"""
        try:
            outfits = get_gown_package_outfits(package_id)
            return jsonify({
                'status': 'success',
                'data': outfits
            }), 200
        except Exception as e:
            app.logger.error(f"Error fetching gown package outfits: {e}")
            return jsonify({
                'status': 'error',
                'message': 'An error occurred while fetching gown package outfits'
            }), 500

    @app.route('/api/user/update-profile-picture', methods=['POST'])
    @jwt_required()
    def update_profile_picture():
        try:
            if 'profile_image' not in request.files:
                return jsonify({
                    'status': 'error',
                    'message': 'No file provided'
                }), 400

            file = request.files['profile_image']
            if file.filename == '':
                return jsonify({
                    'status': 'error',
                    'message': 'No file selected'
                }), 400

            # Get current user's email from JWT
            email = get_jwt_identity()
            user_id = get_user_id_by_email(email)
            
            if not user_id:
                return jsonify({
                    'status': 'error',
                    'message': 'User not found'
                }), 404

            # Check if file type is allowed
            allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
            if not '.' in file.filename or \
               file.filename.rsplit('.', 1)[1].lower() not in allowed_extensions:
                return jsonify({
                    'status': 'error',
                    'message': 'Invalid file type'
                }), 400

            # Create a secure filename with timestamp and UUID
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            file_extension = file.filename.rsplit('.', 1)[1].lower()
            filename = f"profile_{user_id}_{timestamp}_{str(uuid.uuid4())[:8]}.{file_extension}"
            
            # Get the absolute path to the project root directory
            root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            profile_img_dir = os.path.join(root_dir, 'saved', 'users_profile')
            
            # Ensure the directory exists
            os.makedirs(profile_img_dir, exist_ok=True)
            
            # Save file to the specified directory
            save_path = os.path.join(profile_img_dir, filename)
            file.save(save_path)

            # Update user's profile picture in database
            if update_user_profile_picture(user_id, filename):
                return jsonify({
                    'status': 'success',
                    'message': 'Profile picture updated successfully',
                    'data': {
                        'image_url': filename
                    }
                }), 200
            else:
                # If database update fails, delete the uploaded file
                if os.path.exists(save_path):
                    os.remove(save_path)
                return jsonify({
                    'status': 'error',
                    'message': 'Failed to update profile picture in database'
                }), 500

        except Exception as e:
            logger.error(f"Error updating profile picture: {e}")
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500

    @app.route('/event-feedback', methods=['POST'])
    @jwt_required()
    def submit_event_feedback():
        try:
            # Get current user's email and ID
            email = get_jwt_identity()
            userid = get_user_id_by_email(email)
            
            if not userid:
                return jsonify({
                    'status': 'error',
                    'message': 'User not found'
                }), 404

            data = request.json
            events_id = data.get('events_id')
            rating = data.get('rating')
            feedback_text = data.get('feedback_text')

            # Validate required fields
            if not events_id or not rating:
                return jsonify({
                    'status': 'error',
                    'message': 'Event ID and rating are required'
                }), 400

            # Validate rating range
            if not isinstance(rating, int) or rating < 1 or rating > 5:
                return jsonify({
                    'status': 'error',
                    'message': 'Rating must be a number between 1 and 5'
                }), 400

            # Add the feedback
            success, result = add_event_feedback(events_id, userid, rating, feedback_text)
            
            if success:
                return jsonify({
                    'status': 'success',
                    'message': 'Feedback submitted successfully',
                    'feedback_id': result
                }), 201
            else:
                return jsonify({
                    'status': 'error',
                    'message': result
                }), 409 if "already submitted" in str(result) else 500

        except Exception as e:
            app.logger.error(f"Error submitting feedback: {e}")
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500

    @app.route('/event-feedback/<int:events_id>', methods=['GET'])
    @jwt_required()
    def get_event_feedbacks(events_id):
        try:
            feedbacks = get_event_feedback(events_id)
            return jsonify({
                'status': 'success',
                'data': feedbacks
            }), 200
        except Exception as e:
            app.logger.error(f"Error getting event feedbacks: {e}")
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500

    @app.route('/api/user/update-profile', methods=['PUT'])
    @jwt_required()
    def update_user_profile_route():
        try:
            # Get the current user's email from JWT token
            email = get_jwt_identity()
            userid = get_user_id_by_email(email)
            
            if not userid:
                return jsonify({
                    'status': 'error',
                    'message': 'User not found'
                }), 404

            data = request.get_json()
            firstname = data.get('firstname')
            lastname = data.get('lastname')
            username = data.get('username')
            contactnumber = data.get('contactnumber')
            address = data.get('address')

            # Update the profile using the existing model function
            success = update_user_profile(
                userid=userid,
                firstname=firstname,
                lastname=lastname,
                username=username,
                contactnumber=contactnumber,
                address=address
            )

            if success:
                return jsonify({
                    'status': 'success',
                    'message': 'Profile updated successfully'
                }), 200
            else:
                return jsonify({
                    'status': 'error',
                    'message': 'Failed to update profile'
                }), 400

        except Exception as e:
            logger.error(f"Error updating user profile: {e}")
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500

    @app.route('/events-by-month', methods=['GET'])
    def events_by_month():
        """
        Returns event counts per month for each event type.
        Response format:
        {
            "eventTypes": ["Wedding", "Birthday", ...],
            "data": {
                "Wedding": [countJan, countFeb, ..., countDec],
                "Birthday": [countJan, ...]
            }
        }
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # Get all event types
            cursor.execute("SELECT event_type_name FROM event_type")
            event_types = [row[0] for row in cursor.fetchall()]

            # Prepare data dict
            data = {}
            for event_type in event_types:
                # Count events per month for this type
                cursor.execute("""
                    SELECT MONTH(schedule) as month, COUNT(*) 
                    FROM events 
                    WHERE event_type = %s
                    GROUP BY MONTH(schedule)
                """, (event_type,))
                month_counts = {row[0]: row[1] for row in cursor.fetchall()}
                # Fill in 0 for months with no events
                counts = [month_counts.get(i, 0) for i in range(1, 13)]
                data[event_type] = counts

            cursor.close()
            conn.close()

            return jsonify({
                "eventTypes": event_types,
                "data": data
            }), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route('/events', methods=['GET'])
    def get_events():
        try:
            conn = db.get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("""
                SELECT 
                    event_id,
                    event_type,
                    schedule,
                    event_name,
                    event_theme,
                    status
                FROM events 
                WHERE schedule >= CURRENT_DATE
                ORDER BY schedule ASC
            """)
            
            events = cursor.fetchall()
            cursor.close()
            conn.close()
            
            return jsonify(events)
            
        except Exception as e:
            print(f"Error fetching events: {e}")
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/users/<int:userid>', methods=['GET', 'OPTIONS'])
    @app.route('/api/users/info/<int:userid>', methods=['GET', 'OPTIONS'])
    @app.route('/api/user-details/<int:userid>', methods=['GET', 'OPTIONS'])
    @jwt_required(optional=True)  # Make JWT optional to handle OPTIONS requests
    def get_user_info_route(userid):
        if request.method == 'OPTIONS':
            response = jsonify({'message': 'OK'})
            response.headers.add('Access-Control-Allow-Origin', 'http://localhost:5174')
            response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
            response.headers.add('Access-Control-Allow-Methods', 'GET,OPTIONS')
            response.headers.add('Access-Control-Allow-Credentials', 'true')
            return response, 200
            
        try:
            # Query the database for user profile data
            user_data = get_user_profile_by_id(userid)
            
            if not user_data:
                return jsonify({
                    'status': 'error',
                    'message': 'User not found'
                }), 404

            return jsonify({
                'status': 'success',
                'data': user_data
            }), 200
            
        except Exception as e:
            logging.error(f"Error fetching user by id: {e}")
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500
    
    # Supplier Availability Endpoints
    @app.route('/api/supplier/availability', methods=['GET'])
    @jwt_required()
    def get_supplier_availability_route():
        try:
            email = get_jwt_identity()
            print(f"DEBUG: JWT identity (email): {email}")
            
            supplier_id = get_supplier_id_by_email(email)
            print(f"DEBUG: Supplier ID: {supplier_id}")
            
            if not supplier_id:
                print(f"DEBUG: User {email} is not a supplier")
                return jsonify({
                    'status': 'error',
                    'message': 'User is not a supplier'
                }), 403
            
            # Get query parameters for date range
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')
            print(f"DEBUG: Date range - start: {start_date}, end: {end_date}")
            
            availability = get_supplier_availability(supplier_id, start_date, end_date)
            print(f"DEBUG: Availability data: {availability}")
            
            return jsonify({
                'status': 'success',
                'data': availability
            }), 200
            
        except Exception as e:
            print(f"DEBUG: Error in availability route: {e}")
            logging.error(f"Error fetching supplier availability: {e}")
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500

    @app.route('/api/supplier/availability', methods=['POST'])
    @jwt_required()
    def set_supplier_availability_route():
        try:
            email = get_jwt_identity()
            supplier_id = get_supplier_id_by_email(email)
            
            if not supplier_id:
                return jsonify({
                    'status': 'error',
                    'message': 'User is not a supplier'
                }), 403
            
            data = request.json
            date = data.get('date')
            is_available = data.get('is_available', True)
            reason = data.get('reason')
            
            if not date:
                return jsonify({
                    'status': 'error',
                    'message': 'Date is required'
                }), 400
            
            set_supplier_availability(supplier_id, date, is_available, reason)
            
            return jsonify({
                'status': 'success',
                'message': 'Availability updated successfully'
            }), 200
            
        except Exception as e:
            logging.error(f"Error setting supplier availability: {e}")
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500

    @app.route('/api/supplier/availability/<date>', methods=['DELETE'])
    @jwt_required()
    def delete_supplier_availability_route(date):
        try:
            email = get_jwt_identity()
            supplier_id = get_supplier_id_by_email(email)
            
            if not supplier_id:
                return jsonify({
                    'status': 'error',
                    'message': 'User is not a supplier'
                }), 403
            
            deleted = delete_supplier_availability(supplier_id, date)
            
            if deleted:
                return jsonify({
                    'status': 'success',
                    'message': 'Availability removed successfully'
                }), 200
            else:
                return jsonify({
                    'status': 'error',
                    'message': 'No availability record found for this date'
                }), 404
            
        except Exception as e:
            logging.error(f"Error deleting supplier availability: {e}")
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500