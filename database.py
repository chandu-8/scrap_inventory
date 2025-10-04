import sqlite3
from typing import List, Tuple, Optional
from config import classify_bin, get_profile_id_by_name

def get_connection(db_path="inventory.db"):
    """Get database connection"""
    return sqlite3.connect(db_path)

def setup_database(reset=False):
    """Setup database tables with profile_id as TEXT"""
    conn = get_connection()
    cursor = conn.cursor()
    
    if reset:
        cursor.execute("""DROP TABLE IF EXISTS profiles""")
        cursor.execute("""DROP TABLE IF EXISTS bin_summary""")
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS profiles (
        profile_id TEXT NOT NULL,
        name TEXT NOT NULL,
        length REAL NOT NULL CHECK (length > 0),
        quantity INTEGER NOT NULL CHECK (quantity >= 0),
        bin TEXT NOT NULL,
        PRIMARY KEY (profile_id, length)
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bin_summary (
        bin TEXT PRIMARY KEY,
        total_quantity INTEGER NOT NULL CHECK (total_quantity >= 0)
    )
    """)
    
    # Add index for better performance
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_profiles_name_length ON profiles(name, length)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_profiles_id ON profiles(profile_id)")
    
    conn.commit()
    return conn

def add_profile(conn, name, length, quantity):
    """Add or update profile in database using profile ID"""
    if length <= 0 or quantity <= 0:
        return False
    
    # Get profile ID from name
    profile_id = get_profile_id_by_name(name)
    if not profile_id:
        print(f"Warning: Profile ID not found for '{name}'. Using name as ID.")
        profile_id = name  # Fallback to using name as ID
    
    cursor = conn.cursor()
    bin_class = classify_bin(length)
    
    # Check if profile exists (same ID and length)
    cursor.execute("""
        SELECT quantity
        FROM profiles
        WHERE profile_id = ? AND length = ?
    """, (profile_id, length))
    
    existing = cursor.fetchone()
    
    if existing:
        # Update existing profile
        old_qty = existing[0]
        new_qty = old_qty + quantity
        cursor.execute("""
            UPDATE profiles
            SET quantity = ?
            WHERE profile_id = ? AND length = ?
        """, (new_qty, profile_id, length))
        
        # Update bin_summary
        cursor.execute("""
            UPDATE bin_summary
            SET total_quantity = total_quantity + ?
            WHERE bin = ?
        """, (quantity, bin_class))
    else:
        # Insert new profile
        cursor.execute("""
            INSERT INTO profiles (profile_id, name, length, quantity, bin)
            VALUES (?, ?, ?, ?, ?)
        """, (profile_id, name, length, quantity, bin_class))
        
        cursor.execute("""
            INSERT INTO bin_summary (bin, total_quantity)
            VALUES (?, ?)
            ON CONFLICT(bin) DO UPDATE SET total_quantity = total_quantity + excluded.total_quantity
        """, (bin_class, quantity))
    
    conn.commit()
    return True

def get_all_profiles(conn):
    """Get all profiles from database"""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM profiles ORDER BY profile_id, length")
    return cursor.fetchall()

def get_profiles_by_id(conn, profile_id):
    """Get profiles by profile ID"""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM profiles WHERE profile_id = ? ORDER BY length", (profile_id,))
    return cursor.fetchall()

def get_profiles_by_name(conn, name):
    """Get profiles by name"""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM profiles WHERE name = ? ORDER BY length", (name,))
    return cursor.fetchall()

def update_profile_quantity(conn, profile_id, length, new_quantity):
    """Update profile quantity by profile_id and length"""
    cursor = conn.cursor()
    if new_quantity > 0:
        cursor.execute("UPDATE profiles SET quantity = ? WHERE profile_id = ? AND length = ?", 
                     (new_quantity, profile_id, length))
    else:
        cursor.execute("DELETE FROM profiles WHERE profile_id = ? AND length = ?", 
                     (profile_id, length))
    conn.commit()

def delete_profile(conn, profile_id, length):
    """Delete profile from database by profile_id and length"""
    cursor = conn.cursor()
    cursor.execute("DELETE FROM profiles WHERE profile_id = ? AND length = ?", 
                 (profile_id, length))
    conn.commit()