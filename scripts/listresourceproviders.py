#!/usr/bin/env python3

"""
Azure Resource Provider and VM SKU Information Collector

This script collects information about Azure resource providers and VM SKUs
available in a specific region and exports the data to JSON format.

Features:
- Lists all Azure resource providers
- Checks availability in a specified region
- Collects VM SKU information with capabilities and zone support
- Exports data to JSON for use in HTML generation
- Smart deduplication for VM SKUs

Requirements:
- Azure CLI authentication
- Python 3.6+
- azure-mgmt-resource
- azure-mgmt-compute
"""

import json
import os
import sys
from datetime import datetime
from azure.identity import DefaultAzureCredential
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.compute import ComputeManagementClient

# Get the directory of this script and set up relative paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)  # resourcepageapp directory
DATA_DIR = os.path.join(PROJECT_ROOT, "data")

def normalize_region_name(region_name):
    """Normalize region name for comparison"""
    if not region_name:
        return ""
    return region_name.lower().replace(' ', '').replace('(', '').replace(')', '')

def get_azure_clients():
    """Initialize Azure clients using default credentials"""
    try:
        credential = DefaultAzureCredential()
        
        # Get subscription ID from environment or use a default one
        subscription_id = os.environ.get('AZURE_SUBSCRIPTION_ID')
        if not subscription_id:
            print("Warning: AZURE_SUBSCRIPTION_ID not set in environment variables")
            print("Using Azure CLI default subscription...")
            # You can also set a default subscription ID here if needed
            import subprocess
            try:
                result = subprocess.run(['az', 'account', 'show', '--query', 'id', '--output', 'tsv'], 
                                      capture_output=True, text=True, check=True)
                subscription_id = result.stdout.strip()
                print(f"Using subscription: {subscription_id}")
            except subprocess.CalledProcessError:
                raise Exception("Could not get default subscription. Please run 'az login' and 'az account set --subscription <your-subscription-id>'")
        
        resource_client = ResourceManagementClient(credential, subscription_id)
        compute_client = ComputeManagementClient(credential, subscription_id)
        
        return resource_client, compute_client, subscription_id
    except Exception as e:
        print(f"Error initializing Azure clients: {e}")
        print("Please ensure you are logged in with 'az login' and have the required permissions.")
        return None, None, None

def get_resource_providers_info(resource_client, region_filter=None):
    """Get information about all resource providers"""
    try:
        providers = list(resource_client.providers.list())
        provider_info = []
        
        normalized_region = normalize_region_name(region_filter)
        
        for provider in providers:
            # Check if provider is available in the specified region
            available_in_region = False
            resource_types_info = []
            
            if hasattr(provider, 'resource_types') and provider.resource_types:
                for resource_type in provider.resource_types:
                    rt_available_in_region = False
                    
                    if hasattr(resource_type, 'locations') and resource_type.locations:
                        # Check if the resource type is available in the specified region
                        if region_filter:
                            rt_available_in_region = any(
                                normalize_region_name(location) == normalized_region
                                for location in resource_type.locations
                            )
                        else:
                            rt_available_in_region = len(resource_type.locations) > 0
                    
                    if rt_available_in_region:
                        available_in_region = True
                    
                    resource_types_info.append({
                        'resource_type': resource_type.resource_type,
                        'locations': list(resource_type.locations) if resource_type.locations else [],
                        'available_in_region': rt_available_in_region
                    })
            
            provider_info.append({
                'namespace': provider.namespace,
                'registration_state': provider.registration_state,
                'resource_types': resource_types_info,
                'available_in_region': available_in_region
            })
        
        return provider_info
    except Exception as e:
        print(f"Error getting resource providers: {e}")
        return []

