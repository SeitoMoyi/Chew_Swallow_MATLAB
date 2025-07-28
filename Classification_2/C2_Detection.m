clc;
clear;
load("./ProcessedData/EMG_03.mat");
L_MASS_detected_events = detectEMGEvents(L_MASS_envelope, tEMG, FsEMG, 22835);
R_MASS_detected_events = detectEMGEvents(R_MASS_envelope, tEMG, FsEMG, 22835);
L_MYLO_detected_events = detectEMGEvents(L_MYLO_envelope, tEMG, FsEMG, 22835);
R_MYLO_detected_events = detectEMGEvents(R_MYLO_envelope, tEMG, FsEMG, 22835);

L_MASS_extracted_features = extractEMGFeatures(L_MASS_envelope, L_MASS_detected_events, FsEMG);
R_MASS_extracted_features = extractEMGFeatures(R_MASS_envelope, R_MASS_detected_events, FsEMG);
L_MYLO_extracted_features = extractEMGFeatures(L_MYLO_envelope, L_MYLO_detected_events, FsEMG);
R_MYLO_extracted_features = extractEMGFeatures(R_MYLO_envelope, R_MYLO_detected_events, FsEMG);

%% --- Multi-Channel Coincidence Detection (Robust Overlap Method) ---

% Use Left Mylohyoid as the primary channel to search from
confirmed_events_L = confirmEvents(L_MYLO_detected_events, L_MASS_detected_events, tEMG);
confirmed_events_R = confirmEvents(R_MYLO_detected_events, R_MASS_detected_events, tEMG);
confirmed_events = confirmEvents(confirmed_events_L, confirmed_events_R, tEMG);

function confirmed_events = confirmEvents(primary_events, secondary_events, tEMG)

    confirmed_events = [];

    % Loop through each event detected on the primary channel
    for i = 1:size(primary_events, 1)
        
        % Get the start and end times of the primary event
        primary_start_time = tEMG(primary_events(i, 1));
        primary_end_time   = tEMG(primary_events(i, 2));
        
        % Search for an overlapping event in the secondary channel's list
        for j = 1:size(secondary_events, 1)
            
            secondary_start_time = tEMG(secondary_events(j, 1));
            secondary_end_time   = tEMG(secondary_events(j, 2));
            
            % --- Robust Overlap Check ---
            % Check if the two event intervals overlap in time
            if (primary_start_time <= secondary_end_time) && (secondary_start_time <= primary_end_time)
                
                % Coincidence confirmed! This is a high-confidence swallow.
                % We'll use the primary event's timing for our master list.
                confirmed_events = [confirmed_events; primary_events(i, :)];
                
                % Break the inner loop and move to the next primary event
                break; 
            end
        end
    end
    
    fprintf('Found %d raw candidates on Left Mylohyoid.\n', size(primary_events, 1));
    fprintf('Found %d confirmed swallows on the Left side after robust overlap check.\n', size(confirmed_events, 1));
end

function extracted_features = extractEMGFeatures(emg_envelope, detected_events, Fs)
    % extractEMGFeatures: Calculates descriptive features for each detected EMG event.
    %
    % Inputs:
    %   emg_envelope    - (1xN double) The processed EMG envelope signal.
    %   detected_events - (Mx2 double) Matrix of event start and end indices from the detector.
    %   Fs              - (double) The sampling frequency of the signal in Hz.
    %
    % Outputs:
    %   extracted_features - (Mx5 double) A matrix where each row is an event and columns are features:
    %                       Col 1: Peak Amplitude (V)
    %                       Col 2: Duration (s)
    %                       Col 3: Integrated EMG / Area (V*s)
    %                       Col 4: Mean Amplitude (V)
    %                       Col 5: Root Mean Square (RMS)
    
    % --- 1. Pre-allocate matrix for speed ---
    num_events = size(detected_events, 1);
    num_features = 5; % We are calculating 5 features
    extracted_features = zeros(num_events, num_features);
    
    % --- 2. Loop through each event and calculate features ---
    for i = 1:num_events
        % Get the start and end index for the current event
        start_idx = detected_events(i, 1);
        end_idx = detected_events(i, 2);
        
        % Isolate the signal segment for this event
        event_segment = emg_envelope(start_idx:end_idx);
        
        % --- Calculate Features ---
        % 1. Peak Amplitude
        peak_amp = max(event_segment);
        
        % 2. Duration in seconds
        duration_s = (end_idx - start_idx + 1) / Fs;
        
        % 3. Integrated EMG (Area under the curve)
        integrated_emg = sum(event_segment) / Fs;
        
        % 4. Mean Amplitude
        mean_amp = mean(event_segment);
        
        % 5. Root Mean Square (RMS)
        rms_val = rms(event_segment);
        
        % --- Store features in the output matrix ---
        extracted_features(i, :) = [peak_amp, duration_s, integrated_emg, mean_amp, rms_val];
    end

