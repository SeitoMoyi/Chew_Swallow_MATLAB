% === SIMPLIFIED WORKFLOW ===
clc;
clear;
load("./ProcessedData/EMG_03.mat");

% Step 1: Detect events and get thresholds
[L_MASS_detected_events, L_MASS_T_high, L_MASS_T_low] = detectEMGEvents(L_MASS_envelope, tEMG, FsEMG, 22835);
[R_MASS_detected_events, R_MASS_T_high, R_MASS_T_low] = detectEMGEvents(R_MASS_envelope, tEMG, FsEMG, 22835);
[L_MYLO_detected_events, L_MYLO_T_high, L_MYLO_T_low] = detectEMGEvents(L_MYLO_envelope, tEMG, FsEMG, 22835);
[R_MYLO_detected_events, R_MYLO_T_high, R_MYLO_T_low] = detectEMGEvents(R_MYLO_envelope, tEMG, FsEMG, 22835);

% Step 2: Confirm events using overlap method
confirmed_events_MASS = confirmEvents(L_MASS_detected_events, R_MASS_detected_events);
confirmed_events_MYLO = confirmEvents(L_MYLO_detected_events, R_MYLO_detected_events);
confirmed_events = confirmEvents(confirmed_events_MASS, confirmed_events_MYLO);

% Step 3: Process events with unified function (replaces extractEMGFeatures + filtering)
processing_options = struct();
processing_options.filter_low_peaks = true;
processing_options.peak_zscore_threshold = 1;  % Remove events with peak z-score < -1.5
processing_options.filter_close_events = true;
processing_options.interval_method = 'peak_to_peak';
processing_options.interval_zscore = 1;         % Remove events with interval z-score < -1.0
processing_options.verbose = true;
processing_options.plot_intermediate = false;      % NEW: Enable intermediate plotting

[final_events, final_features, stats] = processEMGEvents(L_MASS_envelope, confirmed_events, FsEMG, processing_options);

% Step 4: Visualize results
figure('Position', [100, 100, 1200, 800]);

% --- Plot 1: Before Processing ---
subplot(2,1,1);
hold on;

% Plot EMG envelope
plot(tEMG, L_MASS_envelope, 'b', 'DisplayName', 'EMG Envelope', 'LineWidth', 0.5);

% Plot threshold lines
yline(L_MASS_T_high, '--r', 'High Threshold', 'LineWidth', 1);
yline(L_MASS_T_low, '--g', 'Low Threshold', 'LineWidth', 1);

% Plot events with alternating colors
for k = 1:size(confirmed_events, 1)
    start_idx = confirmed_events(k, 1);
    end_idx = confirmed_events(k, 2);
    
    % Alternate colors
    if mod(k, 2) == 1
        event_color = 'cyan';
    else
        event_color = 'yellow';
    end
    
    % Create display name for legend (only for first event of each color)
    display_name = '';
    if k == 1
        display_name = 'Event Type 1';
    elseif k == 2
        display_name = 'Event Type 2';
    end
    
    plot(tEMG(start_idx:end_idx), L_MASS_envelope(start_idx:end_idx), ...
         'Color', event_color, 'LineWidth', 1.5, 'DisplayName', display_name);
end

% Formatting
title(sprintf('Before Processing (%d events)', size(confirmed_events, 1)));
xlabel('Time (s)');
ylabel('Amplitude (V)');
grid on;
% legend('Location', 'best');
hold off;

% --- Plot 2: After Processing ---
subplot(2,1,2);
hold on;

% Plot EMG envelope
plot(tEMG, L_MASS_envelope, 'b', 'DisplayName', 'EMG Envelope', 'LineWidth', 0.5);

% Plot threshold lines
yline(L_MASS_T_high, '--r', 'High Threshold', 'LineWidth', 1);
yline(L_MASS_T_low, '--g', 'Low Threshold', 'LineWidth', 1);

% Plot final events with alternating colors
for k = 1:size(final_events, 1)
    start_idx = final_events(k, 1);
    end_idx = final_events(k, 2);
    
    % Alternate colors
    if mod(k, 2) == 1
        event_color = 'cyan';
    else
        event_color = 'yellow';
    end
    
    % Create display name for legend (only for first event of each color)
    display_name = '';
    if k == 1
        display_name = 'Event Type 1';
    elseif k == 2
        display_name = 'Event Type 2';
    end
        
    plot(tEMG(start_idx:end_idx), L_MASS_envelope(start_idx:end_idx), ...
         'Color', event_color, 'LineWidth', 1.5, 'DisplayName', display_name);
end

% Formatting
title(sprintf('After Processing (%d events, %.1f%% removed)', size(final_events, 1), stats.removal_rate));
xlabel('Time (s)');
ylabel('Amplitude (V)');
grid on;
% legend('Location', 'best');
hold off;

