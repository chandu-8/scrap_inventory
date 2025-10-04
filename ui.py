import dearpygui.dearpygui as dpg
import pandas as pd
import os
import shutil 
import math
import debugpy
import pydevd_pycharm

from config import PROFILE_NAMES, get_product_names, get_product_components
from database import add_profile, get_connection, get_all_profiles
from requirements_manager import RequirementsManager
from excel_processor import process_requirements

# Global state
requirements_manager = RequirementsManager()

def launch_ui():
    """Launch the Dear PyGui interface with resizable and scrollable UI"""
    dpg.create_context()
    
    # Create viewport with resizable window
    dpg.create_viewport(title="Inventory Management", width=800, height=600)
    
    # Create file dialog once during initialization
    with dpg.file_dialog(directory_selector=False, show=False, callback=file_selection_callback, 
                        tag="file_dialog", width=700, height=400):
        dpg.add_file_extension(".xlsx", color=(0, 255, 0, 255))
        dpg.add_file_extension(".xls", color=(0, 255, 0, 255))
        dpg.add_file_extension(".*", color=(255, 255, 255, 255))
    
    # Main window - simplified to avoid container stack issues
    with dpg.window(label="Inventory Manager", tag="main_window", 
                   width=800, height=600):   # Enable scrollbar when needed
        with dpg.tab_bar():
            
            # --- Tab 1: Upload Cutlist ---
            with dpg.tab(label="Upload Cutlist"):
                dpg.add_text("Upload Excel Cutlist File", color=[0, 255, 0])
                dpg.add_separator()
                
                # File upload area
                with dpg.group(horizontal=True):
                    dpg.add_button(label="Select Excel File", callback=file_dialog_callback)
                    dpg.add_text("Click to browse for Excel files", color=[100, 100, 100])
                
                # File info display
                dpg.add_text("No file selected", tag="file_info", color=[255, 255, 0])
                
                dpg.add_separator()
                
                # Requirements display - simplified
                dpg.add_text("Requirements:", color=[0, 255, 255])
                dpg.add_group(tag="requirements_group", horizontal=False)
                
                dpg.add_separator()
                
                # Process controls
                with dpg.group(horizontal=True):
                    dpg.add_button(label="Process Requirements", callback=process_requirements_callback, 
                                 enabled=False, tag="process_button")
                    dpg.add_button(label="Clear File", callback=clear_file_callback)
                
                dpg.add_text("", tag="processing_status", color=[0, 255, 0])
                
                # Results area - simplified
                dpg.add_separator()
                dpg.add_text("Processing Results:", color=[0, 255, 255])
                dpg.add_group(tag="results_group", horizontal=False)
            
            # --- Tab 2: Add Profile ---
            with dpg.tab(label="Add Profile"):
                dpg.add_text("Add New Profile to Inventory", color=[0, 255, 0])
                dpg.add_separator()
                
                # Profile input form
                dpg.add_combo(PROFILE_NAMES, label="Profile Name", tag="profile_name_dropdown")
                dpg.add_input_float(label="Length (mm)", tag="length_input", default_value=0.0)
                dpg.add_input_int(label="Quantity", tag="quantity_input", default_value=0)
                dpg.add_button(label="Add to Database", callback=submit_profile_callback)
            
            # --- Tab 3: View Database ---
            with dpg.tab(label="View Database"):
                dpg.add_text("Current Inventory", color=[0, 255, 0])
                dpg.add_separator()
                
                # Database controls
                with dpg.group(horizontal=True):
                    dpg.add_button(label="Refresh Table", callback=refresh_database_view)
                    dpg.add_text("Click to refresh inventory data", color=[100, 100, 100])
                
                dpg.add_separator()
                
                # Database view - simplified
                dpg.add_group(tag="db_view_group", horizontal=False)
            
            # --- Tab 4: Product Calculator ---
            with dpg.tab(label="Product Calculator"):
                dpg.add_text("Calculate profiles by product and component weights", color=[0, 255, 0])
                dpg.add_separator()
                dpg.add_combo(get_product_names(), label="Product", tag="product_selector",
                              callback=on_product_change)
                dpg.add_separator()
                dpg.add_text("Components:", color=[0, 255, 255])
                dpg.add_group(tag="product_components_group", horizontal=False)
                dpg.add_separator()
                dpg.add_button(label="Calculate Profiles Needed", tag="calculate_profiles_btn",
                               callback=calculate_profiles_for_product, enabled=False)
                dpg.add_separator()
                dpg.add_text("Results:", color=[0, 255, 255])
                dpg.add_group(tag="product_calc_results_group", horizontal=False)
    
    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.start_dearpygui()
    dpg.destroy_context()

