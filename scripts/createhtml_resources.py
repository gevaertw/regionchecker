import json
import os
from datetime import datetime

# Get the directory of this script and set up relative paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)  # resourcepageapp directory
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")
TEMPLATES_DIR = os.path.join(PROJECT_ROOT, "templates")

def create_html_table():
    """
    Create an HTML file with a table of Azure resource providers from the JSON file
    """
    
    # Updated file paths for relative structure
    json_file_path = os.path.join(DATA_DIR, "azure_resource_providers.json")
    html_file_path = os.path.join(OUTPUT_DIR, "azure_resource_providers.html")
    
    try:
        # Read the JSON file
        with open(json_file_path, 'r') as file:
            data = json.load(file)
        
        # Read the navigation menu
        nav_menu_path = os.path.join(TEMPLATES_DIR, "nav_menu.html")
        try:
            with open(nav_menu_path, 'r') as nav_file:
                nav_menu_html = nav_file.read()
        except FileNotFoundError:
            nav_menu_html = "<!-- Navigation menu file not found -->"
        
        # Extract information
        generated_info = data.get('generated', {})
        region_checked = data.get('region_checked', 'Unknown')
        summary = data.get('summary', {})
        resource_providers = data.get('resource_providers', [])
        
        # Get generation timestamp
        json_generated_time = generated_info.get('date_time', 'Unknown')
        json_timestamp = generated_info.get('timestamp', '')
        
        # Generate HTML content
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Azure Resource Providers - {region_checked}</title>
    <link rel="stylesheet" href="azure_unified_styles.css">
</head>
<body>
    {nav_menu_html}
    
    <div class="container">
        <h1>Azure Resource Providers</h1>
        <p style="color: #605e5c; font-size: 0.9rem; margin-bottom: 20px;">
            <strong>Region:</strong> {region_checked} | 
            <strong>Generated:</strong> {json_generated_time}
        </p>
        
        <div class="search-container">
            <input type="text" id="searchInput" placeholder="Search resource providers, resource types, or availability...">
        </div>
        
        <div class="filter-container">
            <div class="filter-buttons">
                <button id="filterAvailable" class="filter-btn">Available</button>
                <button id="filterPartialAvailable" class="filter-btn">Partial Available</button>
                <button id="filterNotAvailable" class="filter-btn">Not Available</button>
                <button id="clearFilter" class="filter-btn clear-btn">Clear Filter</button>
            </div>
        </div>
        
        <table id="resourceTable">
            <thead>
                <tr>
                    <th>Resource Provider</th>
                    <th>Resource Types</th>
                    <th>Available in {region_checked}</th>
                </tr>
            </thead>
            <tbody>
        """
        
        # Sort resource providers alphabetically by namespace
        sorted_providers = sorted(resource_providers, key=lambda x: x.get('namespace', ''))
        
        # Generate table rows
        for provider in sorted_providers:
            namespace = provider.get('namespace', 'Unknown')
            resource_types = provider.get('resource_types', [])
            
            # Calculate availability based on resource types
            total_resource_types = len(resource_types)
            available_resource_types = sum(1 for rt in resource_types if rt.get('available_in_region', False))
            
            # Determine availability status
            if total_resource_types == 0:
                availability_class = "not-available"
                availability_text = "Not Available"
            elif available_resource_types == total_resource_types:
                availability_class = "available"
                availability_text = "Available"
            elif available_resource_types > 0:
                availability_class = "partial-available"
                availability_text = "Partial Available"
            else:
                availability_class = "not-available"
                availability_text = "Not Available"
            
            # Format resource types as list with highlighting for region availability
            resource_types_html = '<ul class="resource-types-list">'
            for rt in resource_types:
                rt_name = rt.get('resource_type', 'Unknown')
                rt_available = rt.get('available_in_region', False)
                rt_class = 'available-in-region' if rt_available else ''
                resource_types_html += f'<li class="{rt_class}">{rt_name}</li>'
            resource_types_html += '</ul>'
            
            html_content += f"""
                <tr data-availability="{availability_class}">
                    <td><span class="provider-name">{namespace}</span></td>
                    <td>{resource_types_html}</td>
                    <td><span class="{availability_class}">{availability_text}</span></td>
                </tr>
            """
        
        # Close HTML structure
        html_content += """
            </tbody>
        </table>
        
        <div class="footer">
            Generated by Azure Resource Dashboard | Microsoft Learn Style
        </div>
    </div>

    <script>
        let currentFilter = 'all';
        
        // Search functionality
        document.getElementById('searchInput').addEventListener('input', function(e) {
            filterTable();
        });
        
        // Filter button functionality
        document.getElementById('filterAvailable').addEventListener('click', function() {
            currentFilter = 'available';
            updateFilterButtons();
            filterTable();
        });
        
        document.getElementById('filterPartialAvailable').addEventListener('click', function() {
            currentFilter = 'partial-available';
            updateFilterButtons();
            filterTable();
        });
        
        document.getElementById('filterNotAvailable').addEventListener('click', function() {
            currentFilter = 'not-available';
            updateFilterButtons();
            filterTable();
        });
        
        document.getElementById('clearFilter').addEventListener('click', function() {
            currentFilter = 'all';
            updateFilterButtons();
            filterTable();
        });
        
        function updateFilterButtons() {
            const buttons = document.querySelectorAll('.filter-btn:not(.clear-btn)');
            buttons.forEach(btn => btn.classList.remove('active'));
            
            if (currentFilter === 'available') {
                document.getElementById('filterAvailable').classList.add('active');
            } else if (currentFilter === 'partial-available') {
                document.getElementById('filterPartialAvailable').classList.add('active');
            } else if (currentFilter === 'not-available') {
                document.getElementById('filterNotAvailable').classList.add('active');
            }
        }
        
        function filterTable() {
            const searchTerm = document.getElementById('searchInput').value.toLowerCase();
            const table = document.getElementById('resourceTable');
            const rows = table.getElementsByTagName('tbody')[0].getElementsByTagName('tr');
            
            for (let i = 0; i < rows.length; i++) {
                const row = rows[i];
                const cells = row.getElementsByTagName('td');
                let shouldShow = false;
                
                // Check availability filter
                if (currentFilter !== 'all') {
                    const availability = row.getAttribute('data-availability');
                    if (availability !== currentFilter) {
                        row.style.display = 'none';
                        continue;
                    }
                }
                
                // Check search term
                if (searchTerm === '') {
                    shouldShow = true;
                } else {
                    for (let j = 0; j < cells.length; j++) {
                        const cellText = cells[j].textContent || cells[j].innerText;
                        if (cellText.toLowerCase().indexOf(searchTerm) > -1) {
                            shouldShow = true;
                            break;
                        }
                    }
                }
                
                row.style.display = shouldShow ? '' : 'none';
            }
        }
        
        // Add keyboard shortcuts
        document.addEventListener('keydown', function(e) {
            if (e.ctrlKey && e.key === 'f') {
                e.preventDefault();
                document.getElementById('searchInput').focus();
            }
        });
    </script>