% Optional: Access extended features
if ~isempty(final_features)
    fprintf('\n=== EXTENDED FEATURES AVAILABLE ===\n');
    fprintf('Columns: [Peak_Amp, Duration, Integrated_EMG, Mean_Amp, RMS, Peak_Idx, Interval, Peak_ZScore, Interval_ZScore]\n');
    fprintf('Example - First event features:\n');
    fprintf('  Peak amplitude: %.4f V (z-score: %.2f)\n', final_features(1,1), final_features(1,8));
    fprintf('  Duration: %.3f s\n', final_features(1,2));
    if ~isnan(final_features(1,7))
        fprintf('  Interval to next: %.3f s (z-score: %.2f)\n', final_features(1,7), final_features(1,9));
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

function [final_events, final_features, processing_stats] = processEMGEvents(emg_envelope, detected_events, Fs, options)
    % Set default options
    if nargin < 4; options = struct(); end
    if ~isfield(options, 'filter_low_peaks');      options.filter_low_peaks = true; end
    if ~isfield(options, 'peak_zscore_threshold'); options.peak_zscore_threshold = 1.5; end
    if ~isfield(options, 'filter_close_events');   options.filter_close_events = true; end
    if ~isfield(options, 'interval_method');       options.interval_method = 'peak_to_peak'; end
    if ~isfield(options, 'interval_zscore');       options.interval_zscore = 1.5; end
    if ~isfield(options, 'verbose');               options.verbose = true; end
    if ~isfield(options, 'plot_intermediate');     options.plot_intermediate = false; end
    
    % Initialize stats
    processing_stats = struct();
    processing_stats.original_count = size(detected_events, 1);
    
    if options.verbose
        fprintf('\n=== EMG EVENT PROCESSING ===\n');
        fprintf('Starting with %d detected events\n', processing_stats.original_count);
    end
    
    if size(detected_events, 1) == 0
        final_events = [];
        final_features = [];
        return;
    end
    
    % === STEP 1: Extract All Features ===
    if options.verbose; fprintf('\nStep 1: Extracting features...\n'); end
    
    num_events = size(detected_events, 1);
    all_features = zeros(num_events, 9);
    
    for i = 1:num_events
        start_idx = detected_events(i, 1);
        end_idx = detected_events(i, 2);
        event_segment = emg_envelope(start_idx:end_idx);
        
        % Basic features
        peak_amp = max(event_segment);
        duration_s = (end_idx - start_idx + 1) / Fs;
        integrated_emg = sum(event_segment) / Fs;
        mean_amp = mean(event_segment);
        rms_val = rms(event_segment);
        
        % Peak index
        [~, local_peak_idx] = max(event_segment);
        peak_idx = start_idx + local_peak_idx - 1;
        
        all_features(i, 1:6) = [peak_amp, duration_s, integrated_emg, mean_amp, rms_val, peak_idx];
    end
    
    % Calculate intervals (in samples - no need to convert to time for comparisons)
    if num_events > 1
        switch lower(options.interval_method)
            case 'peak_to_peak'
                intervals = diff(all_features(:, 6)); % Peak-to-peak in samples
            case 'end_to_start'
                intervals = detected_events(2:end, 1) - detected_events(1:end-1, 2); % Gap in samples
            case 'start_to_start'
                intervals = diff(detected_events(:, 1)); % Start-to-start in samples
        end
        all_features(1:end-1, 7) = intervals / Fs; % Store in seconds for user reference
    end
    
    % Calculate z-scores for peaks only
    all_features(:, 8) = zscore(all_features(:, 1)); % Peak amplitude z-scores
    
    % === STEP 2: Filter by Peak Z-Score ===
    keep_indices = true(num_events, 1);
    
    if options.filter_low_peaks && num_events > 1
        if options.verbose; fprintf('\nStep 2: Filtering low peak events...\n'); end
        
        peak_keep = all_features(:, 8) > -options.peak_zscore_threshold;
        keep_indices = keep_indices & peak_keep;
        
        processing_stats.after_peak_filter = sum(keep_indices);
        
        if options.verbose
            fprintf('  Removed %d events with peak z-score < %.1f\n', sum(~peak_keep), -options.peak_zscore_threshold);
        end
        
        % === NEW: Plot intermediate results after peak filtering ===
        if options.plot_intermediate
            plotIntermediateResults(emg_envelope, detected_events, keep_indices, Fs, ...
                'After Peak Filtering', processing_stats.after_peak_filter);
        end
        
        % === NEW: Recalculate intervals and interval z-scores after peak filtering ===
        if sum(keep_indices) > 1
            % Extract the events that passed peak filtering
            filtered_events = detected_events(keep_indices, :);
            filtered_features = all_features(keep_indices, :);
            
            % Recalculate intervals based on the filtered events
            num_filtered_events = size(filtered_events, 1);
            switch lower(options.interval_method)
                case 'peak_to_peak'
                    raw_intervals = diff(filtered_features(:, 6)); % Peak-to-peak in samples
                case 'end_to_start'
                    raw_intervals = filtered_events(2:end, 1) - filtered_events(1:end-1, 2); % Gap in samples
                case 'start_to_start'
                    raw_intervals = diff(filtered_events(:, 1)); % Start-to-start in samples
            end
            
            % Update the interval column in all_features (only for the kept events)
            all_features(keep_indices, 7) = [raw_intervals / Fs; NaN]; % Store in seconds, last event has no interval
            
            % Recalculate interval z-scores
            if num_filtered_events > 2
                interval_zscores = zscore(raw_intervals);
                % Update the interval z-score column in all_features (only for the kept events that have an interval)
                % Note: The last event doesn't have an interval, so we don't update its z-score
                kept_indices_with_interval = find(keep_indices);
                kept_indices_with_interval = kept_indices_with_interval(1:end-1); % Exclude last event
                all_features(kept_indices_with_interval, 9) = interval_zscores;
            end
        end
    else
        processing_stats.after_peak_filter = processing_stats.original_count;
    end
    
    % === STEP 3: Filter by Interval Z-Score ===
    if options.filter_close_events && sum(keep_indices) > 1
        if options.verbose; fprintf('\nStep 3: Filtering close events...\n'); end
        
        % Work with currently kept events
        temp_indices = find(keep_indices);
        temp_features = all_features(keep_indices, :);
        
        if size(temp_features, 1) > 2
            % Find events with abnormally short intervals
            interval_zscores = temp_features(:, 9);
            temp_keep = true(size(temp_features, 1), 1);
            
            % Check each interval (except the last event which has no interval)
            for i = 1:size(temp_features, 1)-1
                if ~isnan(interval_zscores(i)) && interval_zscores(i) < -options.interval_zscore
                    % Interval from event i to event i+1 is too short
                    % Remove the SECOND event (i+1) to keep the first in the cluster
                    temp_keep(i+1) = false;
                    if options.verbose
                        fprintf('  Removing event %d: interval z-score %.2f < %.1f\n', ...
                                i+1, interval_zscores(i), -options.interval_zscore);
                    end
                end
            end
            
            % Update keep_indices
            final_keep_indices = false(size(keep_indices));
            final_keep_indices(temp_indices(temp_keep)) = true;
            keep_indices = final_keep_indices;
            
            num_removed_by_interval = sum(~temp_keep);
            if options.verbose && num_removed_by_interval == 0
                fprintf('  No events removed by interval filtering\n');
            end
        end
    end
    
    processing_stats.final_count = sum(keep_indices);
    processing_stats.total_removed = processing_stats.original_count - processing_stats.final_count;
    processing_stats.removal_rate = 100 * processing_stats.total_removed / processing_stats.original_count;
    
    % === FINAL RESULTS ===
    final_events = detected_events(keep_indices, :);
    final_features = all_features(keep_indices, :);
    
    if options.verbose
        fprintf('\n=== PROCESSING SUMMARY ===\n');
        fprintf('Original events: %d\n', processing_stats.original_count);
        if options.filter_low_peaks
            fprintf('After peak filtering: %d\n', processing_stats.after_peak_filter);
        end
        fprintf('Final events: %d\n', processing_stats.final_count);
        fprintf('Total removal rate: %.1f%%\n', processing_stats.removal_rate);
        
        if processing_stats.final_count > 0
            fprintf('\nFinal event statistics:\n');
            fprintf('  Peak amplitude: %.4f ± %.4f V\n', mean(final_features(:, 1)), std(final_features(:, 1)));
            fprintf('  Duration: %.2f ± %.2f s\n', mean(final_features(:, 2)), std(final_features(:, 2)));
            if processing_stats.final_count > 1 && any(~isnan(final_features(:, 7)))
                valid_intervals = final_features(~isnan(final_features(:, 7)), 7);
                if ~isempty(valid_intervals)
                    fprintf('  Inter-event intervals: %.2f ± %.2f s\n', mean(valid_intervals), std(valid_intervals));
                end
            end
        end
    end