def get_vm_skus_info(compute_client, region_filter=None):
    """Get information about VM SKUs available in the specified region"""
    try:
        vm_skus_dict = {}  # Use dictionary to avoid duplicates
        normalized_region = normalize_region_name(region_filter)
        
        print(f"Collecting VM SKUs for region: {region_filter} (normalized: {normalized_region})")
        
        # Get Resource SKUs for detailed information (this is the primary source)
        try:
            resource_skus = list(compute_client.resource_skus.list())
            print(f"Found {len(resource_skus)} total resource SKUs")
            
            vm_count = 0
            available_count = 0
            
            # Debug: collect all unique locations to see what regions are available
            all_locations = set()
            
            for sku in resource_skus:
                if sku.resource_type == 'virtualMachines':
                    vm_count += 1
                    
                    # Collect all locations for debugging
                    if sku.locations:
                        for loc in sku.locations:
                            all_locations.add(loc)
                    
                    # Check if SKU is available in the specified region
                    available_in_region = False
                    zones = []
                    
                    # Primary check: use location_info for accurate region availability
                    if sku.location_info:
                        for location_info in sku.location_info:
                            if normalize_region_name(location_info.location) == normalized_region:
                                available_in_region = True
                                if location_info.zones:
                                    zones = sorted([int(z) for z in location_info.zones])
                                break
                    
                    # Fallback check: use locations if location_info doesn't have our region
                    if not available_in_region and sku.locations:
                        if region_filter:
                            available_in_region = any(
                                normalize_region_name(location) == normalized_region
                                for location in sku.locations
                            )
                        else:
                            available_in_region = len(sku.locations) > 0
                    
                    if available_in_region:
                        available_count += 1
                    
                    # Check for restrictions that might affect availability
                    is_restricted = False
                    if available_in_region and sku.restrictions:
                        for restriction in sku.restrictions:
                            if restriction.type in ['Location', 'Zone']:
                                # Check if the restriction affects our target region
                                if hasattr(restriction, 'restriction_info') and restriction.restriction_info:
                                    if hasattr(restriction.restriction_info, 'locations') and restriction.restriction_info.locations:
                                        restricted_locations = [normalize_region_name(loc) for loc in restriction.restriction_info.locations]
                                        if normalized_region in restricted_locations:
                                            is_restricted = True
                                            available_in_region = False
                                            break
                    
                    # Extract capabilities
                    capabilities = []
                    if sku.capabilities:
                        for capability in sku.capabilities:
                            capabilities.append(f"{capability.name}: {capability.value}")
                    
                    # Parse family and size from name
                    family = 'Unknown'
                    size = 'Unknown'
                    if sku.name:
                        # Common Azure VM naming pattern: Standard_[Family][Size]
                        if sku.name.startswith('Standard_'):
                            name_part = sku.name[9:]  # Remove 'Standard_' prefix
                            # Try to extract family (letters) and size (numbers/letters)
                            family_chars = ''
                            size_chars = ''
                            for i, char in enumerate(name_part):
                                if char.isalpha() and not size_chars:
                                    family_chars += char
                                else:
                                    size_chars += char
                            family = family_chars if family_chars else 'Unknown'
                            size = size_chars if size_chars else 'Unknown'
                    
                    # Get VM specs from virtual_machine_sizes if available
                    vcpus = 'N/A'
                    memory_gb = 'N/A'
                    
                    # Try to get basic VM size info for the region
                    if available_in_region and region_filter:
                        try:
                            vm_sizes = list(compute_client.virtual_machine_sizes.list(region_filter))
                            for vm_size in vm_sizes:
                                if vm_size.name == sku.name:
                                    vcpus = vm_size.number_of_cores
                                    memory_gb = vm_size.memory_in_mb / 1024 if vm_size.memory_in_mb else 0
                                    break
                        except Exception as e:
                            print(f"Warning: Could not get VM size details for {sku.name}: {e}")
                    
                    # Store or update the VM SKU in dictionary with smart merging
                    if sku.name in vm_skus_dict:
                        # If we already have this SKU, merge the availability info
                        existing = vm_skus_dict[sku.name]
                        
                        # Keep availability true if either instance is available
                        existing['available_in_region'] = existing['available_in_region'] or available_in_region
                        
                        # Merge locations (keep unique)
                        all_locations_for_sku = set(existing['locations'])
                        if sku.locations:
                            all_locations_for_sku.update(sku.locations)
                        existing['locations'] = sorted(list(all_locations_for_sku))
                        
                        # Merge zones (keep unique and sorted)
                        all_zones = set(existing['zones'])
                        all_zones.update(zones)
                        existing['zones'] = sorted(list(all_zones))
                        
                        # Keep restriction status as False if either instance is not restricted
                        existing['is_restricted'] = existing['is_restricted'] and is_restricted
                        
                        # Merge restrictions
                        all_restrictions = set(existing['restrictions'])
                        if sku.restrictions:
                            all_restrictions.update([restriction.type for restriction in sku.restrictions])
                        existing['restrictions'] = sorted(list(all_restrictions))
                        
                    else:
                        # First time seeing this SKU
                        vm_skus_dict[sku.name] = {
                            'name': sku.name,
                            'family': family,
                            'size': size,
                            'vcpus': vcpus,
                            'memory_gb': memory_gb,
                            'capabilities': capabilities,
                            'locations': list(sku.locations) if sku.locations else [],
                            'zones': zones,
                            'available_in_region': available_in_region,
                            'restrictions': [restriction.type for restriction in sku.restrictions] if sku.restrictions else [],
                            'is_restricted': is_restricted
                        }
            
            # Debug output: show all unique locations found
            print(f"All unique locations found: {sorted(all_locations)}")
            print(f"Looking for region: '{region_filter}' (normalized: '{normalized_region}')")
            print(f"Processed {vm_count} VM SKUs, {available_count} available in {region_filter}")
            
        except Exception as e:
            print(f"Error getting resource SKUs: {e}")
            return []
        
        # Convert dictionary back to list
        vm_skus_list = list(vm_skus_dict.values())
        
        # Calculate final availability count from deduplicated data
        final_available_count = sum(1 for sku in vm_skus_list if sku['available_in_region'])
        
        print(f"After deduplication: {len(vm_skus_list)} unique VM SKUs, {final_available_count} available in {region_filter}")
        
        return vm_skus_list
        
    except Exception as e:
        print(f"Error getting VM SKUs: {e}")
        return []

