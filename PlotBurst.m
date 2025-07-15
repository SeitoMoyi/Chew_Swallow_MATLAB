figure;
% Calculate the threshold
emg_class = cdswallow_3;
emg_data = emg_class.emg.masseter_envelope;
threshold = mean(emg_data) + 3 * std(emg_data);
plot(emg_class.time, emg_data);

% Find the indices where the EMG signal crosses the threshold from below
% We're looking for points where the signal is below the threshold, and the next point is above or equal to the threshold.
start_indices = find(emg_data(1:end-1) < threshold & emg_data(2:end) >= threshold) + 1;

% Get the time points corresponding to the starting indices
start_times = emg_class.time(start_indices);

% Get the y-values where the lines should be drawn (the threshold value)
y_values = repmat(threshold, size(start_times));

% Draw vertical lines at each starting point
hold on; % Keep the existing plot
for i = 1:length(start_times)
    plot([start_times(i), start_times(i)], [min(emg_data), max(emg_data)], 'r--'); % Red dashed vertical lines
end

% Optionally, draw a horizontal line for the threshold itself
plot(emg_class.time, repmat(threshold, size(emg_class.time)), 'g-.', 'DisplayName', 'EMG Threshold');

hold off; % Release the hold on the figure

% Add labels and title for clarity
xlabel('Time');
ylabel('Masseter EMG Envelope');
title('Masseter EMG Envelope with Signal Start Points');
legend('EMG Envelope', 'Signal Start Points', 'EMG Threshold'); % Update legend to include new lines