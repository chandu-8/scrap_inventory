import os
from database import setup_database, get_connection, get_all_profiles
from ui import launch_ui
import traceback, sys, dearpygui.dearpygui as dpg

# ALWAYS print the full traceback


def excepthook(type, value, tb):
    print('\n' + ''.join(traceback.format_exception(type, value, tb)))
    sys.excepthook = excepthook


sys.excepthook = excepthook


def main():
    try:
        # Setup database (don't reset on startup)
        conn = setup_database(reset=True)
        
        # Display initial inventory
        print("Initial Inventory:")
        profiles = get_all_profiles(conn)
        
        if not profiles:
            print("  No profiles in inventory")
        else:
            for row in profiles:
                print(f"  {row[1]}: {row[2]}mm x {row[3]}pcs (bin: {row[4]})")
        
        print("\n" + "=" * 80)
        print("Launching Inventory Management UI...")
        print("Use the 'Upload Cutlist' tab to process Excel files")
        print("The UI now supports:")
        print("  - Loading multiple files")
        print("  - Reviewing requirements before processing")
        print("  - Switching between tabs while maintaining state")
        
        # Launch GUI (no automatic cutlist processing)
        launch_ui()
    
    except Exception as e:
        print(f"Fatal error: {e}")
    finally:
        if 'conn' in locals():
            conn.close()


if __name__ == "__main__":
    main()