def save_to_json(data, filename):
    """Save data to JSON file with proper formatting"""
    try:
        # Ensure the data directory exists
        os.makedirs(DATA_DIR, exist_ok=True)
        
        filepath = os.path.join(DATA_DIR, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        print(f"✅ Data saved to: {filepath}")
        return True
    except Exception as e:
        print(f"❌ Error saving to JSON: {e}")
        return False

def main():
    """Main function"""
    region = "Belgium Central"  # Back to Belgium Central as requested
    
    print("🚀 Azure Resource Provider and VM SKU Information Collector")
    print("=" * 70)
    print(f"📍 Target Region: {region}")
    print(f"📁 Project Root: {PROJECT_ROOT}")
    print(f"📊 Data Directory: {DATA_DIR}")
    print()
    
    # Initialize Azure clients
    print("🔐 Initializing Azure clients...")
    resource_client, compute_client, subscription_id = get_azure_clients()
    
    if not resource_client or not compute_client:
        print("❌ Failed to initialize Azure clients. Exiting.")
        return False
    
    print(f"✅ Connected to subscription: {subscription_id}")
    print()
    
    # Get current timestamp
    current_time = datetime.now()
    timestamp_str = current_time.strftime("%Y%m%d_%H%M%S")
    datetime_str = current_time.strftime("%Y-%m-%d %H:%M:%S")
    
    # Collect resource providers information
    print("📊 Collecting resource providers information...")
    providers_info = get_resource_providers_info(resource_client, region)
    print(f"✅ Found {len(providers_info)} resource providers")
    
    # Collect VM SKUs information
    print("💻 Collecting VM SKUs information...")
    vm_skus_info = get_vm_skus_info(compute_client, region)
    print(f"✅ Found {len(vm_skus_info)} VM SKUs")
    
    # Calculate summary statistics
    available_providers = sum(1 for p in providers_info if p['available_in_region'])
    available_vm_skus = sum(1 for v in vm_skus_info if v['available_in_region'])
    
    print(f"📈 VM SKUs available in {region}: {available_vm_skus} out of {len(vm_skus_info)}")
    
    # Prepare resource providers data
    providers_data = {
        'generated': {
            'timestamp': timestamp_str,
            'date_time': datetime_str,
            'subscription_id': subscription_id
        },
        'region_checked': region,
        'summary': {
            'total_providers': len(providers_info),
            'available_in_region': available_providers,
            'not_available_in_region': len(providers_info) - available_providers
        },
        'resource_providers': providers_info
    }
    
    # Prepare VM SKUs data (already deduplicated)
    vm_skus_data = {
        'generated': {
            'timestamp': timestamp_str,
            'date_time': datetime_str,
            'subscription_id': subscription_id
        },
        'region_checked': region,
        'summary': {
            'total_vm_skus': len(vm_skus_info),
            'available_in_region': available_vm_skus,
            'not_available_in_region': len(vm_skus_info) - available_vm_skus
        },
        'vm_skus': vm_skus_info
    }
    
    # Save to JSON files
    print("\n💾 Saving data to JSON files...")
    
    providers_success = save_to_json(providers_data, 'azure_resource_providers.json')
    vm_skus_success = save_to_json(vm_skus_data, 'azure_vm_skus.json')
    
    # Print summary
    print("\n" + "=" * 70)
    print("📋 COLLECTION SUMMARY")
    print("=" * 70)
    print(f"🏷️  Region: {region}")
    print(f"📅 Generated: {datetime_str}")
    print(f"🔗 Subscription: {subscription_id}")
    print()
    print(f"📊 Resource Providers:")
    print(f"   • Total: {len(providers_info)}")
    print(f"   • Available in {region}: {available_providers}")
    print(f"   • Not available: {len(providers_info) - available_providers}")
    print()
    print(f"💻 VM SKUs:")
    print(f"   • Total: {len(vm_skus_info)}")
    print(f"   • Available in {region}: {available_vm_skus}")
    print(f"   • Not available: {len(vm_skus_info) - available_vm_skus}")
    
    # Show some examples of available VM SKUs
    if available_vm_skus > 0:
        print(f"\n📝 Sample available VM SKUs in {region}:")
        available_examples = [sku for sku in vm_skus_info if sku['available_in_region']][:5]
        for sku in available_examples:
            zones_info = f" (Zones: {', '.join(map(str, sku['zones']))}" if sku['zones'] else " (No zones"
            print(f"   • {sku['name']} - {sku['family']} family{zones_info})")
    
    if providers_success and vm_skus_success:
        print(f"\n🎉 Data collection completed successfully!")
        print(f"📁 Files saved to: {DATA_DIR}")
        return True
    else:
        print(f"\n❌ Some files failed to save!")
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\n✅ Azure resource collection completed!")
        print("🔄 You can now run the HTML generation scripts.")
    else:
        print("\n❌ Azure resource collection failed!")
