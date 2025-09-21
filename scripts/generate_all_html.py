#!/usr/bin/env python3
"""
Combined HTML Generator for Azure Resources Dashboard
Generates both Resource Providers and VM SKUs HTML files with navigation
Uploads generated files to Azure Storage static website
"""

import os
import subprocess
import shutil
import json
from datetime import datetime

# Get the directory of this script and set up relative paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)  # resourcepageapp directory
TEMPLATES_DIR = os.path.join(PROJECT_ROOT, "templates")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")

def load_config():
    """Load configuration from deploy.json and secrets.json"""
    config = {}
    
    # Load deployment config
    deploy_config_path = os.path.join(PROJECT_ROOT, "deploy.json")
    if os.path.exists(deploy_config_path):
        with open(deploy_config_path, 'r') as f:
            deploy_data = json.load(f)
            config.update(deploy_data.get('parameters', {}))
    
    # Load secrets config
    secrets_config_path = os.path.join(PROJECT_ROOT, "secrets.json")
    if os.path.exists(secrets_config_path):
        with open(secrets_config_path, 'r') as f:
            secrets_data = json.load(f)
            config.update(secrets_data.get('parameters', {}))
    
    return config

def upload_to_storage(config):
    """Upload generated HTML files to Azure Storage static website"""
    
    storage_account = config.get('storageAccountName', {}).get('value')
    resource_group = config.get('RGName', {}).get('value')
    
    if not storage_account or not resource_group:
        print("⚠️  Storage account or resource group not found in config")
        return False
    
    # Check Azure CLI login status
    try:
        result = subprocess.run(["az", "account", "show"], capture_output=True, text=True, check=True)
        print("✅ Azure CLI authenticated")
    except subprocess.CalledProcessError:
        print("❌ Azure CLI not authenticated. Please run: az login")
        return False
    
    files_to_upload = [
        "azure_resource_providers.html", 
        "azure_vm_skus.html"
    ]
    
    print(f"🔄 Uploading files to storage account: {storage_account}")
    
    success_count = 0
    for filename in files_to_upload:
        filepath = os.path.join(OUTPUT_DIR, filename)
        
        if os.path.exists(filepath):
            try:
                # Get storage account key
                key_result = subprocess.run([
                    "az", "storage", "account", "keys", "list",
                    "--resource-group", resource_group,
                    "--account-name", storage_account,
                    "--query", "[0].value",
                    "-o", "tsv"
                ], capture_output=True, text=True, check=True)
                
                account_key = key_result.stdout.strip()
                
                result = subprocess.run([
                    "az", "storage", "blob", "upload",
                    "--account-name", storage_account,
                    "--container-name", "$web",
                    "--name", filename,
                    "--file", filepath,
                    "--overwrite",
                    "--account-key", account_key
                ], capture_output=True, text=True, check=True)
                
                print(f"✅ Uploaded {filename}")
                success_count += 1
                
            except subprocess.CalledProcessError as e:
                print(f"❌ Failed to upload {filename}: {e.stderr}")
        else:
            print(f"⚠️  File not found: {filename}")
    
    print(f"📊 Upload summary: {success_count}/{len(files_to_upload)} files uploaded")
    return success_count > 0

def copy_css_files():
    """Copy unified CSS file to the output directory"""
    
    # Updated to use relative paths
    css_files = [
        "azure_unified_styles.css"
    ]
    
    for css_file in css_files:
        source_path = os.path.join(TEMPLATES_DIR, css_file)
        dest_path = os.path.join(OUTPUT_DIR, css_file)
        
        if os.path.exists(source_path):
            shutil.copy2(source_path, dest_path)
            print(f"✅ {css_file} copied successfully!")
        else:
            print(f"⚠️  {css_file} not found, skipping...")

def copy_navigation_assets():
    """Copy navigation menu HTML and static pages to the output directory"""
    
    # Copy navigation menu
    nav_files = ["nav_menu.html"]
    
    for nav_file in nav_files:
        source_path = os.path.join(TEMPLATES_DIR, nav_file)
        dest_path = os.path.join(OUTPUT_DIR, nav_file)
        
        if os.path.exists(source_path):
            shutil.copy2(source_path, dest_path)
            print(f"✅ {nav_file} copied successfully!")
        else:
            print(f"⚠️  {nav_file} not found in templates directory...")
    
    # Copy static pages
    static_pages_dir = os.path.join(PROJECT_ROOT, "staticpages")
    static_files = ["index.html", "404.html", "azure_unified_styles.css"]
    
    for static_file in static_files:
        source_path = os.path.join(static_pages_dir, static_file)
        dest_path = os.path.join(OUTPUT_DIR, static_file)
        
        if os.path.exists(source_path):
            shutil.copy2(source_path, dest_path)
            print(f"✅ {static_file} copied from staticpages!")
        else:
            print(f"⚠️  {static_file} not found in staticpages directory...")

def run_data_collection():
    """Run the Azure resource data collection script"""
    
    script_path = os.path.join(SCRIPT_DIR, "listresourceproviders.py")
    
    print("📊 Running Azure resource data collection...")
    try:
        result = subprocess.run(
            ["python3", script_path],
            capture_output=True,
            text=True,
            check=True,
            cwd=SCRIPT_DIR  # Set working directory to scripts directory
        )
        print("✅ Data collection completed successfully!")
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Data collection failed!")
        print(f"Error: {e.stderr}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error during data collection: {e}")
        return False

