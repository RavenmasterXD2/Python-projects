import json
import os
import time

USERS_FILE = "data/users.json"
FILES_FILE = "data/files.json"

def run_installer():
    print("Welcome to PyOS Installer!")
    
    username = input("Enter username: ")
    password = input("Enter password: ")
    region = input("Enter region: ")
    language = input("Enter language: ")

   
    if not os.path.exists("data"):
        os.makedirs("data")
    
   
    users = [{"username": username, "password": password, "region": region, "language": language}]
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)
    
    
    filesystem = {"root": {}}
    with open(FILES_FILE, "w") as f:
        json.dump(filesystem, f, indent=4)

   
    steps = ["Installing core files", "Setting up environment", "Finalizing setup"]
    for step in steps:
        print(step + "...")
        time.sleep(1)  

    print("Installation complete! Rebooting...")
    time.sleep(1)
    import login
    login.run_login()
