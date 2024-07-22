package com.example.historyservice.service.impl;

import com.example.historyservice.dto.LicenseChangeRequestDTO;
import com.example.historyservice.dto.LicenseHistoryResponseDTO;
import com.example.historyservice.dto.PaginationCriteria;
import com.example.historyservice.dto.SortCriteria;
import com.example.historyservice.mapper.LicenseHistoryMapper;
import com.example.historyservice.model.LicenseHistory;
import com.example.historyservice.service.LicenseHistoryService;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.List;

@Service
public class LicenseHistoryServiceImpl implements LicenseHistoryService {

    @Autowired
    private LicenseHistoryMapper licenseHistoryMapper;

    @Autowired
    private ObjectMapper objectMapper;

    @Override
    public void logLicenseChange(LicenseChangeRequestDTO request) {
        LicenseHistory existingHistory = licenseHistoryMapper.getLicenseHistoryByMovieId(request.getMovieId());
        
        if (existingHistory == null) {
            LicenseHistory newHistory = new LicenseHistory();
            newHistory.setMovieId(request.getMovieId());
            newHistory.setChanges(createInitialChangeJson(request));
            licenseHistoryMapper.insertLicenseHistory(newHistory);
        } else {
            String updatedChanges = appendChange(existingHistory.getChanges(), request);
            licenseHistoryMapper.updateLicenseHistory(request.getMovieId(), updatedChanges);
        }
    }

    @Override
    public List<LicenseHistoryResponseDTO> getLicenseHistory(String movieId, PaginationCriteria pagination, SortCriteria sort) {
        return licenseHistoryMapper.getLicenseHistory(movieId, pagination.getOffset(), pagination.getLimit(), sort.getField(), sort.getOrder());
    }

    // JSON approach
    private String createInitialChangeJson(LicenseChangeRequestDTO request) {
        try {
            ArrayNode changesArray = objectMapper.createArrayNode();
            ObjectNode changeNode = objectMapper.createObjectNode()
                    .put("changeDate", LocalDateTime.now().toString())
                    .put("previousReleaseDate", request.getPreviousReleaseDate().toString())
                    .put("previousExpiryDate", request.getPreviousExpiryDate().toString())
                    .put("previousStatus", request.getPreviousStatus())
                    .put("changedBy", request.getChangedBy());
            changesArray.add(changeNode);
            return objectMapper.writeValueAsString(changesArray);
        } catch (Exception e) {
            throw new RuntimeException("Error creating initial change JSON", e);
        }
    }

    // JSON approach
    private String appendChange(String existingChanges, LicenseChangeRequestDTO request) {
        try {
            JsonNode existingChangesNode = objectMapper.readTree(existingChanges);
            ObjectNode newChange = objectMapper.createObjectNode()
                    .put("changeDate", LocalDateTime.now().toString())
                    .put("previousReleaseDate", request.getPreviousReleaseDate().toString())
                    .put("previousExpiryDate", request.getPreviousExpiryDate().toString())
                    .put("previousStatus", request.getPreviousStatus())
                    .put("changedBy", request.getChangedBy());
            
            if (existingChangesNode.isArray()) {
                ((ArrayNode) existingChangesNode).add(newChange);
            } else {
                ArrayNode newChangesArray = objectMapper.createArrayNode();
                newChangesArray.add(existingChangesNode);
                newChangesArray.add(newChange);
                existingChangesNode = newChangesArray;
            }
            
            return objectMapper.writeValueAsString(existingChangesNode);
        } catch (Exception e) {
            throw new RuntimeException("Error appending change to existing JSON", e);
        }
    }

    // String approach (alternative implementation)
    /*
    private String createInitialChangeString(LicenseChangeRequestDTO request) {
        return String.format("[{\"changeDate\":\"%s\",\"previousReleaseDate\":\"%s\",\"previousExpiryDate\":\"%s\",\"previousStatus\":\"%s\",\"changedBy\":\"%s\"}]",
                LocalDateTime.now(),
                request.getPreviousReleaseDate(),
                request.getPreviousExpiryDate(),
                request.getPreviousStatus(),
                request.getChangedBy());
    }

    private String appendChangeString(String existingChanges, LicenseChangeRequestDTO request) {
        String newChange = String.format("{\"changeDate\":\"%s\",\"previousReleaseDate\":\"%s\",\"previousExpiryDate\":\"%s\",\"previousStatus\":\"%s\",\"changedBy\":\"%s\"}",
                LocalDateTime.now(),
                request.getPreviousReleaseDate(),
                request.getPreviousExpiryDate(),
                request.getPreviousStatus(),
                request.getChangedBy());
        
        if (existingChanges.startsWith("[")) {
            // Remove the closing bracket, add a comma and the new change, then close the array
            return existingChanges.substring(0, existingChanges.length() - 1) + "," + newChange + "]";
        } else {
            // Wrap the existing change and new change in an array
            return "[" + existingChanges + "," + newChange + "]";
        }
    }
    */
}