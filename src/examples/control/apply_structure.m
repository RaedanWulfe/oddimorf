% -----------------------------------------------------------------------------
% Load reader memory map file for incoming data
function [mm_header] = apply_structure()
    mm_header = ...
        memmapfile(strcat('_Control.dat'), ...
        'Format', {...
            'uint8' double([1 254]) 'textbox0'; ...
            'uint8' double([2 1]) 'togglegroup0'; ...
            'int64' double([1 1]) 'radiogroup0'; ...
            'int64' double([1 1]) 'slider0'; ...
            }, ...
        'Repeat', 1, ...
        'Writable', false);
    % -------------------------------------------------------------------------
end
