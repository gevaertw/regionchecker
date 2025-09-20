import json
import os
from datetime import datetime

# Get the directory of this script and set up relative paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)  # resourcepageapp directory
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")
TEMPLATES_DIR = os.path.join(PROJECT_ROOT, "templates")

def create_vm_html_table():
    """
    Create an HTML file with a table of Azure VM SKUs from the JSON file
    """
    
    # Updated file paths for relative structure
    json_file_path = os.path.join(DATA_DIR, "azure_vm_skus.json")
    html_file_path = os.path.join(OUTPUT_DIR, "azure_vm_skus.html")
    
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
        vm_skus = data.get('vm_skus', [])
        
        # Get generation timestamp
        json_generated_time = generated_info.get('date_time', 'Unknown')
        json_timestamp = generated_info.get('timestamp', '')
        
        # Deduplicate VM SKUs - prefer ones available in region, then by name
        unique_skus = {}
        for sku in vm_skus:
            name = sku.get('name', '')
            if name not in unique_skus:
                unique_skus[name] = sku
            else:
                # Prefer the one available in region
                current_available = unique_skus[name].get('available_in_region', False)
                new_available = sku.get('available_in_region', False)
                if new_available and not current_available:
                    unique_skus[name] = sku
        
        # Convert back to list and sort
        deduplicated_skus = list(unique_skus.values())
        sorted_skus = sorted(deduplicated_skus, key=lambda x: x.get('name', ''))
        
        # Generate HTML content
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Azure VM SKUs - {region_checked}</title>
    <link rel="stylesheet" href="azure_unified_styles.css">
</head>
<body>
    {nav_menu_html}
    
    <div class="container">
        <h1>Azure VM SKUs</h1>
        <p style="color: #605e5c; font-size: 0.9rem; margin-bottom: 20px;">
            <strong>Region:</strong> {region_checked} | 
            <strong>Generated:</strong> {json_generated_time} |
            <strong>Unique SKUs:</strong> {len(sorted_skus)}
        </p>
        
        <div class="search-container">
            <input type="text" id="searchInput" placeholder="Search VM SKUs, families, sizes, or capabilities...">
        </div>
        
        <div class="filter-container">
            <div class="filter-buttons">
                <button id="filterAvailable" class="filter-btn">Available</button>
                <button id="filterNotAvailable" class="filter-btn">Not Available</button>
                <button id="filterNotAllZones" class="filter-btn">Not All Zones</button>
                <button id="clearFilter" class="filter-btn clear-btn">Clear Filter</button>
            </div>
        </div>
        
        <table id="vmTable">
            <thead>
                <tr>
                    <th>VM SKU</th>
                    <th>Family</th>
                    <th>Size</th>
                    <th>vCPUs</th>
                    <th>Memory (GB)</th>
                    <th>Capabilities</th>
                    <th>Available in {region_checked}</th>
                </tr>
            </thead>
            <tbody>
        """
        
        # Generate table rows
        for sku in sorted_skus:
            name = sku.get('name', 'Unknown')
            family = sku.get('family', 'Unknown')
            size = sku.get('size', 'Unknown')
            vcpus = sku.get('vcpus', 'N/A')
            memory_gb = sku.get('memory_gb', 'N/A')
            capabilities = sku.get('capabilities', [])
            available_in_region = sku.get('available_in_region', False)
            zones = sku.get('zones', [])
            
            # Determine availability status based on zones and region availability
            if not available_in_region:
                availability_class = "not-available"
                availability_text = "Not Available"
            elif not zones:
                # Available in region but no zone support
                availability_class = "available"
                availability_text = "Available"
            elif len(zones) == 3:
                # Available in all zones (assuming 3 zones is the maximum)
                availability_class = "available"
                availability_text = "Available"
            else:
                # Available but not in all zones
                availability_class = "not-all-zones"
                availability_text = "Not All Zones"
            
            # Format capabilities as list
            capabilities_html = '<ul class="capabilities-list">'
            for capability in capabilities[:10]:  # Limit to first 10 to keep table readable
                capabilities_html += f'<li>{capability}</li>'
            if len(capabilities) > 10:
                capabilities_html += f'<li style="font-style: italic; color: #605e5c;">... and {len(capabilities) - 10} more</li>'
            capabilities_html += '</ul>'
            
            html_content += f"""
                <tr data-availability="{availability_class}">
                    <td><strong>{name}</strong></td>
                    <td>{family}</td>
                    <td>{size}</td>
                    <td>{vcpus}</td>
                    <td>{memory_gb}</td>
                    <td>{capabilities_html}</td>
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
        
        document.getElementById('filterNotAvailable').addEventListener('click', function() {
            currentFilter = 'not-available';
            updateFilterButtons();
            filterTable();
        });
        
        document.getElementById('filterNotAllZones').addEventListener('click', function() {
            currentFilter = 'not-all-zones';
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
            } else if (currentFilter === 'not-available') {
                document.getElementById('filterNotAvailable').classList.add('active');
            } else if (currentFilter === 'not-all-zones') {
                document.getElementById('filterNotAllZones').classList.add('active');
            }
        }
        
        function filterTable() {
            const searchTerm = document.getElementById('searchInput').value.toLowerCase();
            const table = document.getElementById('vmTable');
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
        
        // Add table sorting functionality
        function sortTable(columnIndex) {
            const table = document.getElementById('vmTable');
            const tbody = table.getElementsByTagName('tbody')[0];
            const rows = Array.from(tbody.getElementsByTagName('tr'));
            
            rows.sort((a, b) => {
                const aText = a.cells[columnIndex].textContent.trim();
                const bText = b.cells[columnIndex].textContent.trim();
                
                // Handle numeric columns (vCPUs, Memory)
                if (columnIndex === 3 || columnIndex === 4) {
                    const aNum = parseFloat(aText) || 0;
                    const bNum = parseFloat(bText) || 0;
                    return aNum - bNum;
                }
                
                return aText.localeCompare(bText);
            });
            
            // Re-append sorted rows
            rows.forEach(row => tbody.appendChild(row));
        }
        
        // Add click handlers to headers for sorting
        document.addEventListener('DOMContentLoaded', function() {
            const headers = document.querySelectorAll('#vmTable th');
            headers.forEach((header, index) => {
                header.style.cursor = 'pointer';
                header.title = 'Click to sort';
                header.addEventListener('click', () => sortTable(index));
            });
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
        
        print(f"VM SKUs HTML file generated successfully: {html_file_path}")
        
        # Print summary information
        print(f"\nSummary:")
        print(f"  - Total VM SKUs (after deduplication): {len(sorted_skus)}")
        available_count = sum(1 for sku in sorted_skus if sku.get('available_in_region', False))
        print(f"  - Available in {region_checked}: {available_count}")
        print(f"  - Not Available in {region_checked}: {len(sorted_skus) - available_count}")
        print(f"  - Data generated: {json_generated_time}")
        
        # Print family breakdown
        families = {}
        for sku in sorted_skus:
            family = sku.get('family', 'Unknown')
            families[family] = families.get(family, 0) + 1
        
        print(f"\nVM Families:")
        for family, count in sorted(families.items()):
            print(f"  - {family}: {count} SKUs")
        
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
        print(f"Error generating VM SKUs HTML file: {e}")
        return False

if __name__ == "__main__":
    success = create_vm_html_table()
    if success:
        print("\n✓ VM SKUs HTML file generation completed successfully!")
    else:
        print("\n✗ VM SKUs HTML file generation failed!")