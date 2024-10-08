#!/usr/bin/env python3

import os
import subprocess
import sys
import numpy as np
from scipy.stats import linregress
import matplotlib.pyplot as plt
import re
from pathlib import Path

def get_display_devices():
    cmd = ['dispwin', '-?']
    print("\n=== Listing Display Devices ===")
    print(f"Running command: {' '.join(cmd)}")
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    output = result.stdout + result.stderr
    print(output)
    displays = []
    for line in output.splitlines():
        line = line.strip()
        match = re.match(r'^(\d+)\s*=\s*(.+)$', line)
        if match:
            display_num = int(match.group(1))
            display_desc = match.group(2).strip("'")
            displays.append((display_num, display_desc))
    return displays

def select_display_device(displays):
    print("\nAvailable Display Devices:")
    for idx, (display_num, display_desc) in enumerate(displays, start=1):
        print(f"{idx}: Display {display_num}: {display_desc}")
    while True:
        try:
            choice = int(input("Select the display device by entering its number: "))
            if 1 <= choice <= len(displays):
                return displays[choice - 1][0]
            else:
                print("Invalid selection. Please try again.")
        except ValueError:
            print("Invalid input. Please enter a number.")

def get_patch_counts():
    while True:
        try:
            num_gray = int(input("Enter the number of grayscale patches (e.g., 64, or 0 to skip): "))
            num_color = int(input("Enter the number of single-channel color patches per channel (e.g., 64, or 0 to skip): "))
            if num_gray >= 0 and num_color >= 0:
                if num_gray == 0 and num_color == 0:
                    print("At least one of grayscale or color patches must be greater than zero.")
                    continue
                return num_gray, num_color
            else:
                print("Please enter non-negative integers.")
        except ValueError:
            print("Invalid input. Please enter integers.")

def run_command(cmd, description):
    print(f"\n=== {description} ===")
    print(f"Running command: {' '.join(cmd)}")
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Command failed with error: {e}")
        sys.exit(1)

def calculate_gamma(V_in, L):
    V_in = np.array(V_in)
    L = np.array(L)

    # Normalize luminance values
    L_normalized = L / np.max(L)

    # Remove zero values to avoid log(0)
    mask = (V_in > 0) & (L_normalized > 0)
    V_in = V_in[mask]
    L_normalized = L_normalized[mask]

    # Check if sufficient data points are available
    if len(V_in) < 2:
        return None

    # Calculate gamma using linear regression on log-log data
    log_V_in = np.log(V_in)
    log_L = np.log(L_normalized)

    slope, intercept, r_value, p_value, std_err = linregress(log_V_in, log_L)
    gamma = slope
    return gamma

