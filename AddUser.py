import csv
from pymongo import MongoClient
from werkzeug.security import generate_password_hash

# MongoDB connection
client = MongoClient("mongodb+srv://userk1:9HxA5EuxjWAny7sO@cluster0.p1ywiyx.mongodb.net/lab_attendance?retryWrites=true&w=majority")
db = client["lab_attendance"]
users_collection = db["users"]

# Function to read CSV and insert data into MongoDB
def insert_users_from_csv(csv_file_path):
    # Open the CSV file and read it
    with open(csv_file_path, mode='r') as file:
        csv_reader = csv.DictReader(file)
        
        users_to_insert = []
        
        # Read each row in the CSV
        for row in csv_reader:
            username = row['username']
            password = row['password']
            role = row['role']
            
            # Hash the password before storing it
            hashed_password = generate_password_hash(password)
            
            # Prepare the user data to be inserted
            user_data = {
                "username": username,
                "password": hashed_password,
                "role": role
            }
            users_to_insert.append(user_data)
        
        # Insert the users into MongoDB
        if users_to_insert:
            users_collection.insert_many(users_to_insert)
            print(f"{len(users_to_insert)} users added successfully!")
        else:
            print("No users to insert.")

# Call the function with the path to your CSV file
insert_users_from_csv(r"C:\Users\Vasanth (Work)\Desktop\users.csv")
