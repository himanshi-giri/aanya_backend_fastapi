# from flask import Flask, jsonify , request , make_response, render_template, Response
# from flask_cors import CORS
# from pymongo import MongoClient
# from dotenv import load_dotenv
# import os
# #from database.db import init_db
# from datetime import timedelta, datetime
# from providers.ClaudeAI import ClaudeAI
# from providers.ClaudeAI2 import ClaudeAI2

# from functools import wraps
# import jwt
# import json
# import traceback
# from helpers.Utils import Utils
# from werkzeug.utils import secure_filename

# SECRET_KEY = "your_secret_key_here"  # Replace with an environment variable for security

# # MongoDB connection string (Replace with your actual details)
# # MONGO_URI = "mongodb+srv://info:rZHHtbPyt3idpUBR@aitutor.yime0.mongodb.net/annya?retryWrites=true&w=majority&appName=AITutor"

# system_cards = {}

# # Initialize Flask app
# app = Flask(__name__)
# CORS(app,methods=["GET", "POST"],supports_credentials=True)
# # Connect to MongoDB
# load_dotenv()
# claude_ai = ClaudeAI()

# claude_ai_old = ClaudeAI2()

# app.config['UPLOAD_FOLDER'] = 'uploads'  # Specify your upload directory

# # Generate a random secret key for the Flask application
# app.secret_key = os.urandom(24)

# system = ""
# # Read the content of the "system_card.txt" file
# with open("system_card.txt", "r") as file:
#     system = file.read()

# conf = Utils.load_json("conf.json")
# page_titles = conf['titles']  #Utils.load_json("titles.json")
# custom_first_prompt = conf['custom_first_prompt']
# valid_keys = conf['valid_keys']

# app_bar_fragment = Utils.read_static_file("templates/appbar.html")

# is_llm_enabled = os.getenv("LLM_ENABLED") == "True"
# print(is_llm_enabled)

# try:
#     MONGO_URI =os.getenv("MONGO_URI")
#     client = MongoClient(MONGO_URI,tlsAllowInvalidCertificates=True)
#     db = client.get_database()  # Connect to the default database
#     collection = db["users"]  # Replace with your collection name
#     role_menu = db["role_menu"]
#     print("✅ Connected to MongoDB successfully!")
#     #init_db()

# except Exception as e:
#     print(f"❌ Failed to connect to MongoDB: {e}")



# # Sample route to test API
# @app.route("/")
# def home():
#     return render_template("index.html")
#     #collection.insert_one({ "name": "Gaurav Nagarkoti", "loginId": "g12","password":"1234","role":"student" , "key":"0" })
#     #return jsonify({"message": "Flask MongoDB API is running!"})

# @app.route("/initial_message", methods=["GET"])
# def get_initial_message():
    
#     try:
#         data_key = request.args.get('data-key')
#         if data_key:
#             filepath = f"initial_messages/{data_key}.json"  # Construct filepath dynamically
#             if os.path.exists(filepath):
#                 with open(filepath, "r") as file:
#                     initial_message = json.load(file)  # Parse the JSON content from the file
#                     print(initial_message)
#             else:
#                 return jsonify({"error": f"Initial message file '{data_key}.json' not found"}), 404
#         else:
#             # Default initial message
#             filepath = "initial_messages/initial_message.json" # Default file if no data_key
#             if os.path.exists(filepath):
#                 with open(filepath, "r") as file:
#                     initial_message = json.load(file)  # Parse the JSON content from the file
#             else:
#                 return jsonify({"error": f"Initial message file '{filepath}' not found"}), 404
#         print(initial_message)
#         return jsonify(initial_message)

#     except Exception as e:
#         return jsonify({"error": str(e)}), 500
   

# @app.route("/generate_claude", methods=["POST"])
# def generate_claude():
#     """Handles AI queries via Claude AI."""
#     try:
#         data = request.form
#         message = data.get("message")
#         history = data.get("history", "[]")
#         image_file = request.files.get("image")

#         if not message:
#             return jsonify({"error": "Message is required."}), 400

#         history = json.loads(history)  # Deserialize chat history
#         if is_llm_enabled:
#         # Handle image if present
#             file_path = None
#             if image_file:
#                 file_path = f"temp/{image_file.filename}"
#                 image_file.save(file_path)

