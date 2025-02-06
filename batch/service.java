// MessageListenerService.java
package com.yourcompany.dbsync.service;

import com.yourcompany.dbsync.model.SyncMessage;
import com.yourcompany.dbsync.util.LoggingUtil;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.cloud.aws.messaging.listener.annotation.SqsListener;
import org.springframework.messaging.handler.annotation.Payload;
import org.springframework.stereotype.Service;

@Service
@Slf4j
public class MessageListenerService {
    
    @Autowired
    private DataComparisonService comparisonService;
    
    @Autowired
    private LoggingUtil loggingUtil;
    
    @SqsListener(value = "${cloud.aws.sqs.queue.name}")
    public void receiveMessage(@Payload SyncMessage message) {
        try {
            log.info("Received message for TI: {} and Country: {}", 
                    message.getTechIntegrator(), message.getCountry());
            loggingUtil.logProcessStart(message);
            
            comparisonService.compareAndSync(message);
            
            loggingUtil.logProcessEnd(message);
        } catch (Exception e) {
            log.error("Error processing message: {}", e.getMessage(), e);
            loggingUtil.logError(message, e);
        }
    }
}

// DataComparisonService.java
package com.yourcompany.dbsync.service;

import com.yourcompany.dbsync.mapper.PRDMapper;
import com.yourcompany.dbsync.mapper.STGMapper;
import com.yourcompany.dbsync.model.MainVodContent;
import com.yourcompany.dbsync.model.SyncMessage;
import com.yourcompany.dbsync.util.LoggingUtil;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@Service
@Slf4j
public class DataComparisonService {
    
    @Autowired
    private STGMapper stgMapper;
    
    @Autowired
    private PRDMapper prdMapper;
    
    @Autowired
    private SyncService syncService;
    
    @Autowired
    private LoggingUtil loggingUtil;
    
    public void compareAndSync(SyncMessage message) {
        try {
            // Fetch assets from both databases
            List<MainVodContent> stgAssets = stgMapper.getAssetsByTIAndCountry(
                message.getTechIntegrator(), message.getCountry());
            List<MainVodContent> prdAssets = prdMapper.getAssetsByTIAndCountry(
                message.getTechIntegrator(), message.getCountry());
            
            log.info("Found {} assets in STG and {} assets in PRD", 
                    stgAssets.size(), prdAssets.size());
            
            // Create map of PRD assets for easy lookup
            Map<String, MainVodContent> prdAssetsMap = prdAssets.stream()
                .collect(Collectors.toMap(
                    asset -> asset.getContentId() + "_" + asset.getCountry(),
                    asset -> asset
                ));
            
            // Process each STG asset
            for (MainVodContent stgAsset : stgAssets) {
                try {
                    String key = stgAsset.getContentId() + "_" + stgAsset.getCountry();
                    MainVodContent prdAsset = prdAssetsMap.get(key);
                    
                    if (prdAsset != null) {
                        processExistingAsset(stgAsset);
                    } else {
                        processNewAsset(stgAsset);
                    }
                } catch (Exception e) {
                    log.error("Error processing asset {}: {}", 
                            stgAsset.getContentId(), e.getMessage(), e);
                    loggingUtil.logAssetError(stgAsset, e);
                }
            }
        } catch (Exception e) {
            log.error("Error in comparison service: {}", e.getMessage(), e);
            loggingUtil.logError(message, e);
            throw e;
        }
    }
    
    private void processExistingAsset(MainVodContent stgAsset) {
        if ("TVplus".equals(stgAsset.getFeedWorker())) {
            if (stgAsset.getIsCmsPrd() == 2) {
                log.info("Skipping asset {} as isCmsPrd = 2", stgAsset.getContentId());
                return;
            }
            
            syncService.updateExistingAsset(stgAsset);
        }
    }
    
    private void processNewAsset(MainVodContent stgAsset) {
        if ("TVplus".equals(stgAsset.getFeedWorker())) {
            syncService.updateNewAsset(stgAsset);
        }
    }
}

// SyncService.java
package com.yourcompany.dbsync.service;

import com.yourcompany.dbsync.mapper.STGMapper;
import com.yourcompany.dbsync.model.MainVodContent;
import com.yourcompany.dbsync.util.LoggingUtil;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@Slf4j
public class SyncService {
    
    @Autowired
    private STGMapper stgMapper;
    
    @Autowired
    private LoggingUtil loggingUtil;
    
    @Transactional(transactionManager = "stgTransactionManager")
    public void updateExistingAsset(MainVodContent asset) {
        try {
            log.info("Updating existing asset: {}", asset.getContentId());
            
            // Update main table
            stgMapper.updateAssetStatus(
                asset.getContentId(),
                asset.getCountry(),
                "released",
                asset.getIsCmsPrd()
            );
            
            // Update denormalized tables
            updateDenormalizedTables(asset);
            
            log.info("Successfully updated asset: {}", asset.getContentId());
        } catch (Exception e) {
            log.error("Error updating existing asset {}: {}", 
                    asset.getContentId(), e.getMessage(), e);
            loggingUtil.logAssetError(asset, e);
            throw e;
        }
    }
    
    @Transactional(transactionManager = "stgTransactionManager")
    public void updateNewAsset(MainVodContent asset) {
        try {
            log.info("Updating new asset: {}", asset.getContentId());
            
            // Update main table
            stgMapper.updateAssetStatus(
                asset.getContentId(),
                asset.getCountry(),
                "READY_FOR_QC",
                0
            );
            
            // Update denormalized tables
            updateDenormalizedTables(asset);
            
            log.info("Successfully updated new asset: {}", asset.getContentId());
        } catch (Exception e) {
            log.error("Error updating new asset {}: {}", 
                    asset.getContentId(), e.getMessage(), e);
            loggingUtil.logAssetError(asset, e);
            throw e;
        }
    }
    
    private void updateDenormalizedTables(MainVodContent asset) {
        stgMapper.updateCastTable(asset.getContentId(), asset.getCountry());
        stgMapper.updateExternalIdTable(asset.getContentId(), asset.getCountry());
        stgMapper.updateRatingTable(asset.getContentId(), asset.getCountry());
        stgMapper.updateAdbreakTable(asset.getContentId(), asset.getCountry());
        stgMapper.updateDrmTable(asset.getContentId(), asset.getCountry());
        stgMapper.updatePlatformTable(asset.getContentId(), asset.getCountry());
    }
}