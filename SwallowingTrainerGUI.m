function SwallowingTrainerGUI()
    % Create main figure
    fig = figure('Name', 'Swallowing Trainer', ...
                 'NumberTitle', 'off', ...
                 'Position', [100, 100, 400, 700], ...
                 'MenuBar', 'none', ...
                 'ToolBar', 'none', ...
                 'Resize', 'off', ...
                 'Color', [0.95, 0.95, 0.95]);
    
    % Store GUI data
    guiData = struct();
    guiData.isRecording = false;
    guiData.sessionCount = 0;
    guiData.currentSwallowType = 'Regular';
    guiData.emgData = [];
    guiData.timeData = [];
    
    % Create UI components
    createHeader(fig, guiData);
    createMainContent(fig, guiData);
    createBottomNav(fig);
    
    % Store GUI data in figure
    guidata(fig, guiData);
end

function createHeader(fig, guiData)
    % Header panel
    headerPanel = uipanel(fig, ...
        'Position', [0, 0.85, 1, 0.15], ...
        'BackgroundColor', [0.2, 0.6, 0.4], ...
        'BorderType', 'none');
    
    % Time display
    uicontrol(headerPanel, ...
        'Style', 'text', ...
        'String', '2:00', ...
        'Position', [20, 40, 80, 30], ...
        'BackgroundColor', [0.2, 0.6, 0.4], ...
        'ForegroundColor', 'white', ...
        'FontSize', 20, ...
        'FontWeight', 'bold', ...
        'HorizontalAlignment', 'left');
    
    % Progress indicators (squares)
    squareSize = 20;
    startX = 150;
    for i = 1:6
        color = [0.3, 0.7, 0.5]; % Default color
        if i <= 2
            color = [0.4, 0.8, 0.6]; % Completed color
        end
        
        uicontrol(headerPanel, ...
            'Style', 'text', ...
            'String', '', ...
            'Position', [startX + (i-1)*25, 45, squareSize, squareSize], ...
            'BackgroundColor', color);
    end
    
    % Trainer label
    uicontrol(headerPanel, ...
        'Style', 'text', ...
        'String', 'Trainer', ...
        'Position', [150, 20, 100, 20], ...
        'BackgroundColor', [0.2, 0.6, 0.4], ...
        'ForegroundColor', 'white', ...
        'FontSize', 12, ...
        'HorizontalAlignment', 'center');
end

function createMainContent(fig, guiData)
    % Main content panel
    mainPanel = uipanel(fig, ...
        'Position', [0, 0.15, 1, 0.7], ...
        'BackgroundColor', 'white', ...
        'BorderType', 'none');
    
    % Instruction text
    instructionText = uicontrol(mainPanel, ...
        'Style', 'text', ...
        'String', 'Complete a Regular swallow.', ...
        'Position', [20, 420, 360, 30], ...
        'BackgroundColor', 'white', ...
        'FontSize', 16, ...
        'HorizontalAlignment', 'center', ...
        'Tag', 'instructionText');
    
    % Create hexagon button area
    createHexagonButton(mainPanel, guiData);
    
    % Create real-time EMG plot
    createEMGPlot(mainPanel);
    
    % Create hexagon pattern decoration
    createHexagonPattern(mainPanel);
    
    % Quit Session button
    uicontrol(mainPanel, ...
        'Style', 'pushbutton', ...
        'String', 'Quit Session', ...
        'Position', [125, 50, 150, 40], ...
        'BackgroundColor', 'white', ...
        'ForegroundColor', [0.3, 0.7, 0.5], ...
        'FontSize', 14, ...
        'Callback', @quitSession);
end

function createEMGPlot(parent)
    % Create axes for real-time EMG visualization
    ax = axes('Parent', parent, ...
              'Position', [0.1, 0.35, 0.8, 0.15], ...
              'Box', 'on', ...
              'XGrid', 'on', ...
              'YGrid', 'on', ...
              'Tag', 'emgAxes');
    
    xlabel(ax, 'Time (s)');
    ylabel(ax, 'EMG (mV)');
    title(ax, 'Real-time EMG Signal');
    
    % Initialize empty plot
    line(NaN, NaN, 'Parent', ax, 'Color', [0.2, 0.6, 0.4], ...
         'LineWidth', 2, 'Tag', 'emgLine');
    
    % Set initial axes limits
    xlim(ax, [0, 5]);
    ylim(ax, [-0.5, 4]);
