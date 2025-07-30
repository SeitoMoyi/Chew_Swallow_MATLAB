function [final_events, final_features, processing_stats] = processEMGEvents(emg_envelope, detected_events, Fs, options)
    % processEMGEvents: Unified function for feature extraction and z-score filtering
    %
    % Inputs:
    %   emg_envelope    - (1xN double) The processed EMG envelope signal
    %   detected_events - (Mx2 double) Matrix of event start and end indices
    %   Fs              - (double) Sampling frequency in Hz
    %   options         - (struct) Processing options:
    %       .filter_low_peaks      - (logical) Enable peak amplitude filtering (default: true)
    %       .peak_zscore_threshold - (double) Z-score threshold for peaks (default: 1.5)
    %       .filter_close_events   - (logical) Enable interval filtering (default: true)
    %       .interval_method       - (string) 'peak_to_peak', 'end_to_start' (default: 'peak_to_peak')
    %       .interval_zscore       - (double) Z-score threshold for intervals (default: 1.5)
    %       .verbose               - (logical) Show detailed output (default: true)
    %
    % Outputs:
    %   final_events      - (Nx2 double) Filtered events matrix
    %   final_features    - (Nx9 double) Extended features matrix:
    %                       Col 1: Peak Amplitude (V)
    %                       Col 2: Duration (s)
    %                       Col 3: Integrated EMG (V*s)
    %                       Col 4: Mean Amplitude (V)
    %                       Col 5: RMS (V)
    %                       Col 6: Peak Index (sample)
    %                       Col 7: Interval to Next Event (s)
    %                       Col 8: Peak Z-Score
    %                       Col 9: Interval Z-Score
    %   processing_stats  - (struct) Processing statistics
    
    % Set default options
    if nargin < 4; options = struct(); end
    if ~isfield(options, 'filter_low_peaks');      options.filter_low_peaks = true; end
    if ~isfield(options, 'peak_zscore_threshold'); options.peak_zscore_threshold = 1.5; end
    if ~isfield(options, 'filter_close_events');   options.filter_close_events = true; end
    if ~isfield(options, 'interval_method');       options.interval_method = 'peak_to_peak'; end
    if ~isfield(options, 'interval_zscore');       options.interval_zscore = 1.5; end
    if ~isfield(options, 'verbose');               options.verbose = true; end
    
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
    
    % Calculate z-scores
    all_features(:, 8) = zscore(all_features(:, 1)); % Peak amplitude z-scores
    if num_events > 2
        % Use raw intervals (samples) for z-score calculation - more efficient
        switch lower(options.interval_method)
            case 'peak_to_peak'
                raw_intervals = diff(all_features(:, 6));
            case 'end_to_start'
                raw_intervals = detected_events(2:end, 1) - detected_events(1:end-1, 2);
            case 'start_to_start'
                raw_intervals = diff(detected_events(:, 1));
        end
        
        if length(raw_intervals) > 1
            interval_zscores = zscore(raw_intervals);
            all_features(1:length(interval_zscores), 9) = interval_zscores;
        end
    end
    
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