#             ai_response = ClaudeAI().get_data("You are an AI assistant.", {
#                 "message": message,
#                 "history": history,
#                 "filePath": file_path
#             })
#         else:
#                 ai_response = {"role": "assistant", "content": [{"type":"text","text":"Thank You for calling LLM"}]}

#         return jsonify({"response": ai_response})

#     except Exception as e:
#         traceback.print_exc()
#         return jsonify({"error": str(e)}), 500

# # @app.route("/generate_claude", methods=["POST"])
# # def generate_claude():
# #     """Handles AI queries via Claude AI."""
# #     try:
# #         data = request.json

# #         if not data or "message" not in data:
# #             return jsonify({"error": "Invalid request data"}), 400

# #         system_message = "You are an AI assistant."

# #         # Handle Image Processing
# #         if "filePath" in data and data["filePath"]:
# #             image_message = ClaudeAI().get_message_image(data)  # Convert to Claude-compatible format
# #             ai_response = ClaudeAI().get_data(system_message, {"messages": [image_message]})
# #         else:
# #             ai_response = ClaudeAI().get_data(system_message, data)

# #         return jsonify({"response": ai_response})
# #     except Exception as e:
# #         return jsonify({"error": str(e)}), 500



# # Route to fetch data from MongoDB
# @app.route("/data")
# def get_data():
#     try:
#         data = list(collection.find({}, {"_id": 0}))  # Exclude ObjectId from response
#         return jsonify(data)
#     except Exception as e:
#         return jsonify({"error": str(e)})
    



# # def decode_token():
# #     """Helper function to decode JWT token from request headers."""
# #     print(request)
# #     token = request.json.headers.get("Authorization")
    
# #     if not token:
# #         return None, jsonify({"error": "Missing session token"}), 401

# #     try:
# #         # Remove 'Bearer ' prefix if present
# #         token = token.replace("Bearer ", "")

# #         # Decode JWT
# #         decoded_token = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
# #         return decoded_token, None
# #     except jwt.ExpiredSignatureError:
# #         return None, jsonify({"error": "Session token has expired"}), 401
# #     except jwt.InvalidTokenError:
# #         return None, jsonify({"error": "Invalid session token"}), 401

# @app.route('/api/select-model', methods=['POST'])
# def select_model():
#     try:
#         data = request.json
#         selected_model = data.get("model")

#         if not selected_model:
#             return jsonify({"error": "No model selected"}), 400

#         # Simulate AI model selection process (replace this with actual logic)
#         response_message = f"You selected {selected_model}. AI is ready."

#         return jsonify({"success": True, "selected_model": selected_model, "message": response_message})

#     except Exception as e:
#         return jsonify({"error": str(e)}), 500


# @app.route("/get-options", methods=["GET"])
# def get_options():
#     try:

#         # 🔹 Read headers from request
#         user_id = request.headers.get("User-Id")
#         user_role = request.headers.get("Role")
#         session_token = request.headers.get("Session-Token")  # Extract session token


#         if not user_id or not user_role or not session_token:
#             return jsonify({"error": "Missing authentication headers"}), 400

#         # 🔹 Verify the session token
#         try:
#             decoded_token = jwt.decode(session_token, SECRET_KEY, algorithms=["HS256"])
#             token_expiry = decoded_token.get("exp")

#             # ✅ Fix: Use `datetime.utcnow()` instead of `datetime.now(timezone.utc)`
#             if datetime.utcnow().timestamp() > token_expiry:
#                 return jsonify({"error": "Session token has expired"}), 401
#         except jwt.ExpiredSignatureError:
#             return jsonify({"error": "Session token expired"}), 401
#         except jwt.DecodeError:
#             return jsonify({"error": "Invalid session token"}), 401
#         except Exception as e:
#             return jsonify({"error": f"Token validation error: {str(e)}"}), 401

#         # 🔹 Query MongoDB for options matching the role
#         options_data = role_menu.find_one({"role": user_role}, {"_id": 0})
        
#         if not options_data:
#             return jsonify({"error": "No options found for this role"}), 404