def main():
    # Change the current working directory to the script's directory
    os.chdir(Path(__file__).parent.resolve())

    # Get the base name from the user
    base_name_input = input("Enter a base name for the calibration files (e.g., 'calibration'): ")

    # Get display devices and let the user select one
    displays = get_display_devices()
    if not displays:
        print("No display devices found.")
        sys.exit(1)
    display_number = select_display_device(displays)

    # Append 'monitor_{display_number}' to the base name
    base_name = f"{base_name_input}_monitor_{display_number}"

    # Create a new directory with the base name
    output_dir = Path(base_name)
    output_dir.mkdir(exist_ok=True)

    # Change the current working directory to the output directory
    os.chdir(output_dir)

    # Get patch counts from the user
    num_gray, num_color = get_patch_counts()

    # Step 1: Generate Test Patches (Grayscale and RGB)
    targen_cmd = ['targen', '-v', '-d3', '-f0']
    if num_gray > 0:
        targen_cmd.append(f'-g{num_gray}')
    if num_color > 0:
        targen_cmd.append(f'-s{num_color}')
    targen_cmd.append(base_name)
    run_command(targen_cmd, 'Generating Test Patches')

    # Step 2: Set the display to a linear state
    dispwin_cmd = ['dispwin', f'-d{display_number}', '-c']
    run_command(dispwin_cmd, 'Setting Display to Linear State')

    # Step 3: Measure the Patches Using dispread
    dispread_cmd = ['dispread', '-v', '-yl', f'-d{display_number}', base_name]
    run_command(dispread_cmd, 'Measuring Patches')

    # Step 4: Process Measurement Data
    ti3_file = f'{base_name}.ti3'

    # Read the .ti3 file
    with open(ti3_file, 'r') as f:
        lines = f.readlines()

    # Find the indices of BEGIN_DATA_FORMAT and END_DATA_FORMAT
    begin_format = lines.index('BEGIN_DATA_FORMAT\n') + 1
    end_format = lines.index('END_DATA_FORMAT\n')

    # Extract headers from the BEGIN_DATA_FORMAT section
    headers = []
    for line in lines[begin_format:end_format]:
        headers.extend(line.strip().split())

    # Find the indices
    device_rgb_index = [headers.index('RGB_R'), headers.index('RGB_G'), headers.index('RGB_B')]
    luminance_index = headers.index('XYZ_Y')

    # Find the BEGIN_DATA and END_DATA indices
    begin_data = lines.index('BEGIN_DATA\n') + 1
    end_data = lines.index('END_DATA\n')

    # Initialize lists to store data for each channel
    V_in_R, L_R = [], []
    V_in_G, L_G = [], []
    V_in_B, L_B = [], []
    V_in_Gray, L_Gray = [], []

    # Parse the data lines
    for line in lines[begin_data:end_data]:
        data = line.strip().split()
        if len(data) < max(device_rgb_index + [luminance_index]) + 1:
            continue  # Skip incomplete lines

        # Get the RGB values
        device_r = float(data[device_rgb_index[0]])
        device_g = float(data[device_rgb_index[1]])
        device_b = float(data[device_rgb_index[2]])

        # Get the luminance value
        Y = float(data[luminance_index])

        # Normalize input values
        V_r = device_r / 100.0
        V_g = device_g / 100.0
        V_b = device_b / 100.0

        # Identify the type of patch and store data accordingly
        if device_r == device_g == device_b and num_gray > 0:
            # Grayscale patch
            V_in_Gray.append(V_r)
            L_Gray.append(Y)
        elif device_r > 0 and device_g == 0 and device_b == 0 and num_color > 0:
            # Red-only patch
            V_in_R.append(V_r)
            L_R.append(Y)
        elif device_g > 0 and device_r == 0 and device_b == 0 and num_color > 0:
            # Green-only patch
            V_in_G.append(V_g)
            L_G.append(Y)
        elif device_b > 0 and device_r == 0 and device_g == 0 and num_color > 0:
            # Blue-only patch
            V_in_B.append(V_b)
            L_B.append(Y)
        else:
            continue  # Skip mixed color patches

    # Calculate gamma values
    gamma_R = calculate_gamma(V_in_R, L_R) if V_in_R else None
    gamma_G = calculate_gamma(V_in_G, L_G) if V_in_G else None
    gamma_B = calculate_gamma(V_in_B, L_B) if V_in_B else None
    gamma_Gray = calculate_gamma(V_in_Gray, L_Gray) if V_in_Gray else None

    print(f"\nCalculated gamma values:")
    if gamma_R:
        print(f"Red channel gamma: {gamma_R:.4f}")
    if gamma_G:
        print(f"Green channel gamma: {gamma_G:.4f}")
    if gamma_B:
        print(f"Blue channel gamma: {gamma_B:.4f}")
    if gamma_Gray:
        print(f"Grayscale gamma: {gamma_Gray:.4f}")

    # Step 5: Generate Gamma Tables
    print("\n=== Generating Gamma Tables ===")

    # Generate input values
    V_in_full = np.linspace(0, 1, 256)

    # Initialize gamma tables
    gamma_tables = {}

    if gamma_R and gamma_G and gamma_B:
        # Create gamma correction curves for each channel
        V_out_R = V_in_full ** (1 / gamma_R)
        V_out_G = V_in_full ** (1 / gamma_G)
        V_out_B = V_in_full ** (1 / gamma_B)
        gamma_table_RGB = np.column_stack((V_out_R, V_out_G, V_out_B))
        gamma_tables['RGB'] = gamma_table_RGB
        # Save the RGB gamma table
        gamma_table_file_RGB = f'{base_name}_gamma_table_RGB.txt'
        np.savetxt(gamma_table_file_RGB, gamma_table_RGB, fmt='%.6f')
        print(f"RGB gamma table saved to {gamma_table_file_RGB}")

    if gamma_Gray:
        V_out_Gray = V_in_full ** (1 / gamma_Gray)
        gamma_table_Gray = np.column_stack((V_out_Gray, V_out_Gray, V_out_Gray))
        gamma_tables['Grayscale'] = gamma_table_Gray
        # Save the grayscale gamma table
        gamma_table_file_Gray = f'{base_name}_gamma_table_Gray.txt'
        np.savetxt(gamma_table_file_Gray, gamma_table_Gray, fmt='%.6f')
        print(f"Grayscale gamma table saved to {gamma_table_file_Gray}")

    # Optional: Plot the Gamma Curves
    print("\n=== Plotting Gamma Curves ===")

    plt.figure()
    if gamma_R:
        plt.plot(V_in_R, L_R / np.max(L_R), 'ro', label='Red Channel Data')
        plt.plot(V_in_full, V_in_full ** gamma_R, 'r-', label=f'Red Fit (γ={gamma_R:.4f})')
    if gamma_G:
        plt.plot(V_in_G, L_G / np.max(L_G), 'go', label='Green Channel Data')
        plt.plot(V_in_full, V_in_full ** gamma_G, 'g-', label=f'Green Fit (γ={gamma_G:.4f})')
    if gamma_B:
        plt.plot(V_in_B, L_B / np.max(L_B), 'bo', label='Blue Channel Data')
        plt.plot(V_in_full, V_in_full ** gamma_B, 'b-', label=f'Blue Fit (γ={gamma_B:.4f})')
    if gamma_Gray:
        plt.plot(V_in_Gray, L_Gray / np.max(L_Gray), 'ko', label='Grayscale Data')
        plt.plot(V_in_full, V_in_full ** gamma_Gray, 'k-', label=f'Grayscale Fit (γ={gamma_Gray:.4f})')

    plt.xlabel('Normalized Input (V_in)')
    plt.ylabel('Normalized Luminance (L)')
    plt.title('Display Gamma Curves')
    plt.legend()
    plt.grid(True)
    plt.savefig(f"{base_name}.png")

if __name__ == '__main__':
    main()
