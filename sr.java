package com.example.usermanagement.service.impl;

import com.example.usermanagement.dto.UserHistoryRequestDTO;
import com.example.usermanagement.dto.UserHistoryResponseDTO;
import com.example.usermanagement.exception.InvalidActionException;
import com.example.usermanagement.mapper.UserHistoryMapper;
import com.example.usermanagement.model.UserHistory;
import com.example.usermanagement.service.UserHistoryService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;
import java.util.stream.Collectors;

@Service
public class UserHistoryServiceImpl implements UserHistoryService {

    @Autowired
    private UserHistoryMapper userHistoryMapper;

    @Override
    @Transactional
    public void createUserHistories(UserHistoryRequestDTO request) {
        String actionName = userHistoryMapper.getActionName(request.getActionId());
        if (actionName == null) {
            throw new InvalidActionException("Invalid action id: " + request.getActionId());
        }

        LocalDateTime changeDateTime = LocalDateTime.now();

        List<UserHistory> histories = request.getChanges().stream()
            .map(change -> UserHistory.builder()
                .userId(change.getUserId())
                .username(change.getUsername())
                .updById(request.getUpdById())
                .actionId(request.getActionId())
                .actionName(actionName)
                .changeDateTime(changeDateTime)
                .change(change.getChange())
                .build())
            .collect(Collectors.toList());

        userHistoryMapper.batchInsertUserHistory(histories);
    }

    @Override
    public List<UserHistoryResponseDTO> getUserHistory(String userId, String sortCol, String sortOrder, int limit, int offset) {
        List<UserHistory> histories = userHistoryMapper.getUserHistory(userId, sortCol, sortOrder, limit, offset);
        return histories.stream()
            .map(history -> UserHistoryResponseDTO.builder()
                .userId(history.getUserId())
                .username(history.getUsername())
                .changeDateTime(history.getChangeDateTime())
                .updById(history.getUpdById())
                .currentRole(history.getCurrentRole())
                .currentStatus(history.getCurrentStatus())
                .change(history.getChange())
                .build())
            .collect(Collectors.toList());
    }
}