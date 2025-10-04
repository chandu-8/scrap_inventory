import sqlite3
import dearpygui.dearpygui as dpg
from tkinter import ttk, messagebox
import pandas as pd
from typing import List, Tuple, Dict, Optional
import os

# --- Constants ---
CUTTING_ALLOWANCE = 10  # mm
NEW_PROFILE_LENGTH = 6000  # mm
MIN_SCRAP_LENGTH = 1000  # mm - minimum length to keep as scrap


def add_profile(conn, name: str, length: float, quantity: int):
    cursor = conn.cursor()

    if length <= 0 or quantity <= 0:
        messagebox.showwarning("Invalid Data", f"Invalid profile: {name}, {length}mm x {quantity}pcs")
        return

    bin_class = classify_bin(length)

    cursor.execute("""
            SELECT profile_id, quantity
            FROM profiles
            WHERE name = ? AND length = ?
        """, (name, length))

    existing = cursor.fetchone()

    if existing:
        # Merge: update quantity
        profile_id, old_qty = existing
        new_qty = old_qty + quantity
        cursor.execute("""
                UPDATE profiles
                SET quantity = ?
                WHERE profile_id = ?
            """, (new_qty, profile_id))

        # Update bin_summary
        cursor.execute("""
                UPDATE bin_summary
                SET total_quantity = total_quantity + ?
                WHERE bin = ?
            """, (quantity, bin_class))

    else:
        cursor.execute("""
            INSERT INTO profiles (name, length, quantity, bin)
            VALUES (?, ?, ?, ?)
        """, (name, length, quantity, bin_class))

        cursor.execute("""
            INSERT INTO bin_summary (bin, total_quantity)
            VALUES (?, ?)
            ON CONFLICT(bin) DO UPDATE SET total_quantity = total_quantity + excluded.total_quantity
        """, (bin_class, quantity))
    conn.commit()


def classify_bin(length: float) -> str:
    """Classify profiles into bins based on length"""
    if 1000 <= length < 1500:
        return "1000-1500"
    elif 1500 <= length < 3000:
        return "1500-3000"
    elif 3000 <= length <= 6000:
        return "3000-6000"
    else:
        return "out-of-range"


