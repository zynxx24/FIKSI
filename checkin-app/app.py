from flask import Flask, render_template, request, session, redirect, jsonify, url_for, flash, send_file
import json
import os
from datetime import timedelta
import re
import qrcode
from io import BytesIO
from datetime import datetime
from collections import defaultdict

app = Flask(__name__, template_folder='asset/templates', static_folder='asset/static')
# Store credentials and secret keys securely in environment variables (set these in your environment)
app.secret_key = os.getenv('SECRET_KEY', 'default_secret')  # Replace with secure key in production
app.permanent_session_lifetime = timedelta(hours=18)  # Set session timeout to 18 hours

# File paths (could be switched to a proper database later)
USERS_DB = os.getenv('USERS_DB', 'data/users.json')
VALID_QR_DB = os.getenv('VALID_QR_DB', 'data/valid_qr_codes.json')
QR_IMAGES_FOLDER = 'asset/static/import/qr_codes/'  # Folder to store generated QR codes

# Ensure required files and directories exist
if not os.path.exists(USERS_DB):
    with open(USERS_DB, 'w') as f:
        json.dump([], f)

if not os.path.exists(VALID_QR_DB):
    with open(VALID_QR_DB, 'w') as f:
        json.dump(['VALIDQR123', 'VALIDQR456'], f)

if not os.path.exists(QR_IMAGES_FOLDER):
    os.makedirs(QR_IMAGES_FOLDER)

# Abstraction for file load/save to avoid repetition
def load_json(file_path, default_data=None):
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            return json.load(file)
    return default_data if default_data else []

def save_json(file_path, data):
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=4)

# Load valid QR codes from JSON file
def load_valid_qr_codes():
    return load_json(VALID_QR_DB, [])

# Load users data from JSON file
def load_users():
    return load_json(USERS_DB, [])

# Save users data to JSON file
def save_users(data):
    save_json(USERS_DB, data)

# Find user by NIS (search using regex to ensure only numeric input is processed)
def find_user_by_nis(nis):
    if re.match(r'^\d+$', nis):  # Ensure NIS is only digits
        users = load_users()
        return next((user for user in users if user['nis'] == nis), None)
    return None


# Update user check-in count
def update_user_checkin(nis, name, class_name, absen):
    users = load_users()
    current_time = datetime.now().isoformat()  # Save the current time in ISO format

    for user in users:
        if user['nis'] == nis:
            user['checkin_count'] = user.get('checkin_count', 0) + 1
            user['last_checkin'] = current_time  # Save the check-in time
            save_users(users)
            return user

    # Create new user if not found
    new_user = {
        'nis': nis,
        'name': name,
        'class': class_name,
        'absen': absen,
        'checkin_count': 1,
        'last_checkin': current_time  # Save the first check-in time
    }
    users.append(new_user)
    save_users(users)
    return new_user


# Function to generate a QR code and save as an image
def generate_qr_code(data, file_name):
    img = qrcode.make(data)
    file_path = os.path.join(QR_IMAGES_FOLDER, file_name)
    img.save(file_path)
    return file_path

# Tambahkan handler untuk 404
@app.errorhandler(404)
def page_not_found(e):
    flash('Halaman yang Anda cari tidak ditemukan, diarahkan kembali ke home.')
    return redirect(url_for('home'))

@app.route('/')
def home():
    return render_template('qr_scan.html')

@app.route('/validate_qr', methods=['POST'])
def validate_qr():
    qr_data = request.json.get('qr_data')  # Ambil data QR dari input
    valid_qr_codes = load_valid_qr_codes()  # Muat QR valid dari file JSON

    if qr_data in valid_qr_codes:
        session.permanent = True  # Persistent session untuk user
        session['admin_qr'] = True  # Tandai bahwa user berhasil memvalidasi QR
        return jsonify({'success': True})  # QR code valid
    return jsonify({'success': False})  # QR code tidak valid

