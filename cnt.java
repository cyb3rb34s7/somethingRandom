package com.example.usermanagement.controller;

import com.example.usermanagement.dto.UserHistoryRequestDTO;
import com.example.usermanagement.dto.UserHistoryResponseDTO;
import com.example.usermanagement.service.UserHistoryService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/user-history")
public class UserHistoryController {

    @Autowired
    private UserHistoryService userHistoryService;

    @PostMapping
    public ResponseEntity<Void> createUserHistories(@RequestBody UserHistoryRequestDTO request) {
        userHistoryService.createUserHistories(request);
        return ResponseEntity.ok().build();
    }

    @GetMapping("/{userId}")
    public ResponseEntity<List<UserHistoryResponseDTO>> getUserHistory(
            @PathVariable String userId,
            @RequestParam(defaultValue = "changeDateTime") String sortCol,
            @RequestParam(defaultValue = "DESC") String sortOrder,
            @RequestParam(defaultValue = "10") int limit,
            @RequestParam(defaultValue = "0") int offset) {
        List<UserHistoryResponseDTO> history = userHistoryService.getUserHistory(userId, sortCol, sortOrder, limit, offset);
        return ResponseEntity.ok(history);
    }
}