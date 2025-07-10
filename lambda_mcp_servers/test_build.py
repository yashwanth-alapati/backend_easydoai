# easydo_backend/lambda_mcp_servers/test_build.py
"""
Test that Docker containers build successfully
"""
import subprocess
import os

def test_docker_builds():
    print("🧪 Testing Docker Builds")
    print("=" * 50)
    
    # Test Gmail container
    print("1. 📧 Testing Gmail container build...")
    try:
        result = subprocess.run([
            "docker", "build", "-t", "easydoai-gmail-mcp-test", 
            "gmail_lambda/"
        ], capture_output=True, text=True, cwd=".")
        
        if result.returncode == 0:
            print("   ✅ Gmail container builds successfully")
        else:
            print(f"   ❌ Gmail container build failed: {result.stderr}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test Calendar container
    print("\n2. 📅 Testing Calendar container build...")
    try:
        result = subprocess.run([
            "docker", "build", "-t", "easydoai-calendar-mcp-test", 
            "calendar_lambda/"
        ], capture_output=True, text=True, cwd=".")
        
        if result.returncode == 0:
            print("   ✅ Calendar container builds successfully")
        else:
            print(f"   ❌ Calendar container build failed: {result.stderr}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

if __name__ == "__main__":
    test_docker_builds()