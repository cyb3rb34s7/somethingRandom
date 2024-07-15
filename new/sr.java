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
        // This method remains the same
    }

    @Override
    public List<UserHistoryResponseDTO> getUserHistory(String userId, String sortCol, String sortOrder, int limit, int offset) {
        return userHistoryMapper.getUserHistory(userId, sortCol, sortOrder, limit, offset);
    }
}