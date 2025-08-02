path = uigetdir();
binFiles = dir(path);

overwrite = 1;

for i = 1:length(binFiles)
    if contains(binFiles(i).name, '.bin') && ~binFiles(i).isdir
        
        if ~isfile(fullfile(binFiles(i).folder, 'structs', [binFiles(i).name(1:end-4) '.mat'])) || overwrite

           binFile = readDAQData(fullfile(path, binFiles(i).name), 1, 1);
            % [binFile, metaData] = readDAQData(fullfile(path, binFiles(i).name), 1, 1);


            
        end
        
    end
    
end