package com.example.usermanagement.dto;

import lombok.Data;
import com.fasterxml.jackson.databind.JsonNode;
import java.util.List;

@Data
public class UserHistoryRequestDTO {
    private List<UserChange> changes;
    private String updById;
    private String actionId;

    @Data
    public static class UserChange {
        private String userId;
        private String username;
        private JsonNode change;
    }
}

package com.example.usermanagement.dto;

import lombok.Data;
import lombok.Builder;
import com.fasterxml.jackson.databind.JsonNode;
import java.time.LocalDateTime;

@Data
@Builder
public class UserHistoryResponseDTO {
    private String userId;
    private String username;
    private LocalDateTime changeDateTime;
    private String updById;
    private String currentRole;
    private String currentStatus;
    private JsonNode change;
}