#         return jsonify(options_data)

#     except Exception as e:
#         print(f"❌ Error fetching options: {e}")
#         return jsonify({"error": "Internal Server Error", "details": str(e)}), 500



# @app.route('/sendMessage', methods=['POST'])
# def send_message():
#     try:
#         data = request.get_json()  # Get JSON data from the request
#         user_message = data.get('text')  # Extract the 'text' field

#         if not user_message:
#             return jsonify({'error': 'Message text is required'}), 400  # Bad Request

#         bot_reply = {
#             'text': user_message + "  by bot",
#             'sender': 'bot'
#         }

#         return jsonify(bot_reply)  # Return the bot's reply as JSON

#     except Exception as e:
#         print(f"An error occurred: {e}")  # Log the error for debugging
#         return jsonify({'error': 'An error occurred'}), 500  # Internal Server Error


# # @app.route("/initial_message", methods=["GET"])
# # def get_initial_message():
# #     data_key = request.args.get('data-key')
    
# #     try:
# #         if data_key:
# #             filepath = f"initial_messages/{data_key}.json"  # Construct filepath dynamically
# #             if os.path.exists(filepath):
# #                 with open(filepath, "r") as file:
# #                     initial_message = {"content": file.read()}
# #                     print(initial_message)
# #             else:
# #                 return jsonify({"error": f"Initial message file '{data_key}.txt' not found"}), 404
# #         else:
# #             # Default initial message
# #             filepath = "initial_message.txt" # Default file if no data_key
# #             if os.path.exists(filepath):
# #                 with open(filepath, "r") as file:
# #                     initial_message = {"content": file.read()}
# #             else:
# #                 return jsonify({"error": f"Initial message file '{filepath}' not found"}), 404

# #         return jsonify(initial_message)

# #     except Exception as e:
# #         return jsonify({"error": str(e)}), 500

# import os
# import json
# from flask import Flask, request, jsonify


# @app.route("/role")
# def role_data():
#     try:
#         data = list(role_menu.find({}, {"_id": 0}))  # Exclude ObjectId from response
#         return jsonify(data)
#     except Exception as e:
#         return jsonify({"error": str(e)})


# @app.route("/login", methods=["POST"])
# def login():
    
#     try:
        
#         data = request.json
#         login_id = data.get("loginId")
#         password = data.get("password")
        
#         if not login_id or not password:
#             return jsonify({"error": "Login ID and password are required"}), 400

#         user = collection.find_one({"loginId": login_id})
        
#         if not user:
#             return jsonify({"error": "Invalid login ID"}), 401

#         if password == user["password"]:
#             # Generate a session token (JWT or Random String)
#             session_token = jwt.encode(
#                 {"loginId": login_id, "exp": datetime.utcnow() + timedelta(days=1)},
#                 SECRET_KEY,
#                 algorithm="HS256",
#             )
            
#             # Store the session token in the database (optional)
#             #collection.update_one({"loginId": login_id}, {"$set": {"sessionToken": session_token}})

#             # Return the token and user data
#             return jsonify({
#                 "message": "Login successful",
#                 "userId": str(user["_id"]),
#                 "role": user["role"],
#                 "sessionToken": session_token
#             }), 200
#         else:
#             return jsonify({"error": "Invalid password"}), 401
#     except Exception as e:
#         return jsonify({"error": "Internal Server Error", "details": str(e)}), 500


# @app.route('/logout', methods=['POST'])
# def logout():
#   return jsonify({"message": "Logged out successfully"}), 200

# @app.route("/learn-icon.png")
# def fav_icon():
#     s = get_local_file("learn-icon.png")
#     return s

# def get_local_file(filepath):
#     if not (os.path.exists(filepath) and os.path.isfile(filepath)):
#         filepath = "templates/empty.html"
#         return make_response(render_template('not_found.html'), 404)
#     with open(filepath, 'rb') as file:
#         s = file.read()
#     if filepath.lower().endswith(".css"):
#         return Response(s, mimetype='text/css')
#     if filepath.lower().endswith(".svg"):
#         return Response(s, mimetype='image/svg+xml')
#     if filepath.lower().endswith(".jpeg"):
#         return Response(s, mimetype='image/jpeg')
#     if filepath.lower().endswith(".bmp"):
#         return Response(s, mimetype='image/bmp')
#     return s

