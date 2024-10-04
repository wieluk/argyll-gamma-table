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
pause(30)

% Restore original gamma table
Screen('LoadNormalizedGammaTable', windowPtr, oldTable);
Screen('CloseAll');