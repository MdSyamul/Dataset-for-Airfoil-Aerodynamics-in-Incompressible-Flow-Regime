import subprocess
import numpy as np
import csv
import os

# --- User Inputs ---
AIRFOIL_LIST = ["NACA 4412"]

# Mach number list
MACH_LIST = [0.001, 0.1]

# Reynolds number sweep parameters
re_strt = 30000
re_end = 30000
re_step = 1
re_num = int((re_end - re_strt) / re_step) + 1

# Angle of attack sweep parameters
alfa_strt = -4
alfa_end = 16
alfa_step = 1
alfa_num = int((alfa_end - alfa_strt) / alfa_step) + 1

# Path to XFOIL executable
XFOIL_PATH = r"c:/Users/shadm/Desktop/Run Sim/XFOIL6.99/xfoil.exe"

# Create output directory if it doesn't exist
os.makedirs('output', exist_ok=True)

# --- Paneling Parameters ---
NUM_PANELS = 200    # total panels
BUNCH = 1.1         # bunching parameter
TELE_RATIO = 0.3    # TE/LE ratio (T in XFOIL PPAR)

def get_cmd(airfoil_name, mach, re, alfa_strt, alfa_end, alfa_step):
    safe_airfoil_name = airfoil_name.replace(" ", "_")
    cmd = f"""\

{airfoil_name}

PANE
PPAR
N {NUM_PANELS}
P {BUNCH}
T {TELE_RATIO}

\n

OPER
MACH {mach}
VISC {re}
ITER 10000
PACC
output/{safe_airfoil_name}_{mach}_{re}_SAVE

ASEQ {alfa_strt} {alfa_end} {alfa_step}
PACC
QUIT
"""
    return cmd

def xfoil_interact(airfoil_name, mach, re, alfa_strt, alfa_end, alfa_step):
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = 6  # Minimize window

    p = subprocess.Popen(
        [XFOIL_PATH],
        stdout=subprocess.PIPE,
        stdin=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        startupinfo=startupinfo,
        universal_newlines=True
    )
    
    try:
        cmd = get_cmd(airfoil_name, mach, re, alfa_strt, alfa_end, alfa_step)
        stdout, _ = p.communicate(input=cmd, timeout=60)
        print(stdout)
    except subprocess.TimeoutExpired:
        print(f"Iteration for {airfoil_name} at Mach {mach} Reynolds {re} timed out.")
        p.kill()
        return False
    
    return True

for AIRFOIL_NAME in AIRFOIL_LIST:
    SAFE_AIRFOIL_NAME = AIRFOIL_NAME.replace(" ", "_")
    OUTPUT_CSV = f'output/{SAFE_AIRFOIL_NAME}.csv'

    digits = AIRFOIL_NAME.strip().split()[-1]  # e.g. '4406'
    M = int(digits[0])
    P = int(digits[1])
    TT = int(digits[2:])

    total_rows = len(MACH_LIST) * re_num * alfa_num
    tbl = np.zeros([total_rows, 10])  # Columns: M,P,T,Mach,Re,Alpha,Cl,Cd,Cm,Cdp

    row_idx = 0
    for mach in MACH_LIST:
        for re in range(re_strt, re_end + 1, re_step):
            print(f"Running {AIRFOIL_NAME} at Mach {mach:.3f}, Re {re}...")
            success = xfoil_interact(AIRFOIL_NAME, mach, re, alfa_strt, alfa_end, alfa_step)
            if not success:
                print(f"Skipping Mach {mach} Re {re} due to timeout.")
                continue
            
            output_file = f'output/{SAFE_AIRFOIL_NAME}_{mach}_{re}_SAVE'
            try:
                with open(output_file, 'r') as infile:
                    lines = infile.readlines()
            except FileNotFoundError:
                print(f"Output file {output_file} not found, skipping...")
                continue
            
            # Skip header lines (XFOIL usually first 12 lines are header)
            data_lines = lines[12:]
            
            for line in data_lines:
                parts = line.split()
                if len(parts) < 5:
                    continue
                try:
                    alpha = float(parts[0])
                    cl = float(parts[1])
                    cd = float(parts[2])
                    cdp = float(parts[3])
                    cm = float(parts[4])
                except ValueError:
                    continue  # skip lines that don’t parse
                
                tbl[row_idx, :] = [M/100, P/10, TT/100, mach, re, alpha, cl, cd, cm, cdp]
                row_idx += 1
            
            os.remove(output_file)
    
    # Truncate to actual filled rows
    tbl = tbl[:row_idx, :]
    
    # Write output CSV with header
    header = ['M', 'P', 'T', 'Mach', 'Re', 'Alpha', 'Cl', 'Cd', 'Cm', 'Cdp']
    with open(OUTPUT_CSV, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(tbl)
    
    print(f"Processing for {AIRFOIL_NAME} complete. Results saved to '{OUTPUT_CSV}'.")

print("All airfoils processed successfully. End of execution.")