# @app.route("/assets/<filepath>")
# def app_assets(filepath):
    
#     filepath = "assets/" + filepath
#     s = get_local_file(filepath)
#     #print(filepath)
#     return s

# @app.route("/<folderpath>/<filepath>")
# def app_static_files(folderpath, filepath):
    
#     filepath = folderpath + "/" + filepath
#     s = get_local_file(filepath)
#     #print(filepath)
#     return s


# @app.route("/assets/images/<filepath>")
# def app_assets_images(filepath):
    
#     filepath = "assets/images/" + filepath
#     s = get_local_file(filepath)
#     #print(filepath)
#     return s

# @app.route("/edu/<role>/<objective>")
# def edu(role, objective):
#     #print(role, objective)
#     system_key = role + "-" + objective
#     template_name = 'templates/template.html'
#     if system_key not in valid_keys:
#         template_name = 'templates/invalidkey.html'
    
#     if os.path.exists("templates/"+system_key + ".html"):
#         template_name = "templates/"+system_key + ".html"

#     s = ""
    
#     with open(template_name, 'r') as file:
#         s = file.read()
#     s = s.replace("{APP_BAR}", app_bar_fragment)
#     s = s.replace("{ROLE}",role)
#     s = s.replace("{OBJECTIVE}",objective)
#     s = s.replace("{AI_MODEL}",conf['ai_model'])
#     if( system_key in page_titles):
#         s = s.replace("{PAGE_TITLE}", str(page_titles[system_key]).title())
#     custom_msg = ""
#     if system_key in custom_first_prompt:
#         custom_msg = custom_first_prompt[system_key]

#     s = s.replace("{CUSTOM_MESSAGE}",custom_msg)
#     return s #render_template("template.html")


# # Define the route for generating a response using the OpenAI API
# # The route accepts POST requests
# @app.route("/generate", methods=["POST"])
# def generate():
#     # Get the data from the incoming request in JSON format
#     data = request.get_json()
#     data["temperature"] = conf['temperature']
#     #print(data)
#     fname = ""
#     system_key = data['role'] + "-" + data['objective']
#     if system_key in system_cards:
#         system_val = system_cards[system_key]
#         fname = "already initialized"
#     else:
#         fname = "system-prompts/" + system_key + ".txt"
#         if os.path.exists(fname):
#             print("Reading Prompt", fname)
#             with open( fname , "r") as file:
#                 system_val = file.read()
#             #system_cards[system_key] = system_val
#         else:
#             fname = "system-prompts/" + data['role'] + ".txt"
#             if os.path.exists(fname):
#                 with open( fname , "r") as file:
#                     system_val = file.read()
#                 system_cards[system_key] = system_val
#             else:
#                 system_val = system #default value
#     if not is_llm_enabled:
#         print("test message")
#         Utils.save_json("history.json", data["history"])
#         ai_message = system_key +  " - " +  data['ai_model'] + "["+ fname +"]" # chats.get_data(system_val, data)
#         #print(system_val)
#         ai_message += "\n" + system_val
#         ai_message = jsonify(ai_message)
#         #print(ai_message)
#     else:
# #        if "append_to_system" in data:
# #            system_val = data['message'] + "\n" + system_val
# #            data['message'] = ''
#         chats = ClaudeAI2() 
#         ai_message = chats.get_data(system_val, data)
#     return ai_message


# @app.route('/upload', methods=['POST'])
# def upload_file():
#     if request.method == 'POST':
#         #print(request.files)
#         #key_name = "myFile"
#         for uploaded_file_key in request.files:
#             print(uploaded_file_key)
#             #return (upload_file)
#             uploaded_file = request.files[uploaded_file_key]
#             if uploaded_file:
#                 filename = secure_filename(uploaded_file.filename)
#                 filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
#                 print(filepath)
#                 uploaded_file.save(filepath)
#                 return f"{filepath}"
#     return render_template('index.html')



# # Run the Flask app
# if __name__ == "__main__":
#     app.run(debug=True)  # Prevents reloader issues