def run_html_generation():
    """Run both HTML generation scripts"""
    
    scripts = [
        (os.path.join(SCRIPT_DIR, "createhtml_resources.py"), "Resource Providers"),
        (os.path.join(SCRIPT_DIR, "createhtml_vms.py"), "VM SKUs")
    ]
    
    success_count = 0
    
    for script_path, description in scripts:
        print(f"🌐 Generating {description} HTML...")
        try:
            result = subprocess.run(
                ["python3", script_path],
                capture_output=True,
                text=True,
                check=True,
                cwd=SCRIPT_DIR  # Set working directory to scripts directory
            )
            print(f"✅ {description} HTML generated successfully!")
            print(result.stdout)
            success_count += 1
        except subprocess.CalledProcessError as e:
            print(f"❌ {description} HTML generation failed!")
            print(f"Error: {e.stderr}")
        except Exception as e:
            print(f"❌ Unexpected error generating {description} HTML: {e}")
    
    return success_count == len(scripts)

def main():
    """Main function to orchestrate the entire process"""
    
    print("🚀 Starting Azure Resource Dashboard Generation")
    print("=" * 60)
    print(f"📁 Project Root: {PROJECT_ROOT}")
    print(f"🐍 Scripts Directory: {SCRIPT_DIR}")
    print(f"📄 Templates Directory: {TEMPLATES_DIR}")
    print(f"🌐 Output Directory: {OUTPUT_DIR}")
    print()
    
    # Load configuration
    config = load_config()
    
    # Ensure output directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Copy CSS files and navigation assets
    print("🎨 Copying CSS files and navigation assets...")
    copy_css_files()
    copy_navigation_assets()
    
    # Generate HTML files (assumes data already exists)
    if not run_html_generation():
        print("\n⚠️  Some HTML files failed to generate.")
    
    # Upload to Azure Storage
    print("\n🚀 Uploading to Azure Storage...")
    upload_success = upload_to_storage(config)
    
    # Print summary
    print("\n" + "=" * 60)
    print("📋 GENERATION SUMMARY")
    print("=" * 60)
    
    files_to_check = [
        ("azure_resource_providers.html", "Resource Providers Dashboard"),
        ("azure_vm_skus.html", "VM SKUs Dashboard"),
        ("azure_unified_styles.css", "Unified Styles"),
        ("nav_menu.html", "Navigation Menu")
    ]
    
    print("\n📁 Generated Files:")
    all_files_exist = True
    
    for filename, description in files_to_check:
        filepath = os.path.join(OUTPUT_DIR, filename)
        if os.path.exists(filepath):
            size = os.path.getsize(filepath)
            print(f"  ✅ {description}: {filename} ({size:,} bytes)")
        else:
            print(f"  ❌ {description}: {filename} (NOT FOUND)")
            all_files_exist = False
    
    # Print Azure Storage information
    if upload_success:
        storage_account = config.get('storageAccountName', {}).get('value', 'UNKNOWN')
        print(f"\n🌐 Azure Static Website:")
        print(f"  🔗 URL: https://{storage_account}.z1.web.core.windows.net/")
        print(f"  📊 Resource Providers: https://{storage_account}.z1.web.core.windows.net/azure_resource_providers.html")
        print(f"  💻 VM SKUs: https://{storage_account}.z1.web.core.windows.net/azure_vm_skus.html")
    
    # Print local access information
    print(f"\n🌐 Local Access:")
    print(f"  📊 Resource Providers: file://{os.path.join(OUTPUT_DIR, 'azure_resource_providers.html')}")
    print(f"  💻 VM SKUs: file://{os.path.join(OUTPUT_DIR, 'azure_vm_skus.html')}")
    
    # Print folder structure information
    print(f"\n📁 Project Structure:")
    print(f"  🐍 Scripts: {os.path.relpath(SCRIPT_DIR, PROJECT_ROOT)}/")
    print(f"  📄 Templates: {os.path.relpath(TEMPLATES_DIR, PROJECT_ROOT)}/")
    print(f"  📊 Data: data/")
    print(f"  🌐 Output: {os.path.relpath(OUTPUT_DIR, PROJECT_ROOT)}/")
    
    # Print styling information
    print(f"\n🎨 Styling:")
    print(f"  • Microsoft Learn inspired design")
    print(f"  • Unified CSS file for consistency")
    print(f"  • Responsive design for mobile/desktop")
    print(f"  • Interactive search and filtering")
    
    if all_files_exist and upload_success:
        print(f"\n🎉 All files generated and uploaded successfully!")
        print(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        return True
    else:
        if not all_files_exist:
            print(f"\n⚠️  Some files are missing. Check the logs above.")
        if not upload_success:
            print(f"\n⚠️  Upload to Azure Storage failed. Check the logs above.")
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\n✅ Azure Resource Dashboard generation completed successfully!")
    else:
        print("\n❌ Dashboard generation completed with errors!")