@app.route('/checkin')
def checkin():
    if session.get('admin_qr'):
        return render_template('checkin.html')
    # Tambahkan pesan flash untuk memberi tahu user bahwa mereka perlu memvalidasi QR dulu
    flash('You need to validate the QR code first!')
    return redirect('/')

@app.route('/submit_checkin', methods=['POST'])
def submit_checkin():
    if session.get('admin_qr'):
        nis = request.form['nis']
        name = request.form['name']
        class_name = request.form['class']
        absen = request.form['absen']

        # Tambahkan batasan panjang input NIS dan Absen
        if not re.match(r'^\d{1,10}$', nis) or not name or not class_name or not re.match(r'^\d{1,2}$', absen):
            flash("Invalid input", "error")
            return redirect('/checkin')  # Kembali ke halaman check-in
        
        # Update atau simpan data pengguna dengan waktu check-in yang tercatat
        update_user_checkin(nis, name, class_name, absen)  # Panggil fungsi untuk menyimpan data
        session['checkin'] = True
        return redirect('/cooldown')
    
    flash("You need to validate the QR code first!", "error")  # Pesan error jika QR belum divalidasi
    return redirect('/')

@app.route('/cooldown')
def cooldown():
    if session.get('checkin'):
        return render_template('cooldown.html')
    return redirect('/')

# Admin credentials should be stored in environment variables in production for better security
admin_credentials = [
    {'username': os.getenv('ADMIN_USERNAME', 'wira'), 'password': os.getenv('ADMIN_PASSWORD', 'wira'),
     'redeemcode': os.getenv('ADMIN_REDEEMCODE', '121217'), 'email': os.getenv('ADMIN_EMAIL', 'contoh@gmail.com')}
]

@app.route('/admin', methods=['GET', 'POST'])
def admin_admin():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        redeemcode = request.form.get('redeemcode')
        email = request.form.get('email')

        for admin in admin_credentials:
            if (username == admin['username'] and 
                password == admin['password'] and
                redeemcode == admin.get('redeemcode') and
                email == admin.get('email')):
                session['admin_login'] = True
                return redirect('admin_dashboard')  # Redirect instead of render template

        # Redirect kembali ke admin login untuk menghindari refresh loop
        flash('Invalid credentials, please try again!')
        return redirect('/admin')

    return render_template('admin_login.html')

@app.route('/chart-data', methods=['POST'])
def chart_data():
    # Load all user data (check-in)
    users = load_users()

    # Return empty arrays if there are no users
    if not users:
        return jsonify({
            'labels': [],
            'checkin_counts': [],
            'start_date': None,
            'end_date': None
        })

    # Get start and end dates from request; if not provided, use the earliest and latest check-in dates
    start_date = request.json.get('start_date')
    end_date = request.json.get('end_date')

    # If no input dates, use the earliest and latest check-in dates from data
    if not start_date or not end_date:
        all_checkin_dates = [
            datetime.fromisoformat(user['last_checkin']).date() 
            for user in users if 'last_checkin' in user
        ]
        if not all_checkin_dates:
            return jsonify({
                'labels': [],
                'checkin_counts': [],
                'start_date': None,
                'end_date': None
            })
        start_date = min(all_checkin_dates).isoformat()
        end_date = max(all_checkin_dates).isoformat()

    # Convert string to datetime
    start_date = datetime.fromisoformat(start_date)
    end_date = datetime.fromisoformat(end_date)

    # Create a dictionary to count check-ins per date
    checkin_counts_by_date = defaultdict(int)

    for user in users:
        if 'last_checkin' in user:
            checkin_date = datetime.fromisoformat(user['last_checkin']).date()
            if start_date.date() <= checkin_date <= end_date.date():
                checkin_counts_by_date[checkin_date] += 1

    sorted_dates = sorted(checkin_counts_by_date.keys())
    labels = [date.isoformat() for date in sorted_dates]
    checkin_counts = [checkin_counts_by_date[date] for date in sorted_dates]

    return jsonify({
        'labels': labels,
        'checkin_counts': checkin_counts,
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat()
    })

