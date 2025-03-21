import streamlit as st
import cv2
import numpy as np
from pyzbar.pyzbar import decode
from PIL import Image
from pymongo import MongoClient
from datetime import datetime
from werkzeug.security import check_password_hash
from dotenv import load_dotenv
import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import timedelta
from collections import defaultdict
import pytz
IST = pytz.timezone("Asia/Kolkata")

# Load environment variables
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://userk1:9HxA5EuxjWAny7sO@cluster0.p1ywiyx.mongodb.net/lab_attendance?retryWrites=true&w=majority")

# MongoDB connection
client = MongoClient(MONGO_URI)
db = client["lab_attendance"]
attendance_collection = db["attendance"]
users_collection = db["users"]

# Function to scan QR code using camera
def scan_qr_code():
    st.title("Scan QR Code for Attendance")

    # Capture image from user's camera
    uploaded_image = st.camera_input("Scan QR Code")

    if uploaded_image:
        # Convert image to OpenCV format
        image = Image.open(uploaded_image)
        image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

        # Decode QR Code
        qr_codes = decode(image)
        if qr_codes:
            qr_data = qr_codes[0].data.decode("utf-8")
            st.success(f"Scanned QR Code: {qr_data}")
            return qr_data
        else:
            st.error("No valid QR Code detected. Please try again.")
    
    return None  # No QR code detected

# Function to handle check-in and check-out
def update_check_in_check_out(action, student_id):
    if student_id:
        if action == "Check-In-IITM-Project-PTC-LAB":
            existing = attendance_collection.find_one({"student_id": student_id, "check_out": None})
            if existing:
                st.warning(f"{student_id}, you have already checked in! Please check out first.")
            else:
                attendance_collection.insert_one({
                    "student_id": student_id,
                    "check_in": datetime.now(IST)
,
                    "check_out": None
                })
                st.success(f"{student_id}, checked in successfully!")

        elif action == "Check-Out-IITM-Project-PTC-LAB":
            existing = attendance_collection.find_one({"student_id": student_id, "check_out": None})
            if not existing:
                st.warning(f"{student_id}, you need to check in first before checking out!")
            else:
                attendance_collection.update_one(
                    {"student_id": student_id, "check_out": None},
                    {"$set": {"check_out": datetime.now(IST)
}}
                )
                st.success(f"{student_id}, checked out successfully!")

# Student Page (QR Scanner)
def student_page():
    qr_data = scan_qr_code()
    if qr_data:
        if "Check-In-IITM-Project-PTC-LAB" in qr_data:
            update_check_in_check_out("Check-In-IITM-Project-PTC-LAB", st.session_state["username"])
        elif "Check-Out-IITM-Project-PTC-LAB" in qr_data:
            update_check_in_check_out("Check-Out-IITM-Project-PTC-LAB", st.session_state["username"])

# Admin Dashboard
def show_admin_dashboard():
    st.title("Admin Dashboard")

    # Dashboard Tabs
    tabs = st.sidebar.radio("Dashboard", ("Overview", "Current Lab Status"))

    if tabs == "Overview":
        show_overview()
    elif tabs == "Current Lab Status":
        show_current_lab_status()


