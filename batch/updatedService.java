@Service
@Slf4j
@RequiredArgsConstructor
public class MessageListenerService {
    
    private final DataComparisonService comparisonService;
    private final CommonMapper stgMapper;
    private final LoggingUtil loggingUtil;
    private final SQSService sqsService;
    
    @SqsListener(value = "${cloud.aws.sqs.queue.name}")
    public void receiveMessage(@Payload SyncMessage message) {
        try {
            if (message.isSyncAll()) {
                processBulkSync();
            } else {
                processSingleSync(message);
            }
        } catch (Exception e) {
            log.error("Error processing message: {}", e.getMessage(), e);
            loggingUtil.logError(message, e);
            sqsService.sendToErrorQueue(message, e);
        }
    }

    private void processBulkSync() {
        log.info("Starting bulk sync process");
        List<Map<String, String>> combinations = stgMapper.getAllTIAndCountryCombinations();
        log.info("Found {} TI and Country combinations to process", combinations.size());
        
        for (Map<String, String> combination : combinations) {
            try {
                SyncMessage newMessage = SyncMessage.builder()
                    .techIntegrator(combination.get("techIntegrator"))
                    .country(combination.get("country"))
                    .syncAll(false)
                    .build();
                
                processSingleSync(newMessage);
            } catch (Exception e) {
                log.error("Error processing combination TI: {} Country: {}: {}", 
                    combination.get("techIntegrator"), 
                    combination.get("country"), 
                    e.getMessage());
            }
        }
        log.info("Completed bulk sync process");
    }

    private void processSingleSync(SyncMessage message) {
        log.info("Processing sync for TI: {} and Country: {}", 
                message.getTechIntegrator(), message.getCountry());
        loggingUtil.logProcessStart(message);
        comparisonService.compareAndSync(message);
        loggingUtil.logProcessEnd(message);
    }
}

@Service
@Slf4j
@RequiredArgsConstructor
public class DataComparisonService {
    
    private final CommonMapper stgMapper;
    private final CommonMapper prdMapper;
    private final SyncService syncService;
    private final LoggingUtil loggingUtil;
    
    public void compareAndSync(SyncMessage message) {
        try {
            List<MainVodContent> stgAssets = stgMapper.getAssetsByTIAndCountry(
                message.getTechIntegrator(), message.getCountry());
            List<MainVodContent> prdAssets = prdMapper.getAssetsByTIAndCountry(
                message.getTechIntegrator(), message.getCountry());
            
            log.info("Found {} assets in STG and {} assets in PRD", 
                    stgAssets.size(), prdAssets.size());

            Map<String, MainVodContent> prdAssetsMap = prdAssets.stream()
                .collect(Collectors.toMap(
                    MainVodContent::getContentId,
                    asset -> asset
                ));
            
            Map<String, MainVodContent> stgAssetsMap = stgAssets.stream()
                .collect(Collectors.toMap(
                    MainVodContent::getContentId,
                    asset -> asset
                ));

            processStgAssets(stgAssets, prdAssetsMap);
            processPrdOnlyAssets(prdAssets, stgAssetsMap);
            
        } catch (Exception e) {
            log.error("Error in comparison service: {}", e.getMessage(), e);
            throw e;
        }
    }

    private void processStgAssets(List<MainVodContent> stgAssets, 
                                Map<String, MainVodContent> prdAssetsMap) {
        for (MainVodContent stgAsset : stgAssets) {
            try {
                if ("TVplus".equals(stgAsset.getFeedWorker())) {
                    if (prdAssetsMap.containsKey(stgAsset.getContentId())) {
                        if (stgAsset.getIsCmsPrd() != 2) {
                            syncService.processExistingAsset(stgAsset);
                        } else {
                            log.info("Skipping asset {} as isCmsPrd = 2", stgAsset.getContentId());
                        }
                    } else {
                        syncService.processNewAsset(stgAsset);
                    }
                }
            } catch (Exception e) {
                log.error("Error processing STG asset {}: {}", 
                        stgAsset.getContentId(), e.getMessage(), e);
                loggingUtil.logAssetError(stgAsset, e);
            }
        }
    }

    private void processPrdOnlyAssets(List<MainVodContent> prdAssets, 
                                    Map<String, MainVodContent> stgAssetsMap) {
        for (MainVodContent prdAsset : prdAssets) {
            if (!stgAssetsMap.containsKey(prdAsset.getContentId())) {
                log.info("Asset {} exists only in PRD", prdAsset.getContentId());
            }
        }
    }
}

@Service
@Slf4j
@RequiredArgsConstructor
public class SyncService {
    
    private final CommonMapper stgMapper;
    private final CommonMapper prdMapper;
    private final RetryTemplate retryTemplate;
    private final LoggingUtil loggingUtil;
    
    @Transactional(transactionManager = "chainedTransactionManager")
    public void processExistingAsset(MainVodContent asset) {
        try {
            retryTemplate.execute(context -> {
                updateExistingAsset(asset);
                return null;
            });
        } catch (Exception e) {
            log.error("Failed to update existing asset {} after all retries", asset.getContentId());
            throw new DatabaseSyncException("Failed to update existing asset", 
                    asset.getContentId(), asset.getCountry(), "UPDATE", e);
        }
    }
    
    @Transactional(transactionManager = "chainedTransactionManager")
    public void processNewAsset(MainVodContent asset) {
        try {
            retryTemplate.execute(context -> {
                updateNewAsset(asset);
                return null;
            });
        } catch (Exception e) {
            log.error("Failed to update new asset {} after all retries", asset.getContentId());
            throw new DatabaseSyncException("Failed to update new asset", 
                    asset.getContentId(), asset.getCountry(), "INSERT", e);
        }
    }
    
    private void updateExistingAsset(MainVodContent asset) {
        stgMapper.updateExistingAsset(asset.getContentId(), asset.getCountry());
        stgMapper.updateDenormalizedTables(asset.getContentId(), asset.getCountry());
        
        prdMapper.updateExistingAsset(asset.getContentId(), asset.getCountry());
        prdMapper.updateDenormalizedTables(asset.getContentId(), asset.getCountry());
        
        log.info("Successfully updated existing asset: {}", asset.getContentId());
    }
    
    private void updateNewAsset(MainVodContent asset) {
        stgMapper.updateNewAsset(asset.getContentId(), asset.getCountry());
        stgMapper.updateDenormalizedTables(asset.getContentId(), asset.getCountry());
        
        log.info("Successfully updated new asset: {}", asset.getContentId());
    }
}

@Service
@Slf4j
@RequiredArgsConstructor
public class SQSService {
    
    @Value("${cloud.aws.sqs.error-queue.name}")
    private String errorQueueName;
    
    private final QueueMessagingTemplate queueMessagingTemplate;
    
    public void sendToErrorQueue(SyncMessage message, Exception e) {
        try {
            ErrorMessage errorMessage = ErrorMessage.builder()
                .contentIds(Collections.emptyList())
                .country(message.getCountry())
                .techIntegrator(message.getTechIntegrator())
                .timestamp(LocalDateTime.now())
                .retryCount(0)
                .errorDetails(e.getMessage())
                .operation("SYNC")
                .build();
                
            queueMessagingTemplate.convertAndSend(errorQueueName, errorMessage);
            log.info("Sent error message to queue for TI: {} and Country: {}", 
                    message.getTechIntegrator(), message.getCountry());
        } catch (Exception sqsError) {
            log.error("Failed to send error message to queue: {}", sqsError.getMessage(), sqsError);
        }
    }
}