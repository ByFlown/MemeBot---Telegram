#!/usr/bin/env python3
"""
📁 Storage Setup Script for Fly.io
Creates the proper directory structure with single volume mount
"""

import os
import sys

def setup_storage():
    """Setup storage directories with single volume mount"""
    print("📁 Setting up MemeBot storage...")
    
    # Define directories
    storage_dirs = ["storage/models", "storage/logs", "storage/data", "storage/ml_data"]
    link_dirs = ["models", "logs", "data"]
    
    # Also create ml_data directory (no symlink needed as it's referenced directly)
    
    try:
        # Create storage directories in the mounted volume
        for dir_path in storage_dirs:
            os.makedirs(dir_path, exist_ok=True)
            print(f"   ✅ Created: {dir_path}")
        
        # Create symbolic links from app root to storage
        for dir_name in link_dirs:
            storage_path = f"storage/{dir_name}"
            link_path = dir_name
            
            # Remove existing directory/link if it exists
            if os.path.exists(link_path) or os.path.islink(link_path):
                if os.path.islink(link_path):
                    os.unlink(link_path)
                elif os.path.isdir(link_path):
                    import shutil
                    shutil.rmtree(link_path)
                else:
                    os.remove(link_path)
                print(f"   🗑️  Removed existing: {link_path}")
            
            # Create symbolic link
            os.symlink(storage_path, link_path)
            print(f"   🔗 Linked: {link_path} -> {storage_path}")
        
        print("✅ Storage setup complete!")
        return True
        
    except Exception as e:
        print(f"❌ Storage setup failed: {e}")
        return False

def verify_storage():
    """Verify storage setup is working"""
    print("\n🔍 Verifying storage setup...")
    
    test_dirs = ["models", "logs", "data"]
    
    for dir_name in test_dirs:
        if os.path.exists(dir_name):
            if os.path.islink(dir_name):
                target = os.readlink(dir_name)
                print(f"   ✅ {dir_name} -> {target}")
            else:
                print(f"   ⚠️  {dir_name} exists but is not a symlink")
        else:
            print(f"   ❌ {dir_name} does not exist")
    
    return True

if __name__ == "__main__":
    print("🚀 MemeBot Storage Setup")
    print("=" * 30)
    
    success = setup_storage()
    verify_storage()
    
    if success:
        print("\n🎉 Setup successful!")
        sys.exit(0)
    else:
        print("\n💥 Setup failed!")
        sys.exit(1)