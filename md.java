package com.example.usermanagement.model;

import lombok.Data;
import lombok.Builder;
import com.fasterxml.jackson.databind.JsonNode;
import java.time.LocalDateTime;

@Data
@Builder
public class UserHistory {
    private String userId;
    private String username;
    private String updById;
    private String actionId;
    private String actionName;
    private LocalDateTime changeDateTime;
    private JsonNode change;
    private String currentRole;
    private String currentStatus;
}