# --- Database Setup ---
def setup_database():
    conn = sqlite3.connect("inventory.db")
    cursor = conn.cursor()

    cursor.execute("""DROP TABLE IF EXISTS profiles""")
    cursor.execute("""DROP TABLE IF EXISTS bin_summary""")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS profiles (
        profile_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        length REAL NOT NULL CHECK (length > 0),
        quantity INTEGER NOT NULL CHECK (quantity >= 0),
        bin TEXT NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bin_summary (
        bin TEXT PRIMARY KEY,
        total_quantity INTEGER NOT NULL CHECK (total_quantity >= 0)
    )
    """)

    return conn

    # def add_profile(name: str, length: float, quantity: int):
    #     if length <= 0 or quantity <= 0:
    #         print(f"Warning: Invalid profile data - {name}: {length}mm x {quantity}pcs")
    #         return
    #
    #     bin_class = classify_bin(length)
    #     cursor.execute("""
    #         INSERT INTO profiles (name, length, quantity, bin)
    #         VALUES (?, ?, ?, ?)
    #     """, (name, length, quantity, bin_class))
    #
    #     cursor.execute("""
    #         INSERT INTO bin_summary (bin, total_quantity)
    #         VALUES (?, ?)
    #         ON CONFLICT(bin) DO UPDATE SET total_quantity = total_quantity + excluded.total_quantity
    #     """, (bin_class, quantity))
    #     conn.commit()

    # # Add sample profiles to database
    # # add_profile("P.C.E. PROFILE LAD F-75", 1300, 72)
    # add_profile("FRAME PROFILE FOR LAD F-75", 3000, 1)
    # add_profile("FRAME PROFILE FOR LAD F-75", 2500, 1)
    # # add_profile("FRAME PROFILE FOR LAD F-75", 4000, 1)



# PROFILE_MAP = {
#     "K11I001007": "P.C.E. PROFILE LAD F-75",
#     "K11I001032": "BOX TYPE SAND TRAP BLADE PROFILE",
#     "K11I001009": "FRAME PROFILE FOR LAD F-75",
#     "K11I001014": "PCE PROFILE LAD F-100",
#     "K11I001034": "BOX TYPE LOUVER BLADE PROFILE",
#     "K11I002007": "INNERVANE PROFILE LAD F-100",
#     "K11I001033": "BOX TYPE SAND TRAP FRAME PROFILE",
#     "K11I008007": "FRAME PROFILE XDG",
#     "K15I011002": "FRAME PROFILE FOR OBD - BLACK ANODISED",
#     "K11I007008": "LBG (AIR LINE) BLADE 0°",
#     "K11L001007": "MOVEMENT BAR PROFILE - BLACK ANODISED",
#     "K11I008008": "BLADE PROFILE XDG",
#     "K11L001001": "LBG 15 DEG BLADE PROFILE",
#     "K11I001035": "BOX TYPE LOUVER FRAME PROFILE",
#     "K11I001015": "VCD PROFILE LAD F-100",
#     "K15I011001": "BLADE PROFILE FOR OBD - BLACK ANODISED",
#     "K11I113007": "FLY SCREEN FRAME",
#     "K11I007009": "FRAME PROFILE LBG",
#     "K11I005003": "I BEAM BAR - AIRLINE",
#     "K11L001008": "ENDCAP PROFILE",
#     "K11I001031": "BOX TYPE SAND TRAP BOTTOM FRAME PROFILE",
#     "K11I001012": "FRAME PROFILE LAD F-100",
#     "K11I001006": "INNERVANE PROFILE LAD F-75",
#     "K11I001011": "VCD PROFILE LAD F-75",
#     "K11I009002": "BLADE PROFILE FOR KX3",
#     # add the rest of your mapping here...
# }

# PROFILE_NAMES = list(PROFILE_MAP.values())


# def refresh_table(conn=None):
#     """Refresh the database view table"""
#     try:
#         if conn is None:
#             conn = sqlite3.connect("inventory.db")
#
#         cursor = conn.cursor()
#         cursor.execute("SELECT profile_id, name, length, quantity, bin FROM profiles ORDER BY name, length")
#         rows = cursor.fetchall()
#
#         # Clear old rows safely
#         if dpg.does_item_exist("db_table"):
#             dpg.delete_item("db_table", children_only=True)
#
#             # Re-add rows
#             for row in rows:
#                 with dpg.table_row(parent="db_table"):
#                     for col in row:
#                         dpg.add_text(str(col))
#         else:
#             print("Warning: db_table item doesn't exist yet")
#
#     except Exception as e:
#         print(f"Error refreshing table: {e}")
#     finally:
#         if conn and conn is not None:
#             conn.close()


# def submit_profile_callback(sender, app_data, user_data):
#     """Callback for adding a new profile"""
#     try:
#         name = dpg.get_value("profile_name_dropdown")
#         length = float(dpg.get_value("length_input"))
#         quantity = int(dpg.get_value("quantity_input"))

#         with sqlite3.connect("inventory.db") as conn:
#             add_profile(conn, name, length, quantity)

#         refresh_database_view()

#         # clear inputs
#         dpg.set_value("length_input", 0.0)
#         dpg.set_value("quantity_input", 0)

#     except Exception as e:
#         print(f"Error adding profile: {e}")


# def refresh_database_view():
#     """Load profiles from DB and display in a readable format"""
#     try:
#         with sqlite3.connect("inventory.db") as conn:
#             df = pd.read_sql_query(
#                 "SELECT profile_id, name, length, quantity, bin FROM profiles ORDER BY name, length",
#                 conn
#             )

#         # Clear previous content
#         if dpg.does_item_exist("db_view_window"):
#             dpg.delete_item("db_view_window", children_only=True)

#         if df.empty:
#             dpg.add_text("No profiles in database.", parent="db_view_window")
#             return

#         # Display as formatted text
#         headers = f"{'ID':<5} {'Name':<40} {'Length (mm)':<12} {'Qty':<5} {'Bin':<15}"
#         dpg.add_text(headers, parent="db_view_window")
#         dpg.add_text("-" * len(headers), parent="db_view_window")

#         for _, row in df.iterrows():
#             line = f"{row['profile_id']:<5} {row['name']:<40} {row['length']:<12.0f} {row['quantity']:<5} {row['bin']:<15}"
#             dpg.add_text(line, parent="db_view_window")

#     except Exception as e:
#         dpg.add_text(f"Error loading database: {e}", parent="db_view_window")


# def launch_ui():
#     dpg.create_context()
#     dpg.create_viewport(title="Inventory Management", width=800, height=600)

#     with dpg.window(label="Inventory Manager", width=780, height=580):
#         with dpg.tab_bar():

#             # --- Tab 1: Add Profile ---
#             with dpg.tab(label="Add Profile"):
#                 dpg.add_combo(PROFILE_NAMES, label="Profile Name", tag="profile_name_dropdown")
#                 dpg.add_input_float(label="Length (mm)", tag="length_input", default_value=0.0)
#                 dpg.add_input_int(label="Quantity", tag="quantity_input", default_value=0)
#                 dpg.add_button(label="Add to Database", callback=submit_profile_callback)

#             # --- Tab 2: View Database ---
#             with dpg.tab(label="View Database"):
#                 dpg.add_button(label="Refresh Table", callback=lambda: refresh_database_view())
#                 dpg.add_separator()
#                 dpg.add_child_window(tag="db_view_window", width=-1, height=-1, horizontal_scrollbar=True)

#     dpg.setup_dearpygui()
#     dpg.show_viewport()
#     dpg.start_dearpygui()
#     dpg.destroy_context()


# # --- Improved Best Fit Allocation Algorithm ---
def best_fit_allocation(required_length: float, required_qty: int, profile_name: str, conn) -> Dict:
    """
    Implements true best-fit algorithm to allocate scrap materials.
    Returns allocation results and updates database.
    """

    # Input validation
    if required_length <= 0:
        raise ValueError(f"Required length must be positive, got {required_length}")
    if required_qty <= 0:
        raise ValueError(f"Required quantity must be positive, got {required_qty}")
    if required_length <= CUTTING_ALLOWANCE:
        raise ValueError(
            f"Required length ({required_length}mm) too small for cutting allowance ({CUTTING_ALLOWANCE}mm)")

    cursor = conn.cursor()

    allocation_result = {
        'required_length': required_length,
        'required_qty': required_qty,
        'allocated_from_scrap': 0,
        'allocated_from_new': 0,
        'scrap_used': [],
        'scrap_created': [],
        'remaining_requirement': required_qty,
        'new_profiles_needed': 0
    }

    # Try to allocate from scrap first (best-fit: smallest viable piece first)
    req_length = required_length + CUTTING_ALLOWANCE
    remaining = required_qty

    while remaining > 0:

        # Get available scrap profiles of the same type, sorted by length ASCENDING for true best-fit
        cursor.execute("""
            SELECT profile_id, length, quantity 
            FROM profiles 
            WHERE name = ? AND length >= ? 
            ORDER BY length ASC
            LIMIT 1
        """, (profile_name, required_length + CUTTING_ALLOWANCE))

        available_profile = cursor.fetchone()

        if not available_profile:
            break

        profile_id, scrap_length, scrap_qty = available_profile

        # Calculate how many pieces we can get from this scrap profile
        pieces_per_scrap = int(scrap_length // req_length)

        scrap_needed = min(
            (remaining + pieces_per_scrap - 1) // pieces_per_scrap,
            scrap_qty
        )

        if scrap_needed > 0:
            # Calculate actual pieces obtained
            pieces_obtained = min(scrap_needed * pieces_per_scrap, remaining)
            full_scraps = pieces_obtained // pieces_per_scrap
            partial_scraps = scrap_needed - full_scraps
            partial_pieces = pieces_obtained % pieces_per_scrap

            # Update allocation
            allocation_result['allocated_from_scrap'] += scrap_needed
            remaining -= pieces_obtained

            if full_scraps > 0:
                leftover_full = scrap_length - (pieces_per_scrap * req_length)
            else:
                leftover_full = 0

            if partial_scraps > 0:
                leftover_partial = scrap_length - (partial_pieces * req_length)
            else:
                leftover_partial = 0

            allocation_result['scrap_used'].append({
                'profile_id': profile_id,
                'scrap_length': scrap_length,
                'scrap_qty_used': scrap_needed,
                'pieces_per_scrap': pieces_per_scrap,
                'total_pieces': pieces_obtained,
                'total_waste': leftover_partial + leftover_full
            })

            # Update database - reduce scrap quantity
            new_scrap_qty = scrap_qty - scrap_needed
            if new_scrap_qty > 0:
                cursor.execute("""
                    UPDATE profiles SET quantity = ? WHERE profile_id = ?
                """, (new_scrap_qty, profile_id))
            else:
                cursor.execute("DELETE FROM profiles WHERE profile_id = ?", (profile_id,))

            if leftover_full >= MIN_SCRAP_LENGTH:
                try:
                    cursor.execute("""
                        INSERT INTO profiles (name, length, quantity, bin)
                        VALUES (?, ?, ?, ?)
                    """, (profile_name, leftover_full, full_scraps, classify_bin(leftover_full)))

                except sqlite3.Error as e:
                    print(f"Warning: Could not add leftover scrap to database: {e}")

            if leftover_partial >= MIN_SCRAP_LENGTH:
                try:
                    cursor.execute("""
                        INSERT INTO profiles (name, length, quantity, bin)
                        VALUES (?, ?, ?, ?)
                    """, (profile_name, leftover_partial, partial_scraps, classify_bin(leftover_partial)))

                except sqlite3.Error as e:
                    print(f"Warning: Could not add leftover scrap to database: {e}")

    allocation_result['remaining_requirement'] = remaining

    # If still need more, allocate from new profiles
    if remaining > 0:
        # Check if new profile can fulfill the requirement
        # usable_new_length = NEW_PROFILE_LENGTH - CUTTING_ALLOWANCE
        # if required_length > usable_new_length:
        #     raise ValueError(
        #         f"Required length ({required_length}mm) exceeds new profile capacity ({usable_new_length}mm)")

        pieces_per_new = int(NEW_PROFILE_LENGTH // req_length)
        new_profiles_needed = (remaining + pieces_per_new - 1) // pieces_per_new  # Ceiling division

        remainder = remaining % pieces_per_new

        if remainder == 0:
            full_new_profiles = new_profiles_needed
            partial_new_profiles = 0
            partial_new_pieces = 0
        else:
            full_new_profiles = new_profiles_needed - 1
            partial_new_profiles = 1
            partial_new_pieces = remainder

        leftover_per_full = NEW_PROFILE_LENGTH - (pieces_per_new * req_length)
        leftover_per_partial = NEW_PROFILE_LENGTH - (partial_new_pieces * req_length) if partial_new_profiles > 0 else 0

        # Total scrap created
        total_new_scrap = (leftover_per_full * full_new_profiles) + (leftover_per_partial * partial_new_profiles)

        allocation_result['allocated_from_new'] = remaining
        allocation_result['new_profiles_needed'] = new_profiles_needed

        allocation_result['scrap_created'].append({
            'profile_name': profile_name,
            'scrap_length': [leftover_per_full, leftover_per_partial],
            'scrap_qty': [full_new_profiles, partial_new_profiles],
            'total_waste': total_new_scrap
        })

        if leftover_per_full >= MIN_SCRAP_LENGTH and full_new_profiles > 0:  # Only keep scrap if it's useful
            # Add leftover as new scrap to database
            try:
                # Check if this scrap length already exists
                cursor.execute("""
                    SELECT quantity FROM profiles 
                    WHERE name = ? AND length = ?
                """, (profile_name, leftover_per_full))

                existing = cursor.fetchone()

                if existing:
                    # Update existing scrap quantity
                    new_quantity = existing[0] + full_new_profiles
                    cursor.execute("""
                    UPDATE profiles 
                    SET quantity = ? 
                    WHERE name = ? AND length = ?
                """, (new_quantity, profile_name, leftover_per_full))
                else:
                    # Insert new scrap
                    cursor.execute("""
                        INSERT INTO profiles (name, length, quantity, bin)
                        VALUES (?, ?, ?, ?)
                    """, (profile_name, leftover_per_full, full_new_profiles,
                          classify_bin(leftover_per_full)))

                # Update bin summary
                cursor.execute("""
                    INSERT INTO bin_summary (bin, total_quantity)
                    VALUES (?, ?)
                    ON CONFLICT(bin) DO UPDATE SET total_quantity = total_quantity + excluded.total_quantity
                """, (classify_bin(leftover_per_full), full_new_profiles))

            except sqlite3.Error as e:
                print(f"Warning: Could not add leftover scrap to database: {e}")

        if leftover_per_partial >= MIN_SCRAP_LENGTH and partial_new_profiles > 0:
            try:
                # Check if this scrap length already exists
                cursor.execute("""
                    SELECT quantity FROM profiles 
                    WHERE name = ? AND length = ?
                """, (profile_name, leftover_per_partial))

                existing = cursor.fetchone()

                if existing:
                    # Update existing scrap quantity
                    new_quantity = existing[0] + partial_new_profiles
                    cursor.execute("""
                        UPDATE profiles 
                        SET quantity = ? 
                        WHERE name = ? AND length = ?
                    """, (new_quantity, profile_name, leftover_per_partial))
                else:
                    # Insert new scrap
                    cursor.execute("""
                        INSERT INTO profiles (name, length, quantity, bin)
                        VALUES (?, ?, ?, ?)
                    """, (profile_name, leftover_per_partial, partial_new_profiles,
                          classify_bin(leftover_per_partial)))

                # Update bin summary
                cursor.execute("""
                    INSERT INTO bin_summary (bin, total_quantity)
                    VALUES (?, ?)
                    ON CONFLICT(bin) DO UPDATE SET total_quantity = total_quantity + excluded.total_quantity
                """, (classify_bin(leftover_per_partial), partial_new_profiles))

            except sqlite3.Error as e:
                print(f"Warning: Could not add leftover scrap to database: {e}")

    try:
        conn.commit()
    except sqlite3.Error as e:
        conn.rollback()
        raise Exception(f"Database transaction failed: {e}")

    return allocation_result


# --- Excel Processing with Better Error Handling ---
def process_cutlist(excel_file_path: str, conn):
    """
    Reads the Excel cutlist and processes each requirement
    """
    # Validate file exists
    if not os.path.exists(excel_file_path):
        raise FileNotFoundError(f"Excel file not found: {excel_file_path}")

    try:
        # Read Excel file
        df = pd.read_excel(excel_file_path, sheet_name='Sheet1')

        if df.empty:
            print("Warning: Excel file is empty")
            return

        # Clean column names (remove extra spaces)
        df.columns = [str(col).strip() for col in df.columns]

        print("Cutlist Processing Results:")
        print("=" * 80)

        processed_rows = 0
        # Process each row with valid MODEL data
        for index, row in df.iterrows():
            try:
                model = str(row.get('MODEL', '')).strip()

                # Skip rows without valid MODEL or with header-like values
                if (not model or model in ['MODEL', '0', '01-LAD/9108-25',
                                           '01-LAD/9107-25', '01-LAD/9109-25'] or
                        'KSLAD' not in model and 'KRLAD' not in model):
                    continue

                # Extract requirements based on MODEL type
                if 'KSLAD F-75' in model or 'KRLAD F-75' in model:
                    process_f75_requirements(row, conn, index)
                    processed_rows += 1

            except Exception as e:
                print(f"Error processing row {index + 1}: {e}")
                continue

        print(f"\nProcessed {processed_rows} valid rows from cutlist")

    except Exception as e:
        raise Exception(f"Error processing cutlist: {e}")


def process_f75_requirements(row, conn, index):
    """
    Process requirements for F-75 models with improved validation
    """

    print('Processing F-75 requirements...')

    def safe_int(value, default=0):
        try:
            return int(value) if pd.notna(value) and value != '' else default
        except (ValueError, TypeError):
            return default

    def safe_float(value, default=0.0):
        try:
            return float(value) if pd.notna(value) and value != '' else default
        except (ValueError, TypeError):
            return default

    try:
        # Get quantities with validation
        frame_qty = safe_int(row.get('FRAME_QTY'))
        inner_vane_qty = safe_int(row.get('IV_QTY'))
        pce_qty = safe_int(row.get('PCE_QTY'))
        vcd_qty = safe_int(row.get('VCD_QTY'))

        # Get lengths with validation
        frame_length = safe_float(row.get('FRAME LENGTH'))
        inner_vane_length = safe_float(row.get('INNER VANE'))
        pce_length = safe_float(row.get('PCE'))
        vcd_length = safe_float(row.get('VCD'))

        print(f"\nRow {index + 1}: {row.get('MODEL', 'N/A')}")
        print(f"Length: {row.get('Length  (mm)', 'N/A')}mm, Qty: {row.get('Qty', 'N/A')}")

        # Process each requirement type
        requirements = [
            (frame_qty, frame_length, "FRAME PROFILE FOR LAD F-75", "FRAME"),
            (inner_vane_qty, inner_vane_length, "INNERVANE PROFILE LAD F-75", "INNER VANE"),
            (pce_qty, pce_length, "P.C.E. PROFILE LAD F-75", "PCE"),
            (vcd_qty, vcd_length, "VCD PROFILE LAD F-75", "VCD"),
        ]

        print("Requirements generated...")

        for qty, length, profile_name, req_type in requirements:
            if qty > 0 and length > 0:
                print(f"\n{req_type} Requirement: {length}mm x {qty}pcs")
                try:
                    result = best_fit_allocation(length, qty, profile_name, conn)
                    print_allocation_result(result)
                except Exception as e:
                    print(f"  Error allocating {req_type}: {e}")

    except Exception as e:
        print(f"Error processing F-75 requirements for row {index + 1}: {e}")


def print_allocation_result(result: Dict):
    """
    Print formatted allocation results with more detail
    """
    print(f"  ✓ Allocated from scrap: {result['allocated_from_scrap']} pcs")
    print(f"  ✓ Allocated from new: {result['allocated_from_new']} pcs")

    if result['remaining_requirement'] > 0:
        print(f"  ⚠ Remaining requirement: {result['remaining_requirement']} pcs")
    else:
        print(f"  ✓ Requirement fully satisfied")

    if result['scrap_used']:
        print("  📦 Scrap used:")
        total_waste = 0
        for scrap in result['scrap_used']:
            waste = scrap.get('total_waste', 0)
            total_waste += waste
            print(f"    - Profile {scrap['profile_id']}: {scrap['scrap_length']}mm "
                  f"({scrap['scrap_qty_used']} pieces → {scrap['total_pieces']} cuts), Waste: {waste}mm")
        # if total_waste > 0:
        #     print(f"  🗑 Total waste from scrap: {total_waste}mm")

    if result.get('new_profiles_needed', 0) > 0:
        print(f"  🆕 New profiles needed: {result['new_profiles_needed']}")


# --- Main Execution with Better Error Handling ---
if __name__ == "__main__":
    try:
        # Setup database
        conn = setup_database()
        cursor = conn.cursor()

        # Display initial inventory
        print("Initial Inventory:")
        cursor.execute("SELECT * FROM profiles ORDER BY name, length")
        profiles = cursor.fetchall()

        if not profiles:
            print("  No profiles in inventory")
        else:
            for row in profiles:
                print(f"  {row[1]}: {row[2]}mm x {row[3]}pcs (bin: {row[4]})")

        # Process cutlist
        excel_file_path = "LAD cutlist-2.xlsx"
        if os.path.exists(excel_file_path):
            process_cutlist(excel_file_path, conn)
        else:
            print(f"\nWarning: Excel file '{excel_file_path}' not found. Skipping cutlist processing.")

        # Display final inventory
        print("\n" + "=" * 80)
        print("Final Inventory:")
        cursor.execute("SELECT * FROM profiles ORDER BY name, length")
        final_profiles = cursor.fetchall()

        if not final_profiles:
            print("  No profiles remaining in inventory")
        else:
            for row in final_profiles:
                print(f"  {row[1]}: {row[2]}mm x {row[3]}pcs (bin: {row[4]})")

        #launch_ui()

    except Exception as e:
        print(f"Fatal error: {e}")
    finally:
        if 'conn' in locals():
            conn.close()