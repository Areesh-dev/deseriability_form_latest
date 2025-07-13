from flask import Flask, request, jsonify
from flask_cors import CORS
import pymysql
import logging
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.DEBUG)
app.logger.setLevel(logging.DEBUG)

# MySQL Configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '03102000',
    'database': 'juno',
    'port': 3306
}

def get_db_connection():
    try:
        connection = pymysql.connect(
            host=DB_CONFIG['host'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            database=DB_CONFIG['database'],
            port=DB_CONFIG['port'],
            cursorclass=pymysql.cursors.DictCursor
        )
        app.logger.info("Database connection successful")
        return connection
    except pymysql.Error as e:
        app.logger.error(f"Database connection failed: {str(e)}")
        raise

@app.route('/submit', methods=['POST'])
def submit_form():
    conn = None
    cursor = None
    try:
        data = request.get_json()
        app.logger.debug(f"Received data: {data}")
        
        # Validate required fields
        required_fields = ['name', 'gender', 'city', 'email', 'phone', 'occupation']
        personal_info = data.get('personalInfo', {})
        
        if not all(personal_info.get(field) for field in required_fields):
            return jsonify({"success": False, "error": "All personal information fields are required"}), 400
        
        # Check for duplicate submission
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id FROM desirablity_form_responses 
            WHERE email = %s OR phone = %s 
            LIMIT 1
        """, (personal_info['email'], personal_info['phone']))
        
        if cursor.fetchone():
            return jsonify({
                "success": False,
                "error": "This email or phone number has already been used"
            }), 400
        
        # Prepare data for insertion
        values = {
            'full_name': personal_info['name'][:100],
            'gender': personal_info['gender'][:20],
            'city': personal_info['city'][:50],
            'email': personal_info['email'][:100],
            'phone': personal_info['phone'][:20],
            'occupation': personal_info['occupation'][:50],
        }
        
        # Process responses
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
        
        for group, column in response_mapping.items():
            answers = data.get('responses', {}).get(group, {}).get('answers', [])
            values[column] = ','.join(str(a.get('value', '')) for a in answers)[:255]
        
        # Insert record
        cursor.execute("""
            INSERT INTO desirablity_form_responses (
                full_name, gender, city, email, phone, occupation,
                weekend_options, meeting_feeling, vibe_selections,
                last_new_thing, main_frustration, meeting_blocker,
                safe_fun_option, platform_likelihood
            ) VALUES (
                %(full_name)s, %(gender)s, %(city)s, %(email)s, %(phone)s, %(occupation)s,
                %(weekend_options)s, %(meeting_feeling)s, %(vibe_selections)s,
                %(last_new_thing)s, %(main_frustration)s, %(meeting_blocker)s,
                %(safe_fun_option)s, %(platform_likelihood)s
            )
        """, values)
        
        conn.commit()
        return jsonify({"success": True, "message": "Form submitted successfully"}), 200
        
    except pymysql.Error as e:
        app.logger.error(f"Database error: {str(e)}")
        if conn:
            conn.rollback()
        return jsonify({"success": False, "error": "Database error occurred"}), 500
    except Exception as e:
        app.logger.error(f"Unexpected error: {str(e)}")
        if conn:
            conn.rollback()
        return jsonify({"success": False, "error": "An unexpected error occurred"}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == '__main__':
    app.run(debug=True, port=5000)