def file_dialog_callback(sender, app_data):
    """Handle file dialog button click - just show the existing dialog"""
    dpg.show_item("file_dialog")

def file_selection_callback(sender, app_data):
    """Handle file selection from dialog"""
    if app_data['file_path_name']:
        handle_file_selection(app_data['file_path_name'])

def handle_file_selection(file_path):
    """Handle file selection and parse requirements"""
    global requirements_manager
    
    try:
        if not file_path.lower().endswith(('.xlsx', '.xls')):
            update_status("Error: Please select an Excel file (.xlsx or .xls)")
            return
        
        # Load requirements
        if requirements_manager.load_file(file_path):
            filename = os.path.basename(file_path)
            dpg.set_value("file_info", f"Selected: {filename}")
            dpg.configure_item("process_button", enabled=True)
            
            # Display requirements
            display_requirements()
            update_status(f"File loaded: {filename}")
        else:
            update_status("Error: Failed to load file")
    
    except Exception as e:
        update_status(f"Error handling file: {str(e)}")

def display_requirements():
    """Display parsed requirements in the UI"""
    global requirements_manager
    
    # Clear previous requirements safely
    if dpg.does_item_exist("requirements_group"):
        try:
            dpg.delete_item("requirements_group", children_only=True)
        except:
            pass  # Ignore errors if item doesn't exist
    
    requirements = requirements_manager.get_requirements()
    
    if not requirements:
        dpg.add_text("No requirements found", parent="requirements_group")
        return
    
    # Display requirements summary
    summary = requirements_manager.get_summary()
    dpg.add_text(f"Total Requirements: {summary['total_requirements']}", 
                parent="requirements_group", color=[255, 255, 0])
    
    # Display each requirement
    for i, req in enumerate(requirements):
        status = "Processed" if req['processed'] else "Pending"
        dpg.add_text(f"{i+1}. {req['requirement_type']}: {req['length']}mm x {req['quantity']}pcs - {status}", 
                    parent="requirements_group")


def process_requirements_callback(sender, app_data, user_data):
    """Process the loaded requirements"""
    print("Callback triggered!")
    global requirements_manager
    try:
        update_status("Processing requirements... Please wait")
        dpg.configure_item("process_button", enabled=False)
        
        # Clear previous results safely
        if dpg.does_item_exist("results_group"):
            try:
                dpg.delete_item("results_group", children_only=True)
            except:
                pass

        # pydevd_pycharm.settrace(suspend=True, trace_only_current_thread=True)
        # Get database connection and process
        with get_connection() as conn:
            summary = process_requirements(requirements_manager.get_unprocessed_requirements(), conn)
        
        # Update requirements display
        display_requirements()
        update_status("Requirements processed successfully!")
        dpg.configure_item("process_button", enabled=True)

        if summary:
            dpg.add_separator(parent="results_group")
            dpg.add_text(f"TOTAL new profiles allocated: {summary.get('total_new_profiles', 0)}",
                 parent="results_group", color=[0, 255, 0])

            per_prof = summary.get('per_profile_new') or {}
            if per_prof:
                dpg.add_text("Per-profile new allocations:", parent="results_group", color=[0, 255, 255])
                for name, cnt in per_prof.items():
                    dpg.add_text(f"  - {name}: {cnt}", parent="results_group")
        
    except Exception as e:
        update_status(f"Error processing requirements: {str(e)}")
        dpg.configure_item("process_button", enabled=True)


def clear_file_callback(sender, app_data, user_data):
    """Clear the selected file and requirements"""
    global requirements_manager
    
    requirements_manager.clear_requirements()
    dpg.set_value("file_info", "No file selected")
    dpg.configure_item("process_button", enabled=False)
    update_status("File and requirements cleared")
    
    # Clear displays safely
    if dpg.does_item_exist("requirements_group"):
        try:
            dpg.delete_item("requirements_group", children_only=True)
        except:
            pass
    
    if dpg.does_item_exist("results_group"):
        try:
            dpg.delete_item("results_group", children_only=True)
        except:
            pass


def update_status(message):
    """Update the status message"""
    dpg.set_value("processing_status", message)


