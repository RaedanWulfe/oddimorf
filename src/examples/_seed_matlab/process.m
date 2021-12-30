% -----------------------------------------------------------------------------
% Load control memory file
control_mm = ...
    memmapfile('_Control.dat', ...
    'Format', {...
        'int32' double([1 1]) 'is_terminated'; ...
        'int32' double([1 1]) 'header_size'; ...
        'uint64' double([1 1]) 'timestamp'; ...
        % TODO: Define control fields
        }, ...
    'Repeat', 1, ...
    'Writable', false);

% -----------------------------------------------------------------------------
% Load reader memory map file for incoming data
incoming_mm_header = ...
    memmapfile('_TodoInc.dat', ...
    'Format', {...
        'int64' double([1 1]) 'max_size_bytes'; ...
        'int64' double([1 1]) 'element_size_bytes'; ...
        'int64' double([1 1]) 'write_head'; ...
        'uint64' double([1 1]) 'start_time'; ...
        'single' double([1 2]) 'sensor_origin'; ...
        'uint64' double([1 1]) 'rotation_time_msec'; ...
        }, ...
    'Repeat', 1, ...
    'Writable', false);
% ---
incoming_end_index = int64(incoming_mm_header.Data(1).max_size_bytes / incoming_mm_header.Data(1).element_size_bytes);
incoming_read_head = 1;
incoming_write_head = 1;
incoming_read_block_bounds = [[0, 0]; [0, 0]];
% ---
incoming_mm_data = ...
    memmapfile('_TodoInc.dat', ...
    'Format', {...
        % TODO: Define field structure of the incoming data
        }, ...
    'Offset', control_mm.Data(1).header_size, ...
    'Repeat', incoming_end_index, ...
    'Writable', false);

% -----------------------------------------------------------------------------
% Load writer memory map file for outgoing TODO data
todo_mm_header = ...
    memmapfile('_TodoOut.dat', ...
    'Format', {...
        'int64' double([1 1]) 'max_size_bytes'; ...
        'int64' double([1 1]) 'element_size_bytes'; ...
        'int64' double([1 1]) 'write_head'; ...
        'uint64' double([1 1]) 'start_time'; ...
        'single' double([1 2]) 'sensor_origin'; ...
        'uint64' double([1 1]) 'rotation_time_msec'; ...
        }, ...
    'Repeat', 1, ...
    'Writable', true);
% ---
todo_end_index = int64(todo_mm_header.Data(1).max_size_bytes / todo_mm_header.Data(1).element_size_bytes);
todo_write_head = 1;
todo_write_block_bounds = [[0, 0]; [0, 0]];
% ---
todo_mm_data = ...
    memmapfile('_TodoOut.dat', ...
    'Format', {...
        % TODO: Define field structure of the outgoing data
        }, ...
    'Offset', control_mm.Data(1).header_size, ...
    'Repeat', 1, ...
    'Writable', true);

% -----------------------------------------------------------------------------
% Preset common parameters and structures
interpreted_data = zeros([7, incoming_end_index]);
is_terminated = control_mm.Data(1).is_terminated;
origin_latitude = incoming_mm_header.Data(1).sensor_origin(1);
origin_longitude = incoming_mm_header.Data(1).sensor_origin(2);
[r1, r2, w1, w2] = deal(0, 0, 0, 0);

% -----------------------------------------------------------------------------
% Primary processing loop
while ~is_terminated
    % Terminate the primary processing loop if the requisite control flag is set
    if control_mm.Data(1).is_terminated
        disp('Matlab process ended.');
        is_terminated = true;
        break
    end

    % Determine the last write index of the incoming struct data
    incoming_write_head = int64((incoming_mm_header.Data(1).write_head / incoming_mm_header.Data(1).element_size_bytes) + 1);
    % If no new data, sleep for 100ms and then try another run of the loop
    if incoming_read_head == incoming_write_head
        pause(0.1)
        continue
    end

    % Set up the read blocks for the incoming data, splitting the read in two if the buffer wraps
    if incoming_read_head < incoming_write_head
        incoming_read_block_bounds = int64([[incoming_read_head, incoming_write_head]; [1, 1]]);
    else
        incoming_read_block_bounds = int64([[incoming_read_head, incoming_end_index]; [1, incoming_write_head]]);
    end

    % Parse the blocks of incoming data
    for incoming_read_block_index = 1:2
        r1 = incoming_read_block_bounds(incoming_read_block_index, 1);
        r2 = incoming_read_block_bounds(incoming_read_block_index, 2);
        if (~control_mm.Data(1).is_terminated) & (r1 ~= r2)
            read_range = r1:r2;
            % TODO: Data field interpretation
            % interpreted_data(0, read_range) = arrayfun(@(x) ...
            %    uint64(x.todo), ...
            %    incoming_mm_data.Data(read_range, 1));
            % Determine the write blocks to allow for full write, wrapping around if necessary,
            % NOTE: Will skip if the range exceeds the current buffer max
            if r2 - r1 > todo_end_index
                disp("Over max.");
                continue;
            elseif todo_write_head + (r2 - r1) < todo_end_index
                todo_write_block_bounds = int64([[todo_write_head, todo_write_head + (r2 - r1)]; [1, 1]]);
            else
                todo_write_block_bounds = int64([[todo_write_head, todo_end_index]; [1, todo_write_head + (r2 - r1) - todo_end_index]]);
            end

            % TODO: Additional logic to implement per read block

            incoming_read_head = incoming_read_block_bounds(incoming_read_block_index, 2);

        end

        % TODO: Additional logic to implement in full stage with all data

    end

end

% -----------------------------------------------------------------------------