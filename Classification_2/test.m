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
processing_options.interval_zscore = 1.7;         % Remove events with interval z-score < -1.0
processing_options.verbose = true;

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