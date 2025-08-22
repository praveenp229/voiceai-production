#!/usr/bin/env python3
"""
Quick deployment script for Twilio integration
Copy this and multitenant_saas_app.py to your Railway deployment
"""

import os
import requests

def check_twilio_deployment():
    """Check if Twilio endpoints are working"""
    base_url = "https://voiceai-backend-production-81d6.up.railway.app"
    
    # Test health endpoint
    try:
        response = requests.get(f"{base_url}/health")
        print(f"Health check: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Version: {data.get('version', 'unknown')}")
            
    except Exception as e:
        print(f"Health check failed: {e}")
    
    # Test Twilio webhook (should return 405 Method Not Allowed for GET)
    try:
        response = requests.get(f"{base_url}/api/v1/twilio/voice")
        print(f"Twilio webhook test: {response.status_code}")
        if response.status_code == 405:
            print("✅ Twilio webhook endpoint exists!")
        elif response.status_code == 404:
            print("❌ Twilio webhook NOT deployed yet")
            
    except Exception as e:
        print(f"Twilio test failed: {e}")

if __name__ == "__main__":
    print("Checking Twilio deployment status...")
    check_twilio_deployment()