end

function updateRealTimePlot(fig, guiData)
    % Update the real-time EMG plot
    ax = findobj(fig, 'Tag', 'emgAxes');
    emgLine = findobj(ax, 'Tag', 'emgLine');
    
    if ~isempty(emgLine) && ~isempty(guiData.timeData)
        % Update plot data
        set(emgLine, 'XData', guiData.timeData, 'YData', guiData.emgData);
        
        % Adjust x-axis to show rolling window
        if guiData.timeData(end) > 5
            xlim(ax, [guiData.timeData(end)-5, guiData.timeData(end)]);
        else
            xlim(ax, [0, 5]);
        end
        
        % Auto-adjust y-axis
        if length(guiData.emgData) > 10
            yMin = min(guiData.emgData) - 0.5;
            yMax = max(guiData.emgData) + 0.5;
            ylim(ax, [yMin, yMax]);
        end
        
        drawnow;
    end
end

function createHexagonButton(parent, guiData)
    % Main hexagon button (using a regular button styled to look hexagonal)
    hexButton = uicontrol(parent, ...
        'Style', 'pushbutton', ...
        'String', sprintf('I''m\nReady'), ...
        'Position', [125, 250, 150, 130], ...
        'BackgroundColor', [0.3, 0.7, 0.5], ...
        'ForegroundColor', 'white', ...
        'FontSize', 18, ...
        'FontWeight', 'bold', ...
        'Tag', 'readyButton', ...
        'ButtonDownFcn', @(src, evt) startRecording(src, evt, parent.Parent), ...
        'Callback', ''); % Empty callback to prevent default behavior
    
    % Note: In MATLAB, creating a true hexagon button requires custom graphics
    % For now, we use a rectangular button. See Step 4 for custom hexagon implementation
end

function createHexagonPattern(parent)
    % Decorative hexagon pattern below the button
    % This is simplified - you can enhance with actual hexagon graphics
    axes('Parent', parent, ...
         'Position', [0.25, 0.15, 0.5, 0.25], ...
         'XLim', [0, 1], ...
         'YLim', [0, 1], ...
         'Visible', 'off');
    
    % Draw simplified hexagon pattern
    hexColors = [0.3, 0.7, 0.5; 
                 0.4, 0.8, 0.6; 
                 0.2, 0.6, 0.4];
    
    % You can add patch objects here to create actual hexagons
end

function createBottomNav(fig)
    % Bottom navigation panel
    navPanel = uipanel(fig, ...
        'Position', [0, 0, 1, 0.15], ...
        'BackgroundColor', [0.98, 0.98, 0.98], ...
        'BorderType', 'line');
    
    % Navigation items
    navItems = {'Train', 'Track', 'Nutrition', 'Coach', 'More'};
    navIcons = {'▢', '📊', '🍎', '📚', '⋯'}; % Simplified icons
    
    buttonWidth = 70;
    startX = 10;
    
    for i = 1:length(navItems)
        % Icon
        uicontrol(navPanel, ...
            'Style', 'text', ...
            'String', navIcons{i}, ...
            'Position', [startX + (i-1)*buttonWidth, 45, buttonWidth, 20], ...
            'BackgroundColor', [0.98, 0.98, 0.98], ...
            'FontSize', 16, ...
            'HorizontalAlignment', 'center');
        
        % Label
        uicontrol(navPanel, ...
            'Style', 'text', ...
            'String', navItems{i}, ...
            'Position', [startX + (i-1)*buttonWidth, 25, buttonWidth, 20], ...
            'BackgroundColor', [0.98, 0.98, 0.98], ...
            'FontSize', 10, ...
            'HorizontalAlignment', 'center');
    end
end

% Callback functions
function startRecording(src, evt, fig)
    guiData = guidata(fig);
    
    if strcmp(get(src, 'SelectionType'), 'normal') % Mouse down
        % Change button appearance
        set(src, 'BackgroundColor', [0.8, 0.4, 0.2]); % Orange color
        set(src, 'String', sprintf('Recording...\n(Hold)'));
        
        % Start recording
        guiData.isRecording = true;
        guiData.recordStartTime = tic;
        guiData.emgData = [];
        guiData.timeData = [];
        
        % Update guidata
        guidata(fig, guiData);
        
        % Set up button release detection
        set(fig, 'WindowButtonUpFcn', @(s,e) stopRecording(src, fig));
        
        % Start data collection timer (100 Hz sampling rate)
        guiData.dataTimer = timer('Period', 0.01, ...
                                 'ExecutionMode', 'fixedRate', ...
                                 'TimerFcn', @(t,e) collectData(fig), ...
                                 'BusyMode', 'drop');
        start(guiData.dataTimer);
        guidata(fig, guiData);
    end
