import sqlite3

import pydevd_pycharm

from config import MIN_SCRAP_LENGTH, NEW_PROFILE_LENGTH, classify_bin, get_profile_name_by_id, get_profile_id_by_name, get_cutting_allowance

# --- Improved Best Fit Allocation Algorithm ---
def best_fit_allocation(required_length: float, required_qty: int, profile_name: str, conn):
    """
    Implements true best-fit algorithm to allocate scrap materials.
    Returns allocation results and updates database.
    """
    cutting_allowance = get_cutting_allowance(profile_name)

    # Input validation
    if required_length <= 0:
        raise ValueError(f"Required length must be positive, got {required_length}")
    if required_qty <= 0:
        raise ValueError(f"Required quantity must be positive, got {required_qty}")
    if required_length <= cutting_allowance:
        raise ValueError(
            f"Required length ({required_length}mm) too small for cutting allowance ({cutting_allowance}mm)")

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
    req_length_ind = required_length + cutting_allowance
    req_length_total = req_length_ind * required_qty
    remaining = required_qty

    while remaining > 0:

        # Get available scrap profiles of the same type, sorted by length ASCENDING for true best-fit
        cursor.execute("""
            SELECT profile_id, length, quantity
            FROM profiles
            WHERE name = ? AND length >= ?
            ORDER BY length ASC
            LIMIT 1
        """, (profile_name, req_length_ind))

        available_profile = cursor.fetchone()

        if not available_profile:
            break

        profile_id, scrap_length, scrap_qty = available_profile
        # profile_name = get_profile_name_by_id(profile_id)

        # Calculate how many pieces we can get from this scrap profile
        pieces_per_scrap = int(scrap_length // req_length_ind)

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
                leftover_full = scrap_length - (pieces_per_scrap * req_length_ind)
            else:
                leftover_full = 0

            if partial_scraps > 0:
                leftover_partial = scrap_length - (partial_pieces * req_length_ind)
            else:
                leftover_partial = 0

            allocation_result['scrap_used'].append({
                'profile_id': profile_id,
                'scrap_length': scrap_length,
                'scrap_qty_used': scrap_needed,
                'pieces_per_scrap': pieces_per_scrap,
                'total_pieces': pieces_obtained,
                # 'waste_per_piece': leftover_partial + leftover_full
                'total_waste': leftover_partial + leftover_full
            })

            # Update database - reduce scrap quantity
            new_scrap_qty = scrap_qty - scrap_needed
            if new_scrap_qty > 0:
                cursor.execute("""
                    UPDATE profiles SET quantity = ? WHERE profile_id = ? and length = ?
                """, (new_scrap_qty, profile_id, scrap_length))
            else:
                cursor.execute("DELETE FROM profiles WHERE profile_id = ? and length = ?", (profile_id, scrap_length))

            if leftover_full >= MIN_SCRAP_LENGTH:
                try:
                    cursor.execute("""
                        INSERT INTO profiles (profile_id, name, length, quantity, bin)
                        VALUES (?, ?, ?, ?, ?)
                        ON CONFLICT(profile_id, length) DO UPDATE
                        SET quantity = quantity + excluded.quantity
                    """, (profile_id, profile_name, leftover_full, full_scraps, classify_bin(leftover_full)))

                    # Update bin_summary
                    cursor.execute("""
                        INSERT INTO bin_summary (bin, total_quantity)
                        VALUES (?, ?)
                        ON CONFLICT(bin) DO UPDATE SET total_quantity = total_quantity + excluded.total_quantity
                    """, (classify_bin(leftover_full), full_scraps))
                except sqlite3.Error as e:
                    # pydevd_pycharm.settrace(suspend=True, trace_only_current_thread=True)
                    print(f"Warning: Could not add leftover scrap to database: {e}")

            if leftover_partial >= MIN_SCRAP_LENGTH:
                try:
                    cursor.execute("""
                        INSERT INTO profiles (profile_id, name, length, quantity, bin)
                        VALUES (?, ?, ?, ?, ?)
                        ON CONFLICT(profile_id, length) DO UPDATE
                        SET quantity = quantity + excluded.quantity
                    """, (profile_id, profile_name, leftover_partial, partial_scraps, classify_bin(leftover_partial)))

                    # Update bin_summary
                    cursor.execute("""
                        INSERT INTO bin_summary (bin, total_quantity)
                        VALUES (?, ?)
                        ON CONFLICT(bin) DO UPDATE SET total_quantity = total_quantity + excluded.total_quantity
                    """, (classify_bin(leftover_partial), partial_scraps))
                except sqlite3.Error as e:
                    # pydevd_pycharm.settrace(suspend=True, trace_only_current_thread=True)
                    print(f"Warning: Could not add leftover scrap to database: {e}")

    allocation_result['remaining_requirement'] = remaining

    # If still need more, allocate from new profiles
    if remaining > 0:
        # Check if new profile can fulfill the requirement

        # usable_new_length = NEW_PROFILE_LENGTH - CUTTING_ALLOWANCE
        # if required_length > usable_new_length:
        #     raise ValueError(
        #         f"Required length ({required_length}mm) exceeds new profile capacity ({usable_new_length}mm)")

        profile_id = get_profile_id_by_name(profile_name)

        pieces_per_new = int(NEW_PROFILE_LENGTH // req_length_ind)

        new_profiles_needed = (remaining + pieces_per_new - 1) // pieces_per_new  # Ceiling division

        new_pieces_obtained = remaining

        remainder = remaining % pieces_per_new

        if remainder == 0:
            full_new_profiles = new_profiles_needed
            partial_new_profiles = 0
            partial_new_pieces = 0
        else:
            full_new_profiles = new_profiles_needed - 1
            partial_new_profiles = 1
            partial_new_pieces = remainder

        leftover_per_full = NEW_PROFILE_LENGTH - (pieces_per_new * req_length_ind)
        leftover_per_partial = NEW_PROFILE_LENGTH - (partial_new_pieces * req_length_ind) if partial_new_profiles > 0 else 0

        # Total scrap created
        total_new_scrap = (leftover_per_full * full_new_profiles) + (leftover_per_partial * partial_new_profiles)

        allocation_result['allocated_from_new'] = remaining
        allocation_result['new_profiles_needed'] = new_profiles_needed

        allocation_result['scrap_created'].append({
            'profile_id': profile_id,
            'scrap_length': [leftover_per_full, leftover_per_partial],
            'scrap_qty': [full_new_profiles, partial_new_profiles],
            'total_waste': total_new_scrap
        })


        if leftover_per_full >= MIN_SCRAP_LENGTH and full_new_profiles > 0:  # Only keep scrap if it's useful
            # Add leftover as new scrap to database
            try:
                cursor.execute("""
                    INSERT INTO profiles (profile_id, name, length, quantity, bin)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(profile_id, length) DO UPDATE
                    SET quantity = quantity + excluded.quantity
                """, (profile_id, profile_name, leftover_per_full, full_new_profiles, classify_bin(leftover_per_full)))

                # Update bin summary
                cursor.execute("""
                    INSERT INTO bin_summary (bin, total_quantity)
                    VALUES (?, ?)
                    ON CONFLICT(bin) DO UPDATE
                    SET total_quantity = total_quantity + excluded.total_quantity
                """, (classify_bin(leftover_per_full), full_new_profiles))
            except sqlite3.Error as e:
                # pydevd_pycharm.settrace(suspend=True, trace_only_current_thread=True)
                print(f"Warning: Could not add leftover scrap to database: {e}")

        if leftover_per_partial >= MIN_SCRAP_LENGTH and partial_new_profiles > 0:
            try:
                cursor.execute("""
                    INSERT INTO profiles (profile_id, name, length, quantity, bin)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(profile_id, length) DO UPDATE
                    SET quantity = quantity + excluded.quantity
                """, (profile_id, profile_name, leftover_per_partial, partial_new_profiles, classify_bin(leftover_per_partial)))

                # Update bin summary
                cursor.execute("""
                    INSERT INTO bin_summary (bin, total_quantity)
                    VALUES (?, ?)
                    ON CONFLICT(bin) DO UPDATE
                    SET total_quantity = total_quantity + excluded.total_quantity
                """, (classify_bin(leftover_per_partial), partial_new_profiles))
            except sqlite3.Error as e:
                # pydevd_pycharm.settrace(suspend=True, trace_only_current_thread=True)
                print(f"Warning: Could not add leftover scrap to database: {e}")

    try:
        conn.commit()
    except sqlite3.Error as e:
        conn.rollback()
        raise Exception(f"Database transaction failed: {e}")

    return allocation_result

def print_allocation_result(result):
    
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
            #waste = scrap.get('waste_per_piece', 0) * scrap['scrap_qty_used']
            total_waste += waste
            print(f"    - Profile {scrap['profile_id']}: {scrap['scrap_length']}mm "
                  f"({scrap['scrap_qty_used']} pieces → {scrap['total_pieces']} cuts, Waste: {waste}mm)")
        # if total_waste > 0:
        #     print(f"  🗑 Total waste from scrap: {total_waste}mm")

    if result.get('scrap_created'):
        print("  ♻️  Scrap created from new profiles:")
        for scrap in result['scrap_created']:
            lengths = scrap['scrap_length']
            qtys = scrap['scrap_qty']
            
            if qtys[0] > 0:  # Full profiles
                print(f"    - {qtys[0]} × {lengths[0]}mm (from full profiles)")
            if qtys[1] > 0:  # Partial profiles
                print(f"    - {qtys[1]} × {lengths[1]}mm (from partial profile)")
            
            print(f"    Total scrap: {scrap['total_waste']}mm")

    if result.get('new_profiles_needed', 0) > 0:
        print(f"  🆕 New profiles needed: {result['new_profiles_needed']}")


# ------------------------------------------------------------------------------------------------------------------ #

    # remaining = required_qty
    # req_length = required_length + CUTTING_ALLOWANCE
    #
    # while remaining > 0:
    #
    #     # Fetch all viable scraps (ascending length)
    #     cursor.execute("""
    #         SELECT profile_id, length, quantity
    #         FROM profiles
    #         WHERE name = ? AND length >= ?
    #         ORDER BY length ASC
    #     """, (profile_name, req_length))
    #
    #     candidates = cursor.fetchall()
    #     if not candidates:
    #         break  # fallback to new profiles
    #
    #     best_score = float("inf")
    #     best_candidate = None
    #
    #     for profile_id, scrap_length, scrap_qty in candidates:
    #         pieces_per_scrap = scrap_length // req_length
    #         if pieces_per_scrap == 0:
    #             continue
    #
    #         # Max pieces we can cut from this scrap
    #         usable_pieces = min(pieces_per_scrap * scrap_qty, remaining)
    #         total_provided = usable_pieces * req_length
    #         total_leftover = (scrap_length * scrap_qty) - total_provided
    #
    #         # Gap relative to total remaining requirement
    #         gap = abs(remaining * req_length - total_provided)
    #
    #         # Labor penalty if this scrap hasn't been used yet in this allocation
    #         already_used = any(s['profile_id'] == profile_id for s in allocation_result['scrap_used'])
    #         labor_penalty_weight = 0.5
    #         labor_penalty = labor_penalty_weight if not already_used else 0
    #
    #         score = total_leftover + gap + labor_penalty
    #
    #         if score < best_score:
    #             best_score = score
    #             best_candidate = (profile_id, scrap_length, scrap_qty)
    #
    #     if best_candidate is None:
    #         break  # no usable scrap
    #
    #     # Allocate from best candidate
    #     profile_id, scrap_length, scrap_qty = best_candidate
    #     pieces_per_scrap = scrap_length // req_length
    #     scrap_needed = min((remaining + pieces_per_scrap - 1) // pieces_per_scrap, scrap_qty)
    #     pieces_obtained = min(scrap_needed * pieces_per_scrap, remaining)
    #
    #     # Record allocation
    #     allocation_result['allocated_from_scrap'] += scrap_needed
    #     allocation_result['scrap_used'].append({
    #         'profile_id': profile_id,
    #         'scrap_length': scrap_length,
    #         'scrap_qty_used': scrap_needed,
    #         'pieces_per_scrap': pieces_per_scrap,
    #         'total_pieces': pieces_obtained,
    #         'total_waste': (scrap_length * scrap_needed) - (pieces_obtained * req_length)
    #     })
    #
    #     # Update database
    #     new_scrap_qty = scrap_qty - scrap_needed
    #     if new_scrap_qty > 0:
    #         cursor.execute("""
    #             UPDATE profiles
    #             SET quantity = ?
    #             WHERE profile_id = ? AND length = ?
    #         """, (new_scrap_qty, profile_id, scrap_length))
    #     else:
    #         cursor.execute("""
    #             DELETE FROM profiles
    #             WHERE profile_id = ? AND length = ?
    #         """, (profile_id, scrap_length))
    #
    #     # Insert leftover scrap if >= MIN_SCRAP_LENGTH
    #     leftover_per_scrap = scrap_length - (pieces_per_scrap * req_length)
    #     if leftover_per_scrap >= MIN_SCRAP_LENGTH:
    #         cursor.execute("""
    #             INSERT INTO profiles (profile_id, name, length, quantity, bin)
    #             VALUES (?, ?, ?, ?, ?)
    #             ON CONFLICT(profile_id, length) DO UPDATE
    #             SET quantity = quantity + excluded.quantity
    #         """, (profile_id, profile_name, leftover_per_scrap, scrap_needed,
    #               classify_bin(leftover_per_scrap)))
    #
    #     remaining -= pieces_obtained