def submit_profile_callback(sender, app_data, user_data):
    """Callback for adding a new profile"""
    try:
        name = dpg.get_value("profile_name_dropdown")
        length = float(dpg.get_value("length_input"))
        quantity = int(dpg.get_value("quantity_input"))
        
        with get_connection() as conn:
            success = add_profile(conn, name, length, quantity)
        
        if success:
            refresh_database_view()
            dpg.set_value("length_input", 0.0)
            dpg.set_value("quantity_input", 0)
            update_status("Profile added successfully!")
        else:
            update_status("Error: Invalid profile data")
    
    except Exception as e:
        update_status(f"Error adding profile: {str(e)}")


def refresh_database_view():
    """Load profiles from DB and display in a readable format"""
    try:
        with get_connection() as conn:
            df = pd.read_sql_query(
                "SELECT profile_id, name, length, quantity, bin FROM profiles ORDER BY profile_id, length",
                conn
            )
        
        # Clear previous content safely
        if dpg.does_item_exist("db_view_group"):
            try:
                dpg.delete_item("db_view_group", children_only=True)
            except:
                pass
        
        if df.empty:
            dpg.add_text("No profiles in database.", parent="db_view_group")
            return
        
        # Display as formatted text with better formatting
        headers = f"{'Profile ID':<12} {'Name':<40} {'Length (mm)':<12} {'Qty':<8} {'Bin':<15}"
        dpg.add_text(headers, parent="db_view_group", color=[255, 255, 0])
        dpg.add_text("-" * len(headers), parent="db_view_group")
        
        for _, row in df.iterrows():
            line = f"{row['profile_id']:<12} {row['name']:<40} {row['length']:<12.0f} {row['quantity']:<8} {row['bin']:<15}"
            dpg.add_text(line, parent="db_view_group")
    
    except Exception as e:
        dpg.add_text(f"Error loading database: {e}", parent="db_view_group", color=[255, 0, 0])


def on_product_change(sender, app_data, user_data):
    """Render component rows for the selected product"""
    product = dpg.get_value("product_selector")
    # Clear previous
    if dpg.does_item_exist("product_components_group"):
        try:
            dpg.delete_item("product_components_group", children_only=True)
        except:
            pass
    if dpg.does_item_exist("product_calc_results_group"):
        try:
            dpg.delete_item("product_calc_results_group", children_only=True)
        except:
            pass
    if not product:
        dpg.configure_item("calculate_profiles_btn", enabled=False)
        return

    components = get_product_components(product)
    if not components:
        dpg.add_text("No component data for this product.", parent="product_components_group")
        dpg.configure_item("calculate_profiles_btn", enabled=False)
        return

    # Build input rows: label (component), unit weight, input total weight
    for idx, comp in enumerate(components):
        row_tag = f"pc_row_{idx}"
        with dpg.group(parent="product_components_group", horizontal=True):
            dpg.add_text(f"{comp['component']}")
            dpg.add_text(f"(unit {comp['unit_weight']} kg/profile)", color=[150, 150, 150])
            dpg.add_input_float(label="Total weight (kg)", tag=f"pc_total_weight_{idx}",
                                width=150, min_value=0.0, min_clamped=True, default_value=0.0)
    dpg.configure_item("calculate_profiles_btn", enabled=True)


def calculate_profiles_for_product(sender, app_data, user_data):
    """Compute ceil(total_weight / unit_weight) for each component"""
    product = dpg.get_value("product_selector")
    if not product:
        return
    components = get_product_components(product)
    # Clear previous results
    if dpg.does_item_exist("product_calc_results_group"):
        try:
            dpg.delete_item("product_calc_results_group", children_only=True)
        except:
            pass
    
    total_profiles = 0
    dpg.add_text(f"Product: {product}", parent="product_calc_results_group", color=[255, 255, 0])

    for idx, comp in enumerate(components):
        unit_w = comp['unit_weight']
        try:
            total_w = float(dpg.get_value(f"pc_total_weight_{idx}") or 0.0)
        except:
            total_w = 0.0
        profiles_needed = 0
        if unit_w > 0:
            profiles_needed = int(math.ceil(total_w / unit_w))
        total_profiles += profiles_needed
        dpg.add_text(f"- {comp['component']}: total {total_w:.2f} kg / {unit_w:.3f} kg/profile"
                     f" => {profiles_needed} profiles",
                     parent="product_calc_results_group")

    dpg.add_separator(parent="product_calc_results_group")
    dpg.add_text(f"Total profiles across all components: {total_profiles}",
                 parent="product_calc_results_group", color=[0, 255, 0])