end

function stopRecording(buttonHandle, fig)
    guiData = guidata(fig);
    
    if guiData.isRecording
        % Stop data collection
        if isfield(guiData, 'dataTimer') && isvalid(guiData.dataTimer)
            stop(guiData.dataTimer);
            delete(guiData.dataTimer);
        end
        
        % Reset button appearance
        set(buttonHandle, 'BackgroundColor', [0.3, 0.7, 0.5]);
        set(buttonHandle, 'String', sprintf('I''m\nReady'));
        
        % Clear window button up function
        set(fig, 'WindowButtonUpFcn', '');
        
        % Process and save the recorded data
        guiData.isRecording = false;
        guiData.sessionCount = guiData.sessionCount + 1;
        
        % Analyze the swallow
        analyzeSwallow(fig, guiData);
        
        % Update instruction for next swallow type
        updateSwallowType(fig, guiData);
        
        % Save data
        saveSwallowData(guiData);
        
        guidata(fig, guiData);
    end
end

function analyzeSwallow(fig, guiData)
    % Analyze the recorded swallow data
    if length(guiData.emgData) > 10
        % Calculate basic metrics
        peakAmplitude = max(guiData.emgData);
        meanAmplitude = mean(abs(guiData.emgData));
        duration = guiData.timeData(end);
        
        % Find swallow onset and offset (simple threshold method)
        threshold = 0.5;
        aboveThreshold = find(guiData.emgData > threshold);
        if ~isempty(aboveThreshold)
            onsetTime = guiData.timeData(aboveThreshold(1));
            offsetTime = guiData.timeData(aboveThreshold(end));
            swallowDuration = offsetTime - onsetTime;
        else
            onsetTime = 0;
            offsetTime = 0;
            swallowDuration = 0;
        end
        
        % Display results
        msgStr = sprintf(['Swallow Analysis:\n' ...
                         'Type: %s\n' ...
                         'Peak Amplitude: %.2f mV\n' ...
                         'Mean Amplitude: %.2f mV\n' ...
                         'Total Duration: %.2f s\n' ...
                         'Swallow Duration: %.2f s'], ...
                         guiData.currentSwallowType, ...
                         peakAmplitude, meanAmplitude, ...
                         duration, swallowDuration);
        
        % Create analysis figure
        analysisFig = figure('Name', 'Swallow Analysis', ...
                            'Position', [500, 100, 600, 400], ...
                            'NumberTitle', 'off');
        
        % Plot the recorded EMG
        subplot(2,1,1);
        plot(guiData.timeData, guiData.emgData, 'LineWidth', 2);
        hold on;
        
        % Mark onset and offset
        if swallowDuration > 0
            plot([onsetTime, onsetTime], ylim, 'r--', 'LineWidth', 2);
            plot([offsetTime, offsetTime], ylim, 'r--', 'LineWidth', 2);
            text(onsetTime, peakAmplitude*0.9, 'Onset', 'Color', 'red');
            text(offsetTime, peakAmplitude*0.9, 'Offset', 'Color', 'red');
        end
        
        xlabel('Time (s)');
        ylabel('EMG Amplitude (mV)');
        title(sprintf('%s Swallow EMG Recording', guiData.currentSwallowType));
        grid on;
        
        % Plot power spectrum
        subplot(2,1,2);
        if length(guiData.emgData) > 100
            Fs = 100; % Sampling frequency (Hz)
            [pxx, f] = pwelch(guiData.emgData, [], [], [], Fs);
            plot(f, 10*log10(pxx), 'LineWidth', 2);
            xlabel('Frequency (Hz)');
            ylabel('Power/Frequency (dB/Hz)');
            title('Power Spectrum');
            grid on;
        end
        
        % Add text annotation
        annotation('textbox', [0.02, 0.02, 0.3, 0.15], ...
                  'String', msgStr, ...
                  'FontSize', 10, ...
                  'BackgroundColor', 'white');
    else
        warndlg('Not enough data collected for analysis.', 'Analysis Warning');
    end
