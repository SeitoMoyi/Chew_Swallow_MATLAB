clc;
clear;
load("./ProcessedData/EMG_03.mat");
[L_MASS_detected_events, L_MASS_T_high, L_MASS_T_low] = detectEMGEvents(L_MASS_envelope, tEMG, FsEMG, 22835);
[R_MASS_detected_events, R_MASS_T_high, R_MASS_T_low] = detectEMGEvents(R_MASS_envelope, tEMG, FsEMG, 22835);
[L_MYLO_detected_events, L_MYLO_T_high, L_MYLO_T_low] = detectEMGEvents(L_MYLO_envelope, tEMG, FsEMG, 22835);
[R_MYLO_detected_events, R_MYLO_T_high, R_MYLO_T_low] = detectEMGEvents(R_MYLO_envelope, tEMG, FsEMG, 22835);

% L_MASS_extracted_features = extractEMGFeatures(L_MASS_envelope, L_MASS_detected_events, FsEMG);
% R_MASS_extracted_features = extractEMGFeatures(R_MASS_envelope, R_MASS_detected_events, FsEMG);
% L_MYLO_extracted_features = extractEMGFeatures(L_MYLO_envelope, L_MYLO_detected_events, FsEMG);
% R_MYLO_extracted_features = extractEMGFeatures(R_MYLO_envelope, R_MYLO_detected_events, FsEMG);

%% --- Multi-Channel Coincidence Detection (Robust Overlap Method) ---

% Use Left Mylohyoid as the primary channel to search from
confirmed_events_MASS = confirmEvents(L_MASS_detected_events, R_MASS_detected_events);
confirmed_events_MYLO = confirmEvents(L_MYLO_detected_events, R_MYLO_detected_events);
confirmed_events = confirmEvents(confirmed_events_MASS, confirmed_events_MYLO);

plotFigure(tEMG, L_MASS_envelope, confirmed_events, L_MASS_T_high, L_MASS_T_low);

% Extract features for the confirmed events
confirmed_features = extractEMGFeatures(L_MASS_envelope, confirmed_events, FsEMG);

% Method 1: Remove bottom 20% of events by peak amplitude
[filtered_events_v1, filtered_features_v1] = filterLowPeakEvents(confirmed_events, confirmed_features, 'percentile', 20);

% Method 2: Remove events with z-score < -1.5 (more than 1 std below mean)
[filtered_events_v2, filtered_features_v2] = filterLowPeakEvents(confirmed_events, confirmed_features, 'zscore', 1);

% Method 3: Adaptive method (recommended for automatic detection)
[filtered_events_v3, filtered_features_v3] = filterLowPeakEvents(confirmed_events, confirmed_features, 'adaptive');

% Method 4: Absolute threshold (if you know a good minimum value)
% [filtered_events_v4, filtered_features_v4] = filterLowPeakEvents(confirmed_events, confirmed_features, 'absolute', 0.03);

% Use the filtered events for plotting
final_events = filtered_events_v2; % Choose which method you prefer

% Plot original vs filtered results
plotFigure(tEMG, L_MASS_envelope, final_events, L_MASS_T_high, L_MASS_T_low);

function [filtered_events, filtered_features, removed_indices] = filterLowPeakEvents(detected_events, extracted_features, method, threshold_factor)
    % filterLowPeakEvents: Removes events with extremely low peak amplitudes
    %
    % Inputs:
    %   detected_events    - (Mx2 double) Original detected events matrix
    %   extracted_features - (Mx5 double) Features matrix from extractEMGFeatures
    %   method            - (string) Method for filtering: 'percentile', 'zscore', 'iqr', or 'absolute'
    %   threshold_factor  - (double) Threshold parameter (depends on method)
    %
    % Outputs:
    %   filtered_events   - (Nx2 double) Filtered events matrix
    %   filtered_features - (Nx5 double) Filtered features matrix  
    %   removed_indices   - (1xK double) Indices of removed events
    
    if nargin < 3
        method = 'percentile';
    end
    if nargin < 4
        threshold_factor = 25; % Default: remove bottom 25%
    end
    
    % Extract peak amplitudes (column 1 of features)
    peak_amplitudes = extracted_features(:, 1);
    
    % Determine which events to keep based on method
    switch lower(method)
        case 'percentile'
            % Remove events below a certain percentile
            threshold = prctile(peak_amplitudes, threshold_factor);
            keep_indices = peak_amplitudes > threshold;
            fprintf('Percentile method: Removing events with peak < %.4f V (bottom %d%%)\n', threshold, threshold_factor);
            
        case 'zscore'
            % Remove events with z-score below threshold (typically negative)
            z_scores = zscore(peak_amplitudes);
            keep_indices = z_scores > -abs(threshold_factor); % Use negative threshold
            threshold = mean(peak_amplitudes) - abs(threshold_factor) * std(peak_amplitudes);
            fprintf('Z-score method: Removing events with z-score < %.2f (peak < %.4f V)\n', -abs(threshold_factor), threshold);
            
        case 'iqr'
            % Remove outliers using IQR method
            Q1 = prctile(peak_amplitudes, 25);
            Q3 = prctile(peak_amplitudes, 75);
            IQR = Q3 - Q1;
            threshold = Q1 - threshold_factor * IQR; % Usually threshold_factor = 1.5
            keep_indices = peak_amplitudes > threshold;
            fprintf('IQR method: Removing events with peak < %.4f V (Q1 - %.1f*IQR)\n', threshold, threshold_factor);
            
        case 'absolute'
            % Remove events below absolute threshold
            threshold = threshold_factor;
            keep_indices = peak_amplitudes > threshold;
            fprintf('Absolute method: Removing events with peak < %.4f V\n', threshold);
            
        case 'adaptive'
            % Adaptive method based on noise level and signal characteristics
            sorted_peaks = sort(peak_amplitudes, 'descend');
            
            % Find the "knee" point where peak values drop significantly
            if length(sorted_peaks) > 3
                % Calculate differences between consecutive peaks
                peak_diffs = diff(sorted_peaks);
                % Find where the difference suddenly becomes much smaller
                diff_ratios = peak_diffs(1:end-1) ./ peak_diffs(2:end);
                [~, knee_idx] = max(diff_ratios);
                threshold = sorted_peaks(knee_idx + 1) * 0.8; % 80% of knee value
            else
                threshold = median(peak_amplitudes) * 0.5; % Fallback
            end
            
            keep_indices = peak_amplitudes > threshold;
            fprintf('Adaptive method: Removing events with peak < %.4f V (knee-point based)\n', threshold);
            
        otherwise
            error('Unknown method. Use: percentile, zscore, iqr, absolute, or adaptive');
    end
    
    % Apply filtering
    filtered_events = detected_events(keep_indices, :);
    filtered_features = extracted_features(keep_indices, :);
    removed_indices = find(~keep_indices);
    
    % Summary
    num_removed = sum(~keep_indices);
    num_kept = sum(keep_indices);
    fprintf('Filtered results: Kept %d events, removed %d events (%.1f%% removed)\n', ...
            num_kept, num_removed, 100 * num_removed / length(keep_indices));
    
    % Optional: Show statistics
    if num_removed > 0
        fprintf('Removed events had peak range: %.4f - %.4f V\n', ...
                min(peak_amplitudes(~keep_indices)), max(peak_amplitudes(~keep_indices)));
    end
    if num_kept > 0
        fprintf('Kept events have peak range: %.4f - %.4f V\n', ...
                min(peak_amplitudes(keep_indices)), max(peak_amplitudes(keep_indices)));
    end