</body>
</html>
        """
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(html_file_path), exist_ok=True)
        
        # Write HTML file
        with open(html_file_path, 'w') as file:
            file.write(html_content)
        
        print(f"HTML file generated successfully: {html_file_path}")
        
        # Print summary information
        print(f"\nSummary:")
        print(f"  - Total Resource Providers: {len(resource_providers)}")
        
        # Calculate availability categories
        available_count = 0
        partial_available_count = 0
        not_available_count = 0
        
        for provider in resource_providers:
            resource_types = provider.get('resource_types', [])
            total_resource_types = len(resource_types)
            available_resource_types = sum(1 for rt in resource_types if rt.get('available_in_region', False))
            
            if total_resource_types == 0:
                not_available_count += 1
            elif available_resource_types == total_resource_types:
                available_count += 1
            elif available_resource_types > 0:
                partial_available_count += 1
            else:
                not_available_count += 1
        
        print(f"  - Available in {region_checked}: {available_count}")
        print(f"  - Partial Available in {region_checked}: {partial_available_count}")
        print(f"  - Not Available in {region_checked}: {not_available_count}")
        print(f"  - Data generated: {json_generated_time}")
        
        return True
        
    except FileNotFoundError:
        print(f"Error: JSON file not found at {json_file_path}")
        print("Please run listresourceproviders.py first to generate the data.")
        return False
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON format in {json_file_path}")
        print(f"JSON Error: {e}")
        return False
    except Exception as e:
        print(f"Error generating HTML file: {e}")
        return False

if __name__ == "__main__":
    success = create_html_table()
    if success:
        print("\n✓ HTML file generation completed successfully!")
    else:
        print("\n✗ HTML file generation failed!")