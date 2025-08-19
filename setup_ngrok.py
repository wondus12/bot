#!/usr/bin/env python3
"""
Script to set up ngrok tunnel for webhook server
"""
from pyngrok import ngrok
import time
import threading
import subprocess
import os

def start_webhook_server():
    """Start the webhook server in a separate thread"""
    print("Starting webhook server...")
    # Start webhook server in background
    webhook_process = subprocess.Popen(['python', 'webhook_server.py'])
    return webhook_process

def setup_ngrok_tunnel():
    """Set up ngrok tunnel for webhook server"""
    # Set up ngrok tunnel on port 8080 (webhook server port)
    public_url = ngrok.connect(8080)
    print(f"Ngrok tunnel established: {public_url}")
    
    # Extract the URL without the protocol
    webhook_url = public_url.replace("http://", "https://")
    print(f"Webhook URL: {webhook_url}")
    
    # Update the .env file with the webhook URL
    update_env_file(webhook_url)
    
    return public_url

def update_env_file(webhook_url):
    """Update .env file with the webhook URL"""
    env_file = ".env"
    webhook_url_line = f"WEBHOOK_URL={webhook_url}/webhook"
    
    # Read current .env file
    with open(env_file, 'r') as f:
        lines = f.readlines()
    
    # Check if WEBHOOK_URL already exists
    webhook_exists = False
    for i, line in enumerate(lines):
        if line.startswith("WEBHOOK_URL="):
            lines[i] = webhook_url_line + "\n"
            webhook_exists = True
            break
    
    # If WEBHOOK_URL doesn't exist, add it
    if not webhook_exists:
        lines.append(webhook_url_line + "\n")
    
    # Write back to .env file
    with open(env_file, 'w') as f:
        f.writelines(lines)
    
    print(f"Updated .env file with webhook URL: {webhook_url_line}")

def main():
    """Main function to set up ngrok tunnel"""
    print("Setting up ngrok tunnel for webhook server...")
    
    try:
        # Start webhook server
        webhook_process = start_webhook_server()
        
        # Give the server a moment to start
        time.sleep(2)
        
        # Set up ngrok tunnel
        public_url = setup_ngrok_tunnel()
        
        print("Ngrok tunnel is now running. Press Ctrl+C to stop.")
        print("Webhook server is running on port 8080")
        print(f"Public URL: {public_url}")
        
        # Keep the script running
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nShutting down...")
            ngrok.kill()
            webhook_process.terminate()
            
    except Exception as e:
        print(f"Error setting up ngrok: {e}")
        ngrok.kill()

if __name__ == "__main__":
    main()