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