end

function plotIntermediateResults(emg_envelope, detected_events, keep_indices, Fs, title_str, event_count)
    % Plot intermediate results after peak filtering
    % Create time vector
    t = (0:length(emg_envelope)-1)/Fs;
    
    % Create new figure
    figure('Position', [100, 100, 1200, 400]);
    hold on;
    
    % Plot EMG envelope
    plot(t, emg_envelope, 'b', 'DisplayName', 'EMG Envelope', 'LineWidth', 0.5);
    
    % Plot events with different colors for kept/removed events
    for k = 1:size(detected_events, 1)
        start_idx = detected_events(k, 1);
        end_idx = detected_events(k, 2);
        
        if keep_indices(k)
            % Kept events - green
            event_color = 'green';
            display_name = '';
            if k == find(keep_indices, 1)
                display_name = 'Kept Events';
            end
        else
            % Removed events - red
            event_color = 'red';
            display_name = '';
            if k == find(~keep_indices, 1)
                display_name = 'Removed Events';
            end
        end
        
        plot(t(start_idx:end_idx), emg_envelope(start_idx:end_idx), ...
             'Color', event_color, 'LineWidth', 1.5, 'DisplayName', display_name);
    end
    
    % Formatting
    title(sprintf('%s (%d events)', title_str, event_count));
    xlabel('Time (s)');
    ylabel('Amplitude (V)');
    grid on;
    legend('Location', 'best');
    hold off;
end