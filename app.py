from flask import Flask, request, jsonify, session #session stores login info
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your-secret-key'
CORS(app,supports_credentials= True)

#File upload settings
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSION = {'pdf', 'doc', 'docx', 'txt', 'ppt', 'pptx'}


#check if file extention is allowed
def allowed_file(filename):
    return '.' in filename and \
filename.rsplit('.',1)[1].lower() in ALLOWED_EXTENSION #split right side after '.' 1 -refers to slice 1 content after dot and [1] refers to take the 1th indexed value from sliced list
#['notes.pdf']=['notes','pdf']=[1]=['pdf']



#rishimina 8500

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def init_db():
    conn = sqlite3.connect('studybuddy.db')
    cursor = conn.cursor()
    #USER TABLE
    cursor.execute('''
                CREATE TABLE IF NOT EXISTS users(
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   username TEXT NOT NULL UNIQUE,
                   email TEXT NOT NULL UNIQUE,
                   password TEXT NOT NULL,
                   role TEXT DEFAULT 'student', 
                   created_at TEXT
                   )
            ''')
    
    #Resourse table - study materials upload
    #forign key this reference(user_id) == users(id)
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS resources(
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   user_id INTEGER NOT NULL,
                   title TEXT NOT NULL,
                   description TEXT ,
                   subject TEXT ,
                   filename TEXT NOT NULL,
                   file_path TEXT NOT NULL,
                   created_at TEXT,
                   FOREIGN KEY (user_id) REFERENCES users(id) 
                   )
                   ''')
    
    #ratings table
    ##same user cannot rate multiple times #unique combination
    cursor.execute(''' 
            CREATE TABLE IF NOT EXISTS ratings(
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   resource_id INTEGER NOT NULL,
                   user_id INTEGER NOT NULL,
                   ratings INTEGER NOT NULL,
                   created_at TEXT,
                   FOREIGN KEY  (resource_id) REFERENCES resources(id),
                   FOREIGN KEY  (user_id) REFERENCES users(id),
                    UNIQUE(resource_id,user_id) 
                   )
                ''')
    
    #comments table
    #similar to ratings but no unique - 1 user can comment multiple times
    cursor.execute(''' 
        CREATE TABLE IF NOT EXISTS comments(
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   resource_id INTEGER NOT NULL,
                   user_id INTEGER NOT NULL,
                   comment_text TEXT NOT NULL,
                   created_at TEXT,
                   FOREIGN KEY (resource_id) REFERENCES resources (id),
                   FOREIGN KEY (user_id) REFERENCES users (id)
                   )
                ''')
    
    conn.commit()
    conn.close()


init_db()

@app.route('/')
def home():
    return jsonify({"messege" : "StudyBuddy API" , "status" : "running"})

@app.route('/register',methods=['POST'])
def register():
    data = request.json
    username=data.get('username')
    email = data.get('email')
    password = data.get('password')

    #validation
    if not username or not email or not password:
        return jsonify({"error": " All feilds are rquired"})
    
    if(len(password) < 6):
        return jsonify({"error": "password must ahve atleast 6 characters"})

    #hash the password
    hashed_password = generate_password_hash(password)

    try:
        conn= sqlite3.connect('studybuddy.db')
        cursor = conn.cursor()

        cursor.execute(''' 
            INSERT INTO users (username,email,password,created_at)
                       VALUES(?,?,?,?)
                       ''',(username,email,hashed_password,datetime.now().isoformat()))
        
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()


        return jsonify({
            "message": "User Registered succesfully",
            "user_id" : user_id
        }),201

    except sqlite3.IntegrityError:
        return jsonify({"error": "Username or email already exists"}),400
    

#login  - Autenticate user
@app.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"error" : "Username and password required"})
    
    conn=sqlite3.connect('studybuddy.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    #Find User by username
    cursor.execute('SELECT* FROM users WHERE username = ?',(username,))
    user = cursor.fetchone()
    conn.close()

    if not user:
        return jsonify({"error" : "username or password Invalid"}),401
    
    #CHECK IF PASSWORD MATCHES
    if not check_password_hash(user['password'],password):
        return jsonify({"error" : "username or password Invalid"}),401
    
    #STORE USER IN SESSION(AS YOU LOGIN YOU CAN SEE YOU RELATED INFO)

    session['user_id'] = user['id']
    session['username'] = user['username']
    session['role'] = user['role']


    return jsonify({
        "messege" : "Login Successfully",
        "user" : {
            "id":user['id'],
            "username":user['username'],
            "email":user['email'],
            "role":user['role'],
        }
    })

#LOGOUT ROUTE ie LOGOUT SESSION
@app.route('/logout',methods = ['POST'])
def logout():
    session.clear()
    return jsonify({"message":"Logged out successfully"})


#CHECK WHO IS LOGGES IN (DISPLAY USER INFO )
@app.route('/me', methods = ['GET'])
def get_current_user():
    if 'user_id' not in session:
        return jsonify({"error" : "Not Logged in"}),401
    
    return jsonify({
        "user" : {
            "id":  session['user_id'],
            "username" : session['username'],
            "role" : session['role']
        }
    })


#UPLOAD RESOURCE - ONLY WHEN LOGGED IN
@app.route('/resources' , methods=['POST'])
def upload_resource():
    #check login status
    if 'user_id' not in session:
        return jsonify({"error":" Please Login first"}),401
    
    #check if file is in request
    if 'file' not in request.files:
        return jsonify({"error":" No file provided"}),400
    
    file = request.files['file']

    #check if file was actually selected
    if file.filename=='':
        return jsonify({"error":" No file selected"}),400
        
    #get form data
    title = request.form.get('title')
    description = request.form.get('description' , '')
    subject = request.form.get('subject' , '')

    if not title:
        return jsonify({"error":" Title is required"}),400

    #check if file type is allowed
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)

        unique_filename = f"{session['user_id']}_{datetime.now().timestamp()}_{filename}"

        #savig file
        file_path = os.path.join(app.config['UPLOAD_FOLDER'],unique_filename)
        file.save(file_path)


        #save to database
        conn = sqlite3.connect('studybuddy.db')
        cursor = conn.cursor()

        cursor.execute(''' 
                    INSERT INTO resources (user_id,title,description,subject,filename,file_path,created_at)  
                       VALUES (?,?,?,?,?,?,?)
                        ''',(session['user_id'],title,description,subject,filename,file_path,datetime.now().isoformat()))
        
        conn.commit()
        resource_id = cursor.lastrowid
        conn.close()


        return jsonify({
            "message" : "Resource uploaded successfully",
            "resource_id" :resource_id
        }),201
    #else
    return jsonify({"error":" File is not allowed.Use other extention"}),400
    

if __name__ == "__main__":
    import os
    port = int(os.environ.get('PORT' , 5000))
    app.run(host = '0.0.0.0', port = port, debug = True)