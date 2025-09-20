#!/usr/bin/env python3
"""
Combined HTML Generator for Azure Resources Dashboard
Generates both Resource Providers and VM SKUs HTML files with navigation
"""

import os
import subprocess
import shutil
from datetime import datetime

# Get the directory of this script and set up relative paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)  # resourcepageapp directory
TEMPLATES_DIR = os.path.join(PROJECT_ROOT, "templates")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")

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
    """Copy navigation menu HTML to the output directory"""
    
    nav_files = [
        "nav_menu.html"
    ]
    
    for nav_file in nav_files:
        source_path = os.path.join(TEMPLATES_DIR, nav_file)
        dest_path = os.path.join(OUTPUT_DIR, nav_file)
        
        if os.path.exists(source_path):
            shutil.copy2(source_path, dest_path)
            print(f"✅ {nav_file} copied successfully!")
        else:
            print(f"⚠️  {nav_file} not found in templates directory...")

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
    
    # Ensure output directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Copy CSS files and navigation assets
    print("🎨 Copying CSS files and navigation assets...")
    copy_css_files()
    copy_navigation_assets()
    
    # Run data collection
    if not run_data_collection():
        print("\n❌ Process stopped due to data collection failure.")
        return False
    
    # Generate HTML files
    if not run_html_generation():
        print("\n⚠️  Some HTML files failed to generate.")
    
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
    
    # Print access information
    print(f"\n🌐 Access your dashboards:")
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
    
    if all_files_exist:
        print(f"\n🎉 All files generated successfully!")
        print(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        return True
    else:
        print(f"\n⚠️  Some files are missing. Check the logs above.")
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\n✅ Azure Resource Dashboard generation completed successfully!")
    else:
        print("\n❌ Dashboard generation completed with errors!")