end

function saveSwallowData(guiData)
    % Save swallow data to file
    timestamp = datestr(now, 'yyyymmdd_HHMMSS');
    filename = sprintf('SwallowData_%s_%s.mat', guiData.currentSwallowType, timestamp);
    
    % Create data structure
    swallowData = struct();
    swallowData.type = guiData.currentSwallowType;
    swallowData.timeData = guiData.timeData;
    swallowData.emgData = guiData.emgData;
    swallowData.sessionCount = guiData.sessionCount;
    swallowData.timestamp = timestamp;
    
    % Save to file
    save(filename, 'swallowData');
    fprintf('Data saved to: %s\n', filename);
end

function collectData(fig)
    % Simulated EMG data collection with realistic swallowing pattern
    guiData = guidata(fig);
    
    if guiData.isRecording
        currentTime = toc(guiData.recordStartTime);
        
        % Generate simulated EMG signal
        emgValue = generateSimulatedEMG(currentTime, guiData.currentSwallowType);
        
        % Add noise to make it more realistic
        noise = 0.05 * randn();
        emgValue = emgValue + noise;
        
        % Store data
        guiData.timeData = [guiData.timeData, currentTime];
        guiData.emgData = [guiData.emgData, emgValue];
        
        % Update real-time plot if it exists
        updateRealTimePlot(fig, guiData);
        
        guidata(fig, guiData);
    end
end

function emgValue = generateSimulatedEMG(t, swallowType)
    % Generate different EMG patterns based on swallow type
    
    switch swallowType
        case 'Regular'
            % Regular swallow: single peak pattern
            if t < 0.5
                emgValue = 0.1 * randn(); % Baseline
            elseif t >= 0.5 && t < 2.0
                % Swallow activity (gaussian-like peak)
                emgValue = 2 * exp(-((t-1.25)^2)/(2*0.3^2));
            else
                emgValue = 0.1 * randn(); % Return to baseline
            end
            
        case 'Effortful'
            % Effortful swallow: higher amplitude, longer duration
            if t < 0.5
                emgValue = 0.1 * randn(); % Baseline
            elseif t >= 0.5 && t < 3.0
                % Stronger, longer swallow activity
                emgValue = 3.5 * exp(-((t-1.75)^2)/(2*0.5^2));
            else
                emgValue = 0.1 * randn(); % Return to baseline
            end
            
        case 'Held'
            % Held swallow: sustained activity
            if t < 0.5
                emgValue = 0.1 * randn(); % Baseline
            elseif t >= 0.5 && t < 1.0
                % Rise phase
                emgValue = 2 * (t - 0.5) / 0.5;
            elseif t >= 1.0 && t < 3.0
                % Hold phase
                emgValue = 2 + 0.3 * sin(2*pi*8*t); % Sustained with tremor
            elseif t >= 3.0 && t < 3.5
                % Release phase
                emgValue = 2 * (3.5 - t) / 0.5;
            else
                emgValue = 0.1 * randn(); % Return to baseline
            end
    end
    
    % Add muscle fatigue effect for longer recordings
    if t > 5
        emgValue = emgValue * exp(-(t-5)/10);
    end
end

function updateSwallowType(fig, guiData)
    % Cycle through swallow types
    swallowTypes = {'Regular', 'Effortful', 'Held'};
    currentIndex = find(strcmp(swallowTypes, guiData.currentSwallowType));
    nextIndex = mod(currentIndex, length(swallowTypes)) + 1;
    
    guiData.currentSwallowType = swallowTypes{nextIndex};
    
    % Update instruction text
    instructionText = findobj(fig, 'Tag', 'instructionText');
    if nextIndex == 3
        set(instructionText, 'String', sprintf('Complete another %s swallow.', guiData.currentSwallowType));
    else
        set(instructionText, 'String', sprintf('Complete an %s swallow.', guiData.currentSwallowType));
    end
    
    % Update progress squares (simplified)
    % You would update the header squares here based on session count
    
    guidata(fig, guiData);
end

function quitSession(src, evt)
    % Handle quit session
    choice = questdlg('Are you sure you want to quit this session?', ...
                      'Quit Session', ...
                      'Yes', 'No', 'No');
    
    if strcmp(choice, 'Yes')
        close(gcf);
    end
end