def show_overview():
    st.header("Weekly Attendance Comparison")

    # Get today's date and the past week's dates
    today = datetime.today().date()
    past_week_dates = [(today - timedelta(days=i)) for i in range(7)]
    
    # Dictionaries to store the data
    student_check_in_data = defaultdict(list)  # To store check-in times per student
    student_check_out_data = defaultdict(list)  # To store check-out times per student
    daily_check_in_counts = defaultdict(int)
    daily_check_out_counts = defaultdict(int)

    # Loop through past week to collect data for each day
    for day in past_week_dates:
        start_of_day = datetime.combine(day, datetime.min.time())
        end_of_day = datetime.combine(day, datetime.max.time())

        # Fetch check-in and check-out data for the day
        daily_check_in_data = list(attendance_collection.find({"check_in": {"$gte": start_of_day, "$lte": end_of_day}}))
        daily_check_out_data = list(attendance_collection.find({"check_out": {"$gte": start_of_day, "$lte": end_of_day}}))

        # Count daily check-ins and check-outs
        daily_check_in_counts[day] = len(daily_check_in_data)
        daily_check_out_counts[day] = len(daily_check_out_data)

        # Store data for student check-ins and check-outs for the week
        for entry in daily_check_in_data:
            student_check_in_data[entry["student_id"]].append(pd.to_datetime(entry["check_in"]))
        for entry in daily_check_out_data:
            student_check_out_data[entry["student_id"]].append(pd.to_datetime(entry["check_out"]))

    # Calculate the average check-in time, check-out time, and total time spent for each student
    student_avg_check_in = {}
    student_avg_check_out = {}
    student_total_time_spent = {}

    for student_id, check_in_times in student_check_in_data.items():
        check_out_times = student_check_out_data.get(student_id, [])

        # Calculate average check-in and check-out time
        if check_in_times and check_out_times:
            avg_check_in = pd.to_datetime(sum([t.timestamp() for t in check_in_times]) / len(check_in_times), unit='s')
            avg_check_out = pd.to_datetime(sum([t.timestamp() for t in check_out_times]) / len(check_out_times), unit='s')

            student_avg_check_in[student_id] = avg_check_in.strftime("%I:%M %p")  # 12-hour format
            student_avg_check_out[student_id] = avg_check_out.strftime("%I:%M %p")  # 12-hour format

            # Calculate total time spent
            total_time_spent = sum([(check_out - check_in).total_seconds() for check_in, check_out in zip(check_in_times, check_out_times)])
            student_total_time_spent[student_id] = total_time_spent / 3600  # Convert seconds to hours

    # Display the data for each student
    st.subheader("Student-wise Attendance Comparison")
    comparison_df = pd.DataFrame({
        "Student ID": student_avg_check_in.keys(),
        "Average Check-In Time": student_avg_check_in.values(),
        "Average Check-Out Time": student_avg_check_out.values(),
        "Total Time Spent (hrs)": student_total_time_spent.values()
    })
    st.table(comparison_df)

    # Visualization: Pie Chart for Student Time Spent in Lab
    st.subheader("Student Time in Lab (Pie Chart)")
    time_spent = list(student_total_time_spent.values())
    students = list(student_total_time_spent.keys())
    
    fig, ax = plt.subplots()
    ax.pie(time_spent, labels=students, autopct='%1.1f%%', startangle=90, colors=sns.color_palette("Set3", len(students)))
    ax.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
    ax.set_title("Time Spent in Lab by Student")
    st.pyplot(fig)

    # Daily Check-In/Check-Out Count Comparison (Bar Chart)
    st.subheader("Daily Check-In/Check-Out Counts")
    
    # Plot the daily check-ins and check-outs over the past week
    days = [day.strftime("%Y-%m-%d") for day in past_week_dates]
    check_in_counts = [daily_check_in_counts[day] for day in past_week_dates]
    check_out_counts = [daily_check_out_counts[day] for day in past_week_dates]

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(days, check_in_counts, width=0.4, label="Check-In", color="#4CAF50", align="center")
    ax.bar(days, check_out_counts, width=0.4, label="Check-Out", color="#FF5722", align="edge")
    ax.set_xlabel("Date")
    ax.set_ylabel("Attendance Count")
    ax.set_title("Daily Check-In/Check-Out Count")
    ax.legend()
    st.pyplot(fig)

    # Optional: Average time spent in lab (for each student)
    st.subheader("Average Time Spent in Lab (per student)")
    avg_time_spent = {student_id: total_time_spent for student_id, total_time_spent in student_total_time_spent.items()}
    avg_time_df = pd.DataFrame(list(avg_time_spent.items()), columns=["Student ID", "Average Time Spent (hrs)"])
    st.table(avg_time_df)


def show_current_lab_status():
    st.header("Students Currently in Lab")

    # Fetch data for students who have checked in but not checked out
    in_lab = attendance_collection.find({"check_out": None})
    students_in_lab = list(in_lab)

    if students_in_lab:
        students_in_lab_df = pd.DataFrame(students_in_lab)
        
        # Convert check_in to datetime
        students_in_lab_df["check_in"] = pd.to_datetime(students_in_lab_df["check_in"])
        
        # Create a new column for the formatted time with AM/PM
        students_in_lab_df["check_in_am_pm"] = students_in_lab_df["check_in"].dt.strftime("%I:%M %p")  # %I is 12-hour format with AM/PM
        
        # Display the table with student_id and check_in in AM/PM format
        st.table(students_in_lab_df[["student_id", "check_in_am_pm"]])
    else:
        st.write("No students are currently in the lab.")



# Login Page (MongoDB Authentication)
def login_page():
    st.title("Login to Lab Attendance System")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        user = users_collection.find_one({"username": username})
        
        if user and check_password_hash(user["password"], password):
            st.session_state["logged_in"] = True
            st.session_state["username"] = username
            st.session_state["role"] = user["role"]
            st.success(f"Welcome {username}!")
            st.rerun()
        else:
            st.error("Invalid username or password")

# Logout Function
def logout():
    if st.button("Logout"):
        st.session_state.clear()
        st.rerun()

# Main function
def main():
    if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
        login_page()
        return

    if st.session_state["role"] == "admin":
        show_admin_dashboard()
    else:
        student_page()

    logout()

if __name__ == "__main__":
    main()
