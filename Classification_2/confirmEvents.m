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
