clc;
clear;
load('./SegmentedData/IndividualSegments.mat');
% Assign your actual data structure to emg_class
emg_class = purse_lips_3;

% Define your sections (use cell array for strings)
sections = {'masseter', 'temporalis', 'mylohyoid'};

% Create a single figure for all subplots
figure('Name', 'EMG Envelope Analysis');

% Loop through each section to create a subplot for each
for i = 1:length(sections)

    % Select the current subplot for plotting
    % subplot(rows, columns, plot_number)
    subplot(3, 1, i);

    % Get the current section name
    currentSection = sections{i};

    % Construct the full field name dynamically for the envelope data
    fieldName = strcat(currentSection, '_envelope');

    % Access the EMG envelope data for the current section
    emg_data = emg_class.emg.(fieldName);

    % Calculate the threshold (mean + 1 * standard deviation)
    threshold = mean(emg_data) + 3 * std(emg_data);

    % Plot the EMG envelope data
    plot(emg_class.time, emg_data, 'b-', 'DisplayName', 'EMG Envelope');
    hold on; % Keep the current plot active to add more elements

    % Find the indices where the EMG signal crosses the threshold from below
    % This identifies points where the signal was below threshold and then becomes
    % at or above the threshold in the next sample.
    start_indices = find(emg_data(1:end-1) < threshold & emg_data(2:end) >= threshold) + 1;

    % Get the time points corresponding to these starting indices
    start_times = emg_class.time(start_indices);

    % Draw vertical lines at each identified start point
    % These lines extend from the minimum to the maximum of the current EMG data
    for j = 1:length(start_times)
        plot([start_times(j), start_times(j)], [min(emg_data), max(emg_data)], 'r--', 'DisplayName', 'Signal Start Points');
    end

    % Draw a horizontal line for the calculated threshold
    plot(emg_class.time, repmat(threshold, size(emg_class.time)), 'g-.', 'DisplayName', 'EMG Threshold');

    hold off; % Release the hold on the subplot

    % Add labels and title specific to the current subplot
    xlabel('Time (s)');
    ylabel('EMG Envelope Amplitude');
    title(sprintf('%s EMG Envelope with Signal Start Points', upper(currentSection))); % Dynamic title

    % Add a legend for the current subplot
    % 'Location', 'best' tries to find the best spot for the legend
    % legend('show', 'Location', 'best');
    grid on; % Add a grid for better readability
end