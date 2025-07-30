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