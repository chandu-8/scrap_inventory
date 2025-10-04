import pandas as pd
import os
import math
from typing import List, Dict, Any

import pydevd_pycharm


def parse_cutlist(excel_file_path: str) -> List[Dict[str, Any]]:
    """
    Parse Excel cutlist and return requirements without processing allocation.
    Returns list of requirement dictionaries.
    """
    if not os.path.exists(excel_file_path):
        raise FileNotFoundError(f"Excel file not found: {excel_file_path}")
    
    try:
        df = pd.read_excel(excel_file_path, sheet_name='Sheet1')
        
        if df.empty:
            print("Warning: Excel file is empty")
            return []
        
        # Clean column names
        df.columns = [str(col).strip() for col in df.columns]
        
        requirements = []
        processed_rows = 0
        
        for index, row in df.iterrows():
            try:
                model = str(row.get('MODEL', '')).strip()
                
                # Skip invalid rows
                if (not model or model in ['MODEL', '0', '01-LAD/9108-25',
                                           '01-LAD/9107-25', '01-LAD/9109-25'] or
                        'KSLAD' not in model and 'KRLAD' not in model):
                    continue
                
                # Process F-75 requirements
                if 'KSLAD F-75' in model or 'KRLAD F-75' in model:
                    row_requirements = extract_f75_requirements(row, index)
                    if row_requirements:
                        requirements.extend(row_requirements)
                        processed_rows += 1
            
            except Exception as e:
                print(f"Error processing row {index + 1}: {e}")
                continue
        
        print(f"Parsed {processed_rows} valid rows from cutlist")
        return requirements
    
    except Exception as e:
        raise Exception(f"Error parsing cutlist: {e}")

def extract_f75_requirements(row, index):
    """Extract F-75 requirements from a row"""
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
    
    def round_length_mm(length_value: float) -> int:
        """Round length with .5 up and <.5 down to nearest mm."""
        try:
            if length_value is None:
                return 0
            # Ensure float
            numeric = float(length_value)
            # Half-up rule
            return int(math.floor(numeric + 0.5))
        except (ValueError, TypeError):
            return 0
    
    try:
        # Get quantities and lengths
        frame_qty = safe_int(row.get('FRAME_QTY'))
        inner_vane_qty = safe_int(row.get('IV_QTY'))
        pce_qty = safe_int(row.get('PCE_QTY'))
        vcd_qty = safe_int(row.get('VCD_QTY'))
        
        frame_length = round_length_mm(safe_float(row.get('FRAME LENGTH')))
        inner_vane_length = round_length_mm(safe_float(row.get('INNER VANE')))
        pce_length = round_length_mm(safe_float(row.get('PCE')))
        vcd_length = round_length_mm(safe_float(row.get('VCD')))
        
        requirements = []
        
        # Create requirement objects
        req_types = [
            (frame_qty, frame_length, "FRAME PROFILE FOR LAD F-75", "FRAME"),
            (inner_vane_qty, inner_vane_length, "INNERVANE PROFILE LAD F-75", "INNER VANE"),
            (pce_qty, pce_length, "P.C.E. PROFILE LAD F-75", "PCE"),
            (vcd_qty, vcd_length, "VCD PROFILE LAD F-75", "VCD"),
        ]
        
        for qty, length, profile_name, req_type in req_types:
            if qty > 0 and length > 0:
                requirements.append({
                    'row_index': index + 1,
                    'model': row.get('MODEL', 'N/A'),
                    'requirement_type': req_type,
                    'profile_name': profile_name,
                    'length': length,
                    'quantity': qty,
                    'processed': False
                })
        
        return requirements
    
    except Exception as e:
        print(f"Error extracting F-75 requirements for row {index + 1}: {e}")
        return []

def process_requirements(requirements: List[Dict], conn):
    """Process a list of requirements using allocation algorithm"""
    from allocation import best_fit_allocation, print_allocation_result

    sorted_requirements = sorted(requirements, key=lambda x: x['length'], reverse=True)
    
    print("Processing Requirements:")
    print("=" * 80)

    total_new_profiles = 0
    per_profile_new = {}

    #pydevd_pycharm.settrace(suspend=True, trace_only_current_thread=True)
    for req in sorted_requirements:
        if not req['processed']:
            print(f"\n{req['requirement_type']} Requirement: {req['length']}mm x {req['quantity']}pcs")
            try:
                result = best_fit_allocation(req['length'], req['quantity'], req['profile_name'], conn)
                print_allocation_result(result)
                req['processed'] = True

                added = int(result.get('new_profiles_needed', 0) or 0)
                if added > 0:
                    total_new_profiles += added
                    per_profile_new[req['profile_name']] = per_profile_new.get(req['profile_name'], 0) + added
            except Exception as e:
                print(f"  Error allocating {req['requirement_type']}: {e}")

    print("\n" + "=" * 80)
    print(f"Total new profiles added: {total_new_profiles}")
    if per_profile_new:
        print("\nNew profiles added per profile:")
        for profile, count in per_profile_new.items():
            print(f"  {profile}: {count}")
    
    return {"total_new_profiles": total_new_profiles, "per_profile_new": per_profile_new}