end

function plotFigure(time_vector, emg_envelope, detected_events, T_high, T_low)
    figure;
    hold on;
    
    % Plot the EMG envelope
    plot(time_vector, emg_envelope, 'b', 'DisplayName', 'EMG Envelope', 'LineWidth', 0.5);
    
    % Plot threshold lines
    yline(T_high, '--r', 'High Threshold', 'LineWidth', 1);
    yline(T_low, '--g', 'Low Threshold', 'LineWidth', 1);
    
    % Plot each detected event with alternating colors
    for k = 1:size(detected_events, 1)
        start_idx = detected_events(k, 1);
        end_idx = detected_events(k, 2);
        
        % Alternate between red and magenta
        if mod(k, 2) == 1
            event_color = 'cyan';  % Red for odd events
        else
            event_color = 'yellow';  % Magenta for even events
        end
        
        % Create display name for legend (only for first event of each color)
        display_name = '';
        if k == 1
            display_name = 'Event Type 1';
        elseif k == 2
            display_name = 'Event Type 2';
        end
        
        % Plot the event segment
        plot(time_vector(start_idx:end_idx), emg_envelope(start_idx:end_idx), ...
             'Color', event_color, 'LineWidth', 1.5, 'DisplayName', display_name);
    end
    
    % Create legend
    h = get(gca, 'Children');
    legend_handles = [];
    legend_labels = {};
    
    for i = 1:length(h)
        if ~isempty(get(h(i), 'DisplayName'))
            legend_handles = [legend_handles; h(i)];
            legend_labels = [legend_labels; {get(h(i), 'DisplayName')}];
        end
    end
    
    if ~isempty(legend_handles)
        legend(legend_handles, legend_labels, 'Location', 'best');
    end
    
    % Labels and formatting
    title('EMG Events Detected via Threshold');
    xlabel('Time (s)');
    ylabel('Amplitude (V)');
    grid on;
    hold off;
    
    % Add event count in subtitle
    if size(detected_events, 1) > 0
        subtitle(sprintf('Total Events Detected: %d', size(detected_events, 1)));
    end
end

function confirmed_events = confirmEvents(events1, events2)
    
    if size(events1, 1) < size(events2, 1)
        primary_events = events1;
        secondary_events = events2;
    else
        primary_events = events2;
        secondary_events = events1;
    end
    confirmed_events = [];

    for i = 1:size(primary_events, 1)
        primary_start_idx = primary_events(i, 1);
        primary_end_idx   = primary_events(i, 2);
        
        max_overlap_length = 0;
        best_match_idx = 0;
        
        % Find the closest secondary event within tolerance
        for j = 1:size(secondary_events, 1)
            secondary_start_idx = secondary_events(j, 1);
            secondary_end_idx   = secondary_events(j, 2);
            current_overlap = max(0, min(primary_end_idx, secondary_end_idx) - max(primary_start_idx, secondary_start_idx));
            
            if current_overlap > max_overlap_length
                max_overlap_length = current_overlap;
                best_match_idx = j;
            end
        end
        
        % If we found a best match, confirm the event
        if best_match_idx > 0
            secondary_start_idx = secondary_events(best_match_idx, 1);
            secondary_end_idx   = secondary_events(best_match_idx, 2);
            
            % Use intersection of the matched events
            overlap_start_idx = mean(primary_start_idx, secondary_start_idx);
            overlap_end_idx = mean(primary_end_idx, secondary_end_idx);
            
            confirmed_events = [confirmed_events; overlap_start_idx, overlap_end_idx];
        end
    end
    
    fprintf('Found %d confirmed events using best-match approach.\n', size(confirmed_events, 1));
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


function [detected_events, T_high, T_low] = detectEMGEvents(emg_envelope, time_vector, Fs, noise_end_index, options)
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
    if ~isfield(options, 'show_plot');     options.show_plot = false;   end
    
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