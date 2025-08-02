% This code allows us to read the binary data format from the data saved by
%"daq_data_streaming_with_GUI" function and load the metadata associated
% with the data file.
% in order to read the data from the Binary files we need to know the
% number of rows the data has(81 in our case). We therefore used the "metadata"
% to be able to get this information and also the muscle labels and also to
% identify the rows in the 81 rows of data.

% Alternatively, we could only save the data that we need from the
% Recording software to reduce the number of channels but that would
% require some changes in the code.

% Feel free to reach out for questions.

% Last modified August 28th, 2022
% Author: Scott Ensel
% email: sce30@pitt.edu

% function read_and_plot_saved_DAQ_data

% Select files to load data
function returnStruct = readDAQData(filename, saveStruct, makeFigure)
%     if nargin < 2 || isempty(saveStruct)
%         saveStruct = 0;
%     end
%     if nargin < 3 || isempty(makeFigure)
%         makeFigur = 0;
%     end

    % Grab files
    [path, name, ext] = fileparts(filename);
    fid_read = fopen(filename, 'r');
    metapath = fullfile(path, 'metadata');
    
    name = char(name); % Convert to char array
    metafileTrl = ['*' name(end-2:end) '.mat'];
        % if isempty(metafiles)
        %     error('No matching metafile found.');
        % end
        % metafile = metafiles.name;
        % 

    
    metafile = dir(fullfile(metapath, metafileTrl)).name;
    

  

    % Get metadata needed to load data
    meta_data = load(fullfile(metapath, metafile)).meta_data;
    EMG_CH = meta_data.emg_ch_number;
    Fs = meta_data.fs;
    Num_ch_AI = meta_data.total_analog_in_ch;
    
    % Add sample rate to the structure
    returnStruct.Fs = Fs;    
    
    % Read data from binary file
    [ana_in_data, count] = fread(fid_read, [Num_ch_AI+1,inf], 'double');
    
    muscle_labels = meta_data.musc_labels;
    extra_lab = length(EMG_CH)-length(muscle_labels);
    cur_len_musc_lab = length(muscle_labels);
    if ~(extra_lab==0)
        for i = 1:extra_lab
            muscle_labels{cur_len_musc_lab+i} = 'Not connected';
        end
    end
    
% %     27 to 30
%     if (27 <= str2double(name(end-1:end))) && (str2double(name(end-1:end)) <= 30)
%         for jj = 1:length(muscle_labels)
% 
%             if muscle_labels{jj}(1) == 'R'
% 
%                muscle_labels{jj}(1) = 'L';
% 
%             else
%                muscle_labels{jj}(1) = 'R'; 
% 
%             end
%         end
%     end
     
    DAQ_labels = {'HUMAC_DIR', 'HUMAC_VEL', 'HUMAC_TRQ', 'HUMAC_POS', ...
        'KINARM_TASK', 'KINARM_REC', 'KINARM_REP', 'VICON_REC', 'VICON_FRAME', ...
        'PHOTODIODE', 'GRIP', 'PINCH', 'ARDUINO_TRIG', 'ARDUINO_AMP', ...
        'ARDUINO_ACTIVE', 'DS8R_SYNC'};

    returnStruct.time = ana_in_data(1, :);
    % Append the DAQ data
    for i = 1:length(DAQ_labels)
        returnStruct.(DAQ_labels{i}) = ana_in_data(i+1, :);
    end
    % Append the raw EMG data
    for i = 1:length(EMG_CH)
        if ~strcmp(muscle_labels{i}, 'NC')
            muscleLabel = muscle_labels{i};
            muscleLabel(muscleLabel == '-') = '_'; % Change - to _ to be a valid field name
            
            if  strcmp(muscleLabel,'anterior delt')
                muscleLabel='anterior_delt';
            end
            
            returnStruct.(muscleLabel) = ana_in_data(EMG_CH(i)+1, :);
        end
    end

    if saveStruct
        matPath = fullfile(path, 'structs', [name, '.mat']);
        
        if ~exist(fullfile(path, 'structs'), 'dir')
            mkdir(fullfile(path, 'structs'));
        end
        
        save(matPath, '-struct', 'returnStruct');
    end
    
    %% plotting and saving them for quick looks  
    if makeFigure
        figurePath = fullfile(path, 'quick_figure');
        
        if ~exist(figurePath, 'dir')
            mkdir(figurePath);
        end
        
        Nplots = length(EMG_CH);  

        Fcl = 30/(Fs*0.5);
        Fch = 500/(Fs*0.5);
        N_order = 5;
        [Bbp, Abp] = butter(N_order, [Fcl, Fch], 'bandpass');
        [Blp, Alp] = butter(N_order, Fcl, 'low');

        data_read_plots = zeros(Num_ch_AI, 1);
        data_read__ax = zeros(Num_ch_AI, 1);
        data_read_fig = figure(1);
        data_read_fig.WindowState = 'maximized';

        set(data_read_fig, 'position', [50 200 750 750])
        for j = 1:Nplots
            data_read__ax(j) = subplot((Nplots)/2, 2, j);
            data_read_plots(j) = plot(ana_in_data(1,:), filtfilt(Bbp, Abp, ana_in_data(EMG_CH(j)+1,:)), '-b', 'LineWidth', 1);
            
            ylim([-0.04, 0.04])
            set(data_read__ax(j),'XGrid','on');
            set(data_read__ax(j),'YGrid','on');
            set(data_read__ax(j),'XGrid','on');

            title(sprintf('%s', muscle_labels{j}));
        end
        emgPlotName = metafile(1:end-4);
        emgPlotName(emgPlotName == '_') = '-'; % Change - to _ to be a 
        sgtitle(sprintf('File with: %s', emgPlotName))
%         linkaxes(data_read__ax, 'x')
    
        % save figure
        print(fullfile(figurePath, ['EMGs_', name]), '-dpng', '-painters');

        %% define plotting figure and plot ANALOG-IN data
        data_read_plots2 = zeros(Num_ch_AI, 1);
        data_read__ax2 = zeros(Num_ch_AI, 1);
        data_read_fig2 = figure(2);
        data_read_fig2.WindowState = 'maximized';

        set(data_read_fig2, 'position', [50 200 750 750])
        for j = 1:Nplots
            data_read__ax2(j) = subplot(16/2, 2, j);
            data_read_plots2(j) = plot(ana_in_data(1,:), ana_in_data(j+1,:), '-b', 'LineWidth', 1);

            set(data_read__ax2(j),'XGrid','on');
            set(data_read__ax2(j),'YGrid','on');
            set(data_read__ax2(j),'XGrid','on');
            set(data_read__ax2(j),'YLim', [-1 6]);
            set(data_read__ax2(j),'YLimMode', 'manual');

            title(sprintf('DAQ AI-%i', j-1));
        end
        sgtitle(sprintf('File with: %s', emgPlotName))
%         linkaxes(data_read__ax2, 'x')         
        
        % save figure
%         fig_name = fullfile(figurePath, ['Analog-IN', name]);
%         savefig([fullfile(figurePath, ['Analog-IN', name]), '.fig'])
        print(fullfile(figurePath, ['Analog-IN', name]), '-dpng', '-painters');
%         print(fullfile(figurePath, ['Analog-IN', name]), '-dpng', '-painters');

        
        close all
    end
    
    fclose(fid_read);

end