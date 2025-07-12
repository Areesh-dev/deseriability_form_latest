from flask import Flask, request, jsonify
from flask_cors import CORS
import pyodbc
import json
import logging

app = Flask(__name__)
CORS(app)  # Enable CORS

# Configure logging
logging.basicConfig(level=logging.DEBUG)
app.logger.setLevel(logging.DEBUG)

# Database Configuration (UPDATE WITH YOUR VALUES)
HOST = 'localhost'         # Or your server IP
PORT = '1433'              # Default SQL Server port
DATABASE = 'juno'
USERNAME = 'root' # SQL authentication username
PASSWORD = '03102000' # SQL authentication password
DRIVER = '{ODBC Driver 17 for SQL Server}'

def get_db_connection():
    try:
        # Try multiple connection string formats
        connection_strings = [
            # Standard SQL Server auth
            f'DRIVER={DRIVER};SERVER={HOST},{PORT};DATABASE={DATABASE};UID={USERNAME};PWD={PASSWORD};',
            
            # Trusted connection alternative
            f'DRIVER={DRIVER};SERVER={HOST};DATABASE={DATABASE};Trusted_Connection=yes;',
            
            # Try with instance name
            f'DRIVER={DRIVER};SERVER={HOST}\\SQLEXPRESS;DATABASE={DATABASE};UID={USERNAME};PWD={PASSWORD};',
            
            # Try with TCP protocol explicitly
            f'DRIVER={DRIVER};SERVER=tcp:{HOST},{PORT};DATABASE={DATABASE};UID={USERNAME};PWD={PASSWORD};'
        ]

        for conn_str in connection_strings:
            try:
                app.logger.debug(f"Trying connection string: {conn_str}")
                conn = pyodbc.connect(conn_str, timeout=30)  # Increased timeout
                app.logger.info("Database connection successful")
                return conn
            except pyodbc.Error as e:
                app.logger.warning(f"Connection attempt failed: {str(e)}")
                continue

        raise ConnectionError("All connection attempts failed")

    except Exception as e:
        app.logger.error(f"Database connection failed: {str(e)}")
        raise

@app.route('/submit', methods=['POST'])
def submit_form():
    try:
        app.logger.debug("Received submission request")
        
        # Get and log raw request data
        raw_data = request.data
        app.logger.debug(f"Raw request data: {raw_data.decode('utf-8') if raw_data else 'Empty'}")
        
        # Parse JSON data
        data = request.get_json()
        if not data:
            app.logger.error("No JSON data received")
            return jsonify({"success": False, "error": "No data received"}), 400
        
        app.logger.debug(f"Received JSON data: {json.dumps(data, indent=2)}")
        
        # Validate required fields
        required_personal = ['name', 'gender', 'city', 'email', 'phone', 'occupation']
        if 'personalInfo' not in data or not all(data['personalInfo'].get(field) for field in required_personal):
            app.logger.error("Missing required personal info fields")
            return jsonify({"success": False, "error": "Missing required personal information"}), 400
        
        # Validate responses structure
        if 'responses' not in data or not isinstance(data['responses'], dict):
            app.logger.error("Invalid responses structure")
            return jsonify({"success": False, "error": "Invalid responses format"}), 400
        
        # Prepare values for insertion
        values = {
            'full_name': data['personalInfo']['name'][:100],
            'gender': data['personalInfo']['gender'][:20],
            'city': data['personalInfo']['city'][:50],
            'email': data['personalInfo']['email'][:100],
            'phone': data['personalInfo']['phone'][:20],
            'occupation': data['personalInfo']['occupation'][:50],
        }
        
        # Map response groups to columns
        response_mapping = {
            'weekend': 'weekend_options',
            'meeting': 'meeting_feeling',
            'vibe': 'vibe_selections',
            'new_things': 'last_new_thing',
            'frustrations': 'main_frustration',
            'blockers': 'meeting_blocker',
            'safe_fun': 'safe_fun_option',
            'platform': 'platform_likelihood'
        }
        
        # Process responses
        for group, column in response_mapping.items():
            group_data = data['responses'].get(group, {})
            answers = group_data.get('answers', [])
            # Extract values and join with comma
            values[column] = ','.join([str(a.get('value', '')) for a in answers])[:255]
        
        app.logger.debug(f"Prepared values: {values}")
        
        # Database insertion
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO desirablity_form_responses (
            full_name, gender, city, email, phone, occupation, 
            weekend_options, meeting_feeling, vibe_selections, 
            last_new_thing, main_frustration, meeting_blocker, 
            safe_fun_option, platform_likelihood
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', 
        values['full_name'],
        values['gender'],
        values['city'],
        values['email'],
        values['phone'],
        values['occupation'],
        values['weekend_options'],
        values['meeting_feeling'],
        values['vibe_selections'],
        values['last_new_thing'],
        values['main_frustration'],
        values['meeting_blocker'],
        values['safe_fun_option'],
        values['platform_likelihood'])
        
        conn.commit()
        conn.close()
        
        app.logger.info("Form submitted successfully")
        return jsonify({"success": True, "message": "Form submitted successfully!"}), 200
        
    except pyodbc.Error as e:
        app.logger.error(f"Database error: {str(e)}")
        return jsonify({"success": False, "error": f"Database error: {str(e)}"}), 500
    except Exception as e:
        app.logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return jsonify({"success": False, "error": f"Server error: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)