@app.route('/logout', methods=['POST'])
def admin_logout():
    if session.get('admin_login'):
        session.pop('admin_login', None)
        return redirect('/admin')
    return redirect('/admin')

from datetime import datetime, timedelta

@app.route('/admin_dashboard', methods=['GET', 'POST'])
def admin_dashboard():
    if session.get('admin_login'):
        generated_qr_image = None  # Placeholder untuk gambar QR code
        chatbot_response = None  # Placeholder untuk chatbot response

        if 'last_generated_qr' in session:
            last_qr_filename = session['last_generated_qr']
            generated_qr_image = url_for('static', filename=f'import/qr_codes/{last_qr_filename}')

        # Handle QR Code generation
        if request.method == 'POST' and 'qr_data' in request.form:
            qr_data = request.form.get('qr_data')
            if qr_data:
                # Ensure QR folder exists
                img_folder = QR_IMAGES_FOLDER

                if not os.path.exists(img_folder):
                    os.makedirs(img_folder, exist_ok=True)

                # Generate QR code and save it
                img = qrcode.make(qr_data)
                img_filename = f"{qr_data}.png"
                os.chmod(QR_IMAGES_FOLDER, 0o777)
                img_folder = QR_IMAGES_FOLDER
                img_path = os.path.join(img_folder, img_filename)
                os.chmod(img_folder, 0o777)
                img.save(img_path)

                # Save QR data to valid QR database
                valid_qr_codes = load_valid_qr_codes()
                valid_qr_codes.append(qr_data)
                save_json(VALID_QR_DB, valid_qr_codes)

                # Set generated QR image URL
                generated_qr_image = url_for('static', filename=f'import/qr_codes/{img_filename}')
                session['last_generated_qr'] = img_filename

        if request.method == 'POST' and 'message' in request.form:
            message = request.form.get('message')
            if message:
                if re.match(r'^\d+$', message):
                    user = find_user_by_nis(message)
                    if user:
                        total_checkin = user.get('checkin_count', 0)
                        chatbot_response = f"{user['name']}, Kelas: {user['class']}, Absen: {user['absen']}, Total Check-ins: {total_checkin}"
                    else:
                        chatbot_response = "NIS tidak ditemukan."
                else:
                    chatbot_response = "Input tidak valid. Silakan masukkan NIS."


        # Load QR codes and users
        qr_codes = load_valid_qr_codes()
        qr_images = [f"{QR_IMAGES_FOLDER}{code}.png" for code in qr_codes]
        users = load_users()

        # Calculate analytics
        total_visitors = len(users)
        total_checkin = sum(user.get('checkin_count', 0) for user in users)
        avg_checkin = total_checkin / total_visitors if total_visitors > 0 else 0

        # Calculate absent users within last 18 hours
        eighteen_hours_ago = datetime.now() - timedelta(hours=48)
        recent_absent_users = [
            user for user in users if 'last_checkin' in user and
            datetime.fromisoformat(user['last_checkin']) < eighteen_hours_ago
        ]
        recent_absent_users = sorted(recent_absent_users, key=lambda x: x.get('checkin_count', 0), reverse=True)[:10]
        absent_count = len(recent_absent_users)

        return render_template('admin_dashboard.html', 
                               qr_codes=qr_codes, 
                               qr_images=qr_images, 
                               total_visitors=total_visitors, 
                               avg_checkin=avg_checkin, 
                               recent_absent_users=recent_absent_users, 
                               generated_qr_image=generated_qr_image, 
                               chatbot_response=chatbot_response, 
                               users=users,
                               absent_count=absent_count)
    return redirect('/admin')

if __name__ == '__main__':
    app.run(debug=True)