end


function detected_events = detectEMGEvents(emg_envelope, time_vector, Fs, noise_end_index, options)
    % detectEMGEvents: Detects events in an EMG envelope using a double-threshold method with a duration constraint.
    %
    % Syntax:
    %   detected_events = detectEMGEvents(emg_envelope, time_vector, Fs, noise_end_index, options)
    %
    % Inputs:
    %   emg_envelope      - (1xN double) The processed EMG envelope signal.
    %   time_vector       - (1xN double) The corresponding time vector for plotting.
    %   Fs                - (double) The sampling frequency of the signal in Hz.
    %   noise_end_index   - (integer) The sample index where the baseline noise period ends.
    %   options           - (struct) A structure with optional parameters:
    %       .high_factor  - (double) Multiplier for std dev for the high threshold. Default: 5.
    %       .low_factor   - (double) Multiplier for std dev for the low threshold. Default: 2.
    %       .min_duration - (double) Minimum event duration in seconds. Default: 0.05.
    %       .show_plot    - (logical) Set to true to display a plot of the results. Default: true.
    %
    % Outputs:
    %   detected_events   - (Mx2 double) A matrix where each row is a detected event,
    %                       with column 1 as the start index and column 2 as the end index.
    
    % --- 1. Set Default Parameters ---
    if nargin < 5; options = struct(); end
    
    if ~isfield(options, 'high_factor');   options.high_factor = 3;    end
    if ~isfield(options, 'low_factor');    options.low_factor = 1.5;     end
    if ~isfield(options, 'min_duration');  options.min_duration = 0.7;  end
    if ~isfield(options, 'show_plot');     options.show_plot = true;   end
    
    % --- 2. Setup and Calculations ---
    min_duration_samples = round(options.min_duration * Fs);
    
    noise_segment = emg_envelope(1:noise_end_index);
    mean_noise = mean(noise_segment);
    std_noise = std(noise_segment);
    
    T_high = mean_noise + (options.high_factor * std_noise);
    T_low = mean_noise + (options.low_factor * std_noise);
    
    % --- 3. Core Detection Logic ---
    detected_events = [];
    in_event = false;
    event_start_index = 0;
    
    for i = 1:length(emg_envelope)
        if ~in_event
            if emg_envelope(i) > T_high
                in_event = true;
                event_start_index = i;
            end
        else
            if emg_envelope(i) < T_low
                event_duration = i - event_start_index;
                if event_duration >= min_duration_samples
                    detected_events = [detected_events; event_start_index, i - 1];
                end
                in_event = false;
            end
        end
    end
    
    if in_event
        event_duration = length(emg_envelope) - event_start_index;
        if event_duration >= min_duration_samples
            detected_events = [detected_events; event_start_index, length(emg_envelope)];
        end
    end
    
    % --- 4. Visualization ---
    if options.show_plot
        figure;
        hold on;
        
        plot(time_vector, emg_envelope, 'b', 'DisplayName', 'EMG Envelope');
        yline(T_high, '--r', ['High Threshold (', num2str(options.high_factor), 'σ)'], 'LineWidth', 1.5);
        yline(T_low, '--g', ['Low Threshold (', num2str(options.low_factor), 'σ)'], 'LineWidth', 1.5);
        
        for k = 1:size(detected_events, 1)
            start_idx = detected_events(k, 1);
            end_idx = detected_events(k, 2);
            plot(time_vector(start_idx:end_idx), emg_envelope(start_idx:end_idx), 'r', 'LineWidth', 2, 'DisplayName', 'Detected Event');
        end
        
        h = get(gca,'Children');
        if ~isempty(h)
            legend([h(end), h(end-2), h(1)]);
        end
        
        title('EMG Events Detected via Double-Threshold');
        xlabel('Time (s)');
        ylabel('Amplitude (V)');
        grid on;
        hold off;
    end

end