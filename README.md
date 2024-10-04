# Gamma Calibration Script with Photometer and ArgyllCMS

Calibrate your monitor's gamma using a photometer and ArgyllCMS to generate gamma correction tables compatible with Psychtoolbox.

## Prerequisites

### 1. Install ArgyllCMS

**Ubuntu:**

```bash
sudo apt-get install argyll
```

**Other OS:**

Download from [ArgyllCMS Installation Guide](https://www.argyllcms.com/doc/Installing.html).

### 2. Verify Installation

Ensure ArgyllCMS is in your PATH:

```bash
dispwin -?
```

### 3. Install Python Packages

With Python 3 installed:

```bash
pip3 install numpy scipy matplotlib
```

## Running the Script

1. **Start the Script**

```bash
python3 photometer_gamma_table.py
```

2. **Follow Prompts**

   - **Enter Base Name:** e.g., `calibration_session1`.
   - **Select Display Device:** Choose from listed options.
   - **Set Number of Patches:**
     - Grayscale patches (e.g., `64`, or `0` to skip).
     - Color patches per channel (e.g., `64`, or `0` to skip).
     - At least one must be greater than zero.
3. **Calibrate the Photometer (for colormunki photo)**

   1. **Calibration Mode:**

   - Place the photometer sensor face down, button facing you.
   - Set to **calibration mode** (bottom-left position).
4. **Switch to Measurement Mode**

   - Set to **measurement mode** (bottom-middle position).
5. **Measure Test Patches**

   - Follow on-screen instructions.
   - Position sensor against the monitor.
6. **Complete Calibration**

   - Wait for processing to finish.
   - Files saved in a directory named after your base name and display number.

## Using Gamma Tables in Psychtoolbox

Example MATLAB/Octave code:

```matlab
% Load gamma table
gammaTable = load('path_to_gamma_table.txt');

% Open window
screenNumber = max(Screen('Screens'));
[windowPtr, ~] = Screen('OpenWindow', screenNumber);

% Apply gamma table
[oldTable, success] = Screen('LoadNormalizedGammaTable', windowPtr, gammaTable);

% Check success
if success
    disp('Gamma table loaded successfully.');
else
    disp('Failed to load gamma table.');
end

% ... Your experiment code ...

% Restore original gamma table
Screen('LoadNormalizedGammaTable', windowPtr, oldTable);
Screen('CloseAll');
```

Refer to [Psychtoolbox documentation](http://psychtoolbox.org/docs/Screen-LoadNormalizedGammaTable) for details.
