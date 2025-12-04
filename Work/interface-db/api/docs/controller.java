package com.cms.dbinterface.smfparser.controllers;

import com.cms.dbinterface.smfparser.common.exceptions.*;
import com.cms.dbinterface.smfparser.common.util.ErrorCode;
import com.cms.dbinterface.smfparser.dtos.ApiResponseDto;
import com.cms.dbinterface.smfparser.dtos.ErrorResponseDto;
import com.cms.dbinterface.smfparser.dtos.ReqForErrorNotification;
import com.cms.dbinterface.smfparser.dtos.ResponseDto;
import com.cms.dbinterface.smfparser.models.*;
import com.cms.dbinterface.smfparser.services.*;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.networknt.schema.ValidationMessage;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.media.Content;
import io.swagger.v3.oas.annotations.media.ExampleObject;
import io.swagger.v3.oas.annotations.media.Schema;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.*;
import java.util.regex.*;

import static com.cms.dbinterface.smfparser.common.constant.Constants.*;

@Slf4j
@RestController
@RequestMapping(value = {"/cms/v1/vod", "/cms/v2/vod"})
public class ProgramController {
    private final ProgramService programService;
    private final ObjectMapper objectMapper;
    private final SmfMapperService smfMapperService;
    private final JsonValidationService jsonValidationService;
    private final JsonErrorFormatterService jsonErrorFormatterService;
    private final ErrorInsertService errorInsertService;

    public ProgramController(ProgramService programService,
                             ObjectMapper objectMapper,
                             SmfMapperService smfMapperService,
                             JsonValidationService jsonValidationService,
                             JsonErrorFormatterService jsonErrorFormatterService,
                             ErrorInsertService errorInsertService
    ) {

        this.programService = programService;
        this.objectMapper = objectMapper;
        this.smfMapperService = smfMapperService;
        this.jsonValidationService = jsonValidationService;
        this.jsonErrorFormatterService = jsonErrorFormatterService;
        this.errorInsertService = errorInsertService;
    }

    Program program = Program.builder().build();
    LicenseWindow licenseWindow = LicenseWindow.builder().build();

    EventWindow eventWindow=EventWindow.builder().build();
    Media mediaData = Media.builder().build();
    String countryFlag;
    String region;

    @Tag(name = "Asset")
    @Operation(
            summary = "Save program asset to database",
            description = "Validates and saves program JSON to the CMS database. The response includes SQS notification status. " +
                    "The request body must contain a valid SMF format JSON with required fields: program_id, type, titles, and images.")
    @ApiResponses({
            @ApiResponse(responseCode = "200", description = "Asset saved successfully",
                    content = @Content(schema = @Schema(implementation = ResponseDto.class), mediaType = "application/json")),
            @ApiResponse(responseCode = "400", description = "Bad Request - Invalid input data",
                    content = @Content(schema = @Schema(implementation = ErrorResponseDto.class), mediaType = "application/json",
                            examples = {
                                    @ExampleObject(name = "Invalid JSON Format (4001)", description = "JSON is null, empty, or malformed",
                                            value = "{\"stat\":\"Fail\",\"error\":{\"code\":\"4001\",\"msg\":\"Invalid JSON Format\",\"desc\":\"Input Json is invalid!\"}}"),
                                    @ExampleObject(name = "Schema Validation Failed (4002)", description = "JSON doesn't match required schema",
                                            value = "{\"stat\":\"Fail\",\"error\":{\"code\":\"4002\",\"msg\":\"Malformed Body Content\",\"desc\":\"$.type: is missing but it is required\"}}"),
                                    @ExampleObject(name = "Mandatory Element Missing (4003)", description = "Required fields not provided",
                                            value = "{\"stat\":\"Fail\",\"error\":{\"code\":\"4003\",\"msg\":\"Mandatory Element Missing\",\"desc\":\"Invalid input, Program Id not present or contains Empty String!\"}}"),
                                    @ExampleObject(name = "Invalid Parameter (4004)", description = "Query parameter is invalid",
                                            value = "{\"stat\":\"Fail\",\"error\":{\"code\":\"4004\",\"msg\":\"Invalid parameter\",\"desc\":\"Invalid parameter : 'program_id' is invalid!\"}}"),
                                    @ExampleObject(name = "Invalid Country (4005)", description = "Country code is invalid or not allowed",
                                            value = "{\"stat\":\"Fail\",\"error\":{\"code\":\"4005\",\"msg\":\"Invalid Country\",\"desc\":\"Invalid Country Code - XX\"}}")
                            })),
            @ApiResponse(responseCode = "500", description = "Internal Server Error",
                    content = @Content(schema = @Schema(implementation = ErrorResponseDto.class), mediaType = "application/json",
                            examples = @ExampleObject(name = "Server Error (5001)",
                                    value = "{\"stat\":\"Fail\",\"error\":{\"code\":\"5001\",\"msg\":\"Internal Server Error\",\"desc\":\"Database connection failed\"}}")))
    })
    @PostMapping("/asset")
    public ResponseEntity<ResponseDto> savePrograms(
            @Parameter(description = "Two-letter country code (e.g., US, GB, KR)", required = true, example = "US")
            @Valid @RequestParam("country_code") String country_code,
            @Parameter(description = "Content provider identifier", required = true, example = "netflix")
            @RequestParam("provider_id") String provider_id,
            @io.swagger.v3.oas.annotations.parameters.RequestBody(
                    description = "Program asset in SMF JSON format",
                    required = true,
                    content = @Content(schema = @Schema(implementation = Program.class),
                            examples = @ExampleObject(name = "Sample Asset",
                                    value = "{\"program_id\":\"movie_12345\",\"type\":\"movie\",\"titles\":[{\"title\":\"Sample Movie\",\"language\":\"en\"}],\"images\":[{\"url\":\"https://example.com/poster.jpg\",\"type\":\"poster\"}]}")))
            @RequestBody(required = false) JsonNode smf_json)
            throws InvalidJsonFormatException,
            InvalidCountryException,
            InvalidParamException,
            ElementValueCheckException,
            MandatoryElementMissingException {

        //Check for json input
        if (smf_json == null || smf_json.isArray() || smf_json.isEmpty()) {
            log.error("InvalidJsonFormatException: Invalid Json provided please check!!");
            String errMsg = smf_json == null ? "Input Json is not provided!" : "Input Json is invalid!";
            errorInsertService.sendNotification(errMsg,ErrorCode.INVALID_JSON_FORMAT, ASSET);
            throw new InvalidJsonFormatException(errMsg);
        }

        //Check for country_code input
        checkCountry(country_code, ASSET);
        //Check for providerId input
        checkProvider(country_code, provider_id, ASSET);

        log.info("SMF Request Received: {}", smf_json);

        String program_id ;
        if(!smf_json.has(TABLE_SAVE_ASSET_PK)||smf_json.get(TABLE_SAVE_ASSET_PK).asText().isBlank()){
            log.error("Program Id Not Found Or its Empty String");
            errorInsertService.sendNotification("Program Id not present or contains Empty String", ErrorCode.MANDATORY_ELEMENT_MISSING, ASSET);
            throw new MandatoryElementMissingException(("Invalid input, Program Id not present or contains Empty String!"));
        }
        else {
            program_id = smf_json.get(TABLE_SAVE_ASSET_PK).asText();
        }
        //Json Validation check for Json input
        Set<ValidationMessage> errors;
        errors = jsonValidationService.validateJson(smf_json);
        String responseError = "";
        if (!errors.isEmpty()) {
            responseError = jsonErrorFormatterService.formatErrors(errors);
            log.error("InvalidJsonFormatException : Invalid parameter : 'smf_json' is invalid please check!!");
            //saving error to dynamodb
            ReqForErrorNotification request = ReqForErrorNotification.builder()
                    .programId(program_id)
                    .providerId(provider_id)
                    .countryCode(country_code)
                    .inputJson(smf_json.toString())
                    .responseError(responseError)
                    .errorCode(ErrorCode.ELEMENT_VALUE_CHECK_FAILED)
                    .apiType(ASSET).build();
            errorInsertService.insertApiErrorInDynamo(request);
            throw new ElementValueCheckException(responseError);
        }

        try {
            program = objectMapper.convertValue(smf_json, Program.class);

            if (program.getProgramId() == null || program.getTitles() == null || program.getImages() == null || program.getType() == null) {
                log.error("Invalid input, mandatory elements missing!");
                throw new MandatoryElementMissingException("Invalid input, mandatory elements missing!");
            }
            log.info(
                    "Controller layer : Request received for country code : {} ,provider_id : {} ,and Json {}",
                    country_code, provider_id, smf_json);
        } catch (IllegalArgumentException e) {
            log.error(JSON_SYNTAX_CONVERT_OBJECT_MAPPER_EXCEPTION_MSG);
            throw new IllegalArgumentException(e);
        } catch (InvalidInputArrayJsonException e) {
            log.error("Exception while checking duplicate license ids in asset : {}", e.getMessage());
            throw new InvalidInputArrayJsonException(e.getMessage());
        }


        return new ResponseEntity<>(
                programService.savePrograms(country_code.toUpperCase(), provider_id, program, smf_json), HttpStatus.OK);
    }


    @Tag(name = "License")
    @Operation(
            summary = "Update license window for a program",
            description = "Updates the license availability window (start/end dates) for an existing program. " +
                    "The request body must be an array of license window objects containing license_id, available_starting, and available_ending dates.")
    @ApiResponses({
            @ApiResponse(responseCode = "200", description = "License window updated successfully",
                    content = @Content(schema = @Schema(implementation = ResponseDto.class), mediaType = "application/json")),
            @ApiResponse(responseCode = "400", description = "Bad Request - Invalid input data",
                    content = @Content(schema = @Schema(implementation = ErrorResponseDto.class), mediaType = "application/json",
                            examples = {
                                    @ExampleObject(name = "Invalid JSON Format (4001)", description = "Input is not a valid JSON array",
                                            value = "{\"stat\":\"Fail\",\"error\":{\"code\":\"4001\",\"msg\":\"Invalid JSON Format\",\"desc\":\"Input Array is not provided!\"}}"),
                                    @ExampleObject(name = "Schema Validation Failed (4002)", description = "License window JSON doesn't match schema",
                                            value = "{\"stat\":\"Fail\",\"error\":{\"code\":\"4002\",\"msg\":\"Malformed Body Content\",\"desc\":\"$.license_id: is missing but it is required\"}}"),
                                    @ExampleObject(name = "Invalid Parameter (4004)", description = "Query parameter is invalid",
                                            value = "{\"stat\":\"Fail\",\"error\":{\"code\":\"4004\",\"msg\":\"Invalid parameter\",\"desc\":\"Invalid parameter : 'program_id' is invalid!\"}}"),
                                    @ExampleObject(name = "Invalid Country (4005)", description = "Country code is invalid",
                                            value = "{\"stat\":\"Fail\",\"error\":{\"code\":\"4005\",\"msg\":\"Invalid Country\",\"desc\":\"Invalid Country Code - XX\"}}")
                            })),
            @ApiResponse(responseCode = "500", description = "Internal Server Error",
                    content = @Content(schema = @Schema(implementation = ErrorResponseDto.class), mediaType = "application/json",
                            examples = @ExampleObject(name = "Server Error (5001)",
                                    value = "{\"stat\":\"Fail\",\"error\":{\"code\":\"5001\",\"msg\":\"Internal Server Error\",\"desc\":\"Database operation failed\"}}"))),
            @ApiResponse(responseCode = "501", description = "Not Implemented",
                    content = @Content(schema = @Schema(implementation = ErrorResponseDto.class), mediaType = "application/json",
                            examples = @ExampleObject(name = "Not Implemented (5101)",
                                    value = "{\"stat\":\"Fail\",\"error\":{\"code\":\"5101\",\"msg\":\"Not Implemented\",\"desc\":\"Feature not yet available\"}}")))
    })
    @PostMapping("/license")
    public ResponseEntity<ResponseDto> changeLicense(
            @Parameter(description = "Unique program identifier", required = true, example = "movie_12345")
            @Valid @RequestParam("program_id") String program_id,
            @Parameter(description = "Two-letter country code", required = true, example = "US")
            @RequestParam("country_code") String country_code,
            @Parameter(description = "Content provider identifier", required = true, example = "netflix")
            @RequestParam("provider_id") String provider_id,
            @io.swagger.v3.oas.annotations.parameters.RequestBody(
                    description = "Array of license window objects",
                    required = true,
                    content = @Content(schema = @Schema(implementation = LicenseWindow[].class),
                            examples = @ExampleObject(name = "License Windows",
                                    value = "[{\"license_id\":\"lic_001\",\"available_starting\":\"2024-01-01T00:00:00Z\",\"available_ending\":\"2024-12-31T23:59:59Z\"}]")))
            @RequestBody(required = false) ArrayNode license_window_json)
            throws NotImplementedException,
            InvalidParamException,
            InvalidCountryException,
            InvalidJsonFormatException {

        log.info("Change license request for programId {}, countryCode {}, providerId {}, license_window_json {}", program_id, country_code, provider_id, license_window_json);
        List<LicenseWindow> licenseWindowList = new ArrayList<>();

        //Checking program_id input
        checkProgramId(program_id, LICENSE);

        //Checking country_code input
        checkCountry(country_code, LICENSE);

        //Checking provider_id input
        checkProvider(country_code, provider_id, LICENSE);

        //Check for json input
        if (license_window_json == null) {
            log.error("License : InvalidJsonFormatException: Input Array is not provided please check!");
            throw new InvalidJsonFormatException(INPUT_ARRAY_NOT_PROVIDED_EXCEPTION_MSG);
        }
        if (!license_window_json.isArray() || license_window_json.isEmpty()) {
            log.error("License : InvalidJsonFormatException: Invalid Array provided please check!");
            throw new InvalidJsonFormatException(INPUT_ARRAY_INVALID_EXCEPTION_MSG);
        }

        //Json Validation check for Json input
        Set<ValidationMessage> errors;
        errors = jsonValidationService.validateDateTimeJson(license_window_json);
        String responseError = "";
        if (!errors.isEmpty()) {
            responseError = jsonErrorFormatterService.formatErrors(errors);
            log.error("InvalidJsonFormatException : Invalid parameter : 'license_window_json' is invalid please check!");
            ReqForErrorNotification request = ReqForErrorNotification.builder()
                    .programId(program_id)
                    .providerId(provider_id)
                    .countryCode(country_code)
                    .inputJson(license_window_json.toString())
                    .responseError(responseError)
                    .errorCode(ErrorCode.ELEMENT_VALUE_CHECK_FAILED)
                    .apiType(LICENSE).build();
            errorInsertService.insertApiErrorInDynamo(request);
            throw new ElementValueCheckException(responseError);
        }

        try {
            for (JsonNode node : license_window_json) {
                licenseWindow = objectMapper.convertValue(node, LicenseWindow.class);
                licenseWindowList.add(licenseWindow);
            }

        } catch (IllegalArgumentException e) {
            log.error(JSON_SYNTAX_CONVERT_OBJECT_MAPPER_EXCEPTION_MSG);
            throw new IllegalArgumentException(e);
        } catch (InvalidInputArrayJsonException e) {
            log.error("Exception while checking duplicate license ids : {}", e.getMessage());
            throw new InvalidInputArrayJsonException(e.getMessage());
        }

        return new ResponseEntity<>(programService.changeLicense(program_id, country_code.toUpperCase(), provider_id, ACTION_LICENSE, licenseWindowList, license_window_json), HttpStatus.OK);
    }

    @Tag(name = "Media")
    @Operation(
            summary = "Edit media information for a program",
            description = "Updates media metadata for an existing program including stream URL, quality settings, " +
                    "DRM information, audio/subtitle languages, and ad-related data.")
    @ApiResponses({
            @ApiResponse(responseCode = "200", description = "Media information updated successfully",
                    content = @Content(schema = @Schema(implementation = ResponseDto.class), mediaType = "application/json")),
            @ApiResponse(responseCode = "400", description = "Bad Request - Invalid input data",
                    content = @Content(schema = @Schema(implementation = ErrorResponseDto.class), mediaType = "application/json",
                            examples = {
                                    @ExampleObject(name = "Invalid JSON Format (4001)", description = "JSON is null, empty, or an array",
                                            value = "{\"stat\":\"Fail\",\"error\":{\"code\":\"4001\",\"msg\":\"Invalid JSON Format\",\"desc\":\"Invalid parameter : 'media_json' is missing!\"}}"),
                                    @ExampleObject(name = "Schema Validation Failed (4002)", description = "Media JSON doesn't match schema",
                                            value = "{\"stat\":\"Fail\",\"error\":{\"code\":\"4002\",\"msg\":\"Malformed Body Content\",\"desc\":\"$.stream_url: is missing but it is required\"}}"),
                                    @ExampleObject(name = "Invalid Parameter (4004)", description = "Query parameter is invalid",
                                            value = "{\"stat\":\"Fail\",\"error\":{\"code\":\"4004\",\"msg\":\"Invalid parameter\",\"desc\":\"Invalid parameter : 'program_id' is invalid!\"}}"),
                                    @ExampleObject(name = "Invalid Country (4005)", description = "Country code is invalid",
                                            value = "{\"stat\":\"Fail\",\"error\":{\"code\":\"4005\",\"msg\":\"Invalid Country\",\"desc\":\"Invalid Country Code - XX\"}}")
                            })),
            @ApiResponse(responseCode = "500", description = "Internal Server Error",
                    content = @Content(schema = @Schema(implementation = ErrorResponseDto.class), mediaType = "application/json",
                            examples = @ExampleObject(name = "Server Error (5001)",
                                    value = "{\"stat\":\"Fail\",\"error\":{\"code\":\"5001\",\"msg\":\"Internal Server Error\",\"desc\":\"Database operation failed\"}}")))
    })
    @PostMapping("/media")
    public ResponseEntity<ResponseDto> editMedia(
            @Parameter(description = "Unique program identifier", required = true, example = "movie_12345")
            @Valid @RequestParam("program_id") String program_id,
            @Parameter(description = "Two-letter country code", required = true, example = "US")
            @RequestParam("country_code") String country_code,
            @Parameter(description = "Content provider identifier", required = true, example = "netflix")
            @RequestParam("provider_id") String provider_id,
            @io.swagger.v3.oas.annotations.parameters.RequestBody(
                    description = "Media information JSON object",
                    required = true,
                    content = @Content(schema = @Schema(implementation = Media.class),
                            examples = @ExampleObject(name = "Media Object",
                                    value = "{\"stream_url\":\"https://cdn.example.com/stream.m3u8\",\"quality\":\"4K\",\"audio_languages\":[\"en\",\"es\"],\"subtitle_languages\":[\"en\",\"es\",\"fr\"],\"running_time\":7200}")))
            @RequestBody(required = false) JsonNode media_json)
            throws NotImplementedException,
            InvalidParamException,
            InvalidCountryException,
            InvalidJsonFormatException {

        log.info("Edit media request for program_id {}, country_code {}, provider_id {}, media_json {}", program_id, country_code, provider_id, media_json);

        //Checking program_id input
        checkProgramId(program_id, MEDIA);

        //Checking country_code input
        checkCountry(country_code, MEDIA);

        //Checking provider_id input
        checkProvider(country_code, provider_id, MEDIA);

        //Check for json input
        if (media_json == null) {
            log.error("InvalidJsonFormatException : Invalid parameter : 'media_json' is missing please check!");
            throw new InvalidJsonFormatException("Invalid parameter : 'media_json' is missing!");
        }
        if (media_json.isArray() || media_json.isEmpty()) {
            log.error("InvalidJsonFormatException : Invalid parameter : 'media_json' is invalid please check!");
            throw new InvalidJsonFormatException("Invalid parameter : 'media_json' is invalid!");
        }

        //Json Validation check for Json input
        Set<ValidationMessage> errors;
        errors = jsonValidationService.validateMediaJson(media_json);
        String responseError = "";
        if (!errors.isEmpty()) {
            responseError = jsonErrorFormatterService.formatErrors(errors);
            log.error("InvalidJsonFormatException : Invalid parameter : 'media_json' is invalid please check!");
            ReqForErrorNotification request = ReqForErrorNotification.builder()
                    .programId(program_id)
                    .providerId(provider_id)
                    .countryCode(country_code)
                    .inputJson(media_json.toString())
                    .responseError(responseError)
                    .errorCode(ErrorCode.ELEMENT_VALUE_CHECK_FAILED)
                    .apiType(MEDIA).build();
            errorInsertService.insertApiErrorInDynamo(request);
            throw new ElementValueCheckException(responseError);
        }
        try {
            mediaData = objectMapper.convertValue(media_json, Media.class);
        } catch (IllegalArgumentException e) {
            log.error("IllegalArgumentException : while converting value from json to media class through object mapper");
            throw new IllegalArgumentException(e);
        }

        return new ResponseEntity<>(programService.editMedia(program_id, country_code.toUpperCase(), provider_id, mediaData, media_json), HttpStatus.OK);
    }

    /*         Common checks for Program ID, country and provider         */
    //Check for Program ID

    private void checkProgramId(String programId, String apiType){
        //Checking program_id input
        if (programId == null) {
            log.error("{} : InvalidParamException : Required Parameter : 'program_id' is missing please check!", apiType);
            errorInsertService.sendNotification("Required Parameter : 'program_id' is missing!",ErrorCode.INVALID_PARAMETER, apiType);
            throw new InvalidParamException("Required Parameter : 'program_id' is missing!");
        }
        if (programId.length() > PROGRAM_ID_SIZE_LIMIT
                || programId.isBlank()
                || "null".equals(programId)
                || !Pattern.compile(PROGRAM_ID_REGEX).matcher(programId).matches()) {
            log.error("{} : InvalidParamException : Invalid parameter : 'program_id'!", apiType);
            errorInsertService.sendNotification("Invalid parameter : 'program_id' is invalid! : "+programId,ErrorCode.INVALID_PARAMETER, apiType);
            throw new InvalidParamException("Invalid parameter : 'program_id' is invalid!");
        }
    }

    //Check for countryCode
    private void checkCountry(String countryCode, String apiType) {

        if (countryCode == null) {
            log.error("Required Parameter : 'country_code' is missing please check!");
            throw new InvalidCountryException("Country code is not provided!");
        }
        if (countryCode.length() > COUNTRY_CODE_SIZE_LIMIT
                || countryCode.isBlank()
                || countryCode.isEmpty()
                || !Pattern.compile(COUNTRY_CODE_REGEX).matcher(countryCode).matches()
        ) {
            log.error("Invalid Request Parameter: country code is invalid!");
            throw new InvalidCountryException("Country code is invalid!");
        }

        try {
            countryFlag = smfMapperService.getAllowedCountry(countryCode);
            if (countryFlag == null) {
                errorInsertService.sendNotification("Invalid  Country Code - " + countryCode,ErrorCode.INVALID_COUNTRY, apiType);
                throw new InvalidCountryException("Invalid Country Code - " + countryCode);
            }
        } catch (InvalidCountryException e) {
            log.error("InvalidCountryException : {}", e.getMessage());
            throw new InvalidCountryException("Invalid Country Code - " + countryCode);
        } catch (PostGreSqlException e) {
            log.error("PostGreSqlException: While checking valid country code {}", e.getMessage());
            throw new PostGreSqlException(e.getMessage());
        } catch (Exception e) {
            log.error(e.getMessage());
            throw new GenericRuntimeException(e.getMessage());
        }
        log.info("Country flag: {}", countryFlag);
    }

    //Check for providerId
    private void checkProvider(String countryCode, String providerId, String apiType) {

        if (providerId == null) {
            log.error("InvalidParamException: Invalid parameters provider_id is missing please check!");
            throw new InvalidParamException("Invalid parameters: provider_id is missing!");
        }
        if (providerId.isBlank()
                || providerId.isEmpty()
                || "null".equals(providerId)) {
            log.error("InvalidParamException: Invalid parameters provider_id is invalid please check!");
            throw new InvalidParamException(PROVIDER_ID_INVALID_EXCEPTION_MSG);
        }

        try {
            region = smfMapperService.getRegion(countryCode, providerId);
            if (region == null) {
                String errorMsg = "Invalid Provider Id - " + providerId + " for Country Code - " + countryCode;
                errorInsertService.sendNotification(errorMsg,ErrorCode.INVALID_PARAMETER, apiType);
                throw new InvalidParamException(errorMsg);
            }
        } catch (InvalidParamException e) {
            log.error( "InvalidParamException : {}",e.getMessage());
            throw new InvalidParamException(e.getMessage());
        } catch (PostGreSqlException e) {
            log.error("PostGreSqlException: While checking valid provider Id {}", e.getMessage());
            throw new PostGreSqlException(e.getMessage());
        } catch (Exception e) {
            log.error(e.getMessage());
            throw new GenericRuntimeException(e.getMessage());
        }
    }

    @Tag(name = "Asset")
    @Operation(
            summary = "Get asset details",
            description = "Retrieves detailed information about a specific program asset by calling the internal asset details API. " +
                    "Returns complete asset metadata including titles, images, ratings, and playback information.")
    @ApiResponses({
            @ApiResponse(responseCode = "200", description = "Asset details retrieved successfully",
                    content = @Content(mediaType = "application/json")),
            @ApiResponse(responseCode = "400", description = "Bad Request - Invalid input or asset not found",
                    content = @Content(schema = @Schema(implementation = ErrorResponseDto.class), mediaType = "application/json",
                            examples = {
                                    @ExampleObject(name = "Invalid Parameter (4004)", description = "Query parameter is invalid",
                                            value = "{\"stat\":\"Fail\",\"error\":{\"code\":\"4004\",\"msg\":\"Invalid parameter\",\"desc\":\"Invalid parameter : 'program_id' is invalid!\"}}"),
                                    @ExampleObject(name = "Invalid Country (4005)", description = "Country code is invalid",
                                            value = "{\"stat\":\"Fail\",\"error\":{\"code\":\"4005\",\"msg\":\"Invalid Country\",\"desc\":\"country_code is invalid!\"}}"),
                                    @ExampleObject(name = "Region Not Found (4006)", description = "Country-provider region mapping not found",
                                            value = "{\"stat\":\"Fail\",\"error\":{\"code\":\"4006\",\"msg\":\"Asset Validation Failed\",\"desc\":\"Country Region Mapping not found\"}}"),
                                    @ExampleObject(name = "Asset Not Found (4006)", description = "Asset does not exist",
                                            value = "{\"stat\":\"Fail\",\"error\":{\"code\":\"4006\",\"msg\":\"Asset Validation Failed\",\"desc\":\"Asset Details not found\"}}"),
                                    @ExampleObject(name = "Provider ID Invalid (4004)", description = "Provider ID is missing or invalid",
                                            value = "{\"stat\":\"Fail\",\"error\":{\"code\":\"4004\",\"msg\":\"Invalid parameter\",\"desc\":\"Invalid parameters: provider_id is invalid!\"}}")
                            })),
            @ApiResponse(responseCode = "500", description = "Internal Server Error",
                    content = @Content(schema = @Schema(implementation = ErrorResponseDto.class), mediaType = "application/json",
                            examples = @ExampleObject(name = "Server Error (5001)",
                                    value = "{\"stat\":\"Fail\",\"error\":{\"code\":\"5001\",\"msg\":\"Internal Server Error\",\"desc\":\"Database operation failed\"}}")))
    })
    @GetMapping("/asset/details")
    public ResponseEntity<Object> assetDetails(
            @Parameter(description = "Unique program identifier", required = true, example = "movie_12345")
            @Valid @RequestParam("program_id") String program_id,
            @Parameter(description = "Two-letter country code", required = true, example = "US")
            @RequestParam("country_code") String country_code,
            @Parameter(description = "Content provider identifier", required = true, example = "netflix")
            @RequestParam("provider_id") String provider_id)
            throws
            InvalidParamException,
            InvalidCountryException {
        //Checking program_id input
        checkProgramId(program_id, "AssetDetails");

        //Checking provider_id input
        if (provider_id == null) {
            log.error("AssetDetails : InvalidParamException: Invalid parameters provider_id is missing please check!");
            throw new InvalidParamException("Invalid parameters: provider_id is missing!");
        }
        if (provider_id.isBlank()
                || provider_id.isEmpty()
                || "null".equals(provider_id)) {
            log.error("AssetDetails : InvalidParamException: Invalid parameters provider_id is invalid please check!");
            throw new InvalidParamException(PROVIDER_ID_INVALID_EXCEPTION_MSG);
        }
        //Checking country_code input
        if (country_code == null) {
            log.error("AssetDetails : Invalid request parameter: country code!");
            throw new InvalidCountryException("country_code is not provided!");
        }
        if (country_code.length() > COUNTRY_CODE_SIZE_LIMIT
                || country_code.isBlank()
                || country_code.isEmpty()
                || !Pattern.compile(COUNTRY_CODE_REGEX).matcher(country_code).matches()) {
            log.error("Invalid request parameter: country_code!");
            throw new InvalidCountryException("country_code is invalid!");
        }
        try {
            return new ResponseEntity<>(programService.assetDetails(program_id, country_code.toUpperCase(), provider_id), HttpStatus.OK);
        } catch (RegionNotFoundException e) {
            log.error("Asset Details : PostGreSqlException : Region not found based on country - {} and provider - {} ", country_code, provider_id);
            throw new RegionNotFoundException(e.getMessage());
        } catch (PostGreSqlException e) {
            log.error("Asset Details : PostGreSqlException - Error while fetching region according to country and provider : {}", e.getMessage());
            throw new PostGreSqlException(e.getMessage());
        } catch (AssetDetailsNotFoundException e){
            log.error("Asset Details : AssetDetailsNotFoundException : Exception while fetching asset details from API: {}", e.getMessage());
            throw new AssetDetailsNotFoundException(e.getMessage());
        } catch (Exception e) {
            log.error("Asset Details : Exception while fetching asset details: {}", e.getMessage());
            throw new GenericRuntimeException(e.getMessage());
        }
    }

    @Tag(name = "Health")
    @Operation(
            summary = "Check database connectivity",
            description = "Verifies the PostgreSQL database connection status. Returns OK if the connection is healthy.")
    @ApiResponses({
            @ApiResponse(responseCode = "200", description = "Database connection successful",
                    content = @Content(schema = @Schema(implementation = ApiResponseDto.class), mediaType = "application/json",
                            examples = @ExampleObject(name = "Healthy",
                                    value = "{\"stat\":\"OK\",\"message\":\"Success\"}"))),
            @ApiResponse(responseCode = "500", description = "Database connection failed",
                    content = @Content(schema = @Schema(implementation = ErrorResponseDto.class), mediaType = "application/json",
                            examples = @ExampleObject(name = "Connection Error (5001)",
                                    value = "{\"stat\":\"Fail\",\"error\":{\"code\":\"5001\",\"msg\":\"Internal Server Error\",\"desc\":\"Error while connecting to PostGre Database\"}}")))
    })
    @GetMapping("/healthcheck")
    public ResponseEntity<ApiResponseDto> healthCheck() {
        try {
            smfMapperService.getPostGreConnectionResponse();
            log.info("healthCheck : PostGre Database Connected Successfully");
            return new ResponseEntity<>(ApiResponseDto.builder().stat("OK").message("Success").build(), HttpStatus.OK);
        } catch (PostGreSqlException e) {
            log.error("PostGreSql Exception : Error while connecting to PostGre Database : {}", e.getMessage());
            throw new PostGreSqlException(e.getMessage());
        } catch (Exception e) {
            log.error("Exception : {}", e.getMessage());
            throw new GenericRuntimeException(e.getMessage());
        }
    }

    @Tag(name = "Event")
    @Operation(
            summary = "Update event window for a program",
            description = "Updates or adds event scheduling windows for an existing program. " +
                    "Event windows define when specific events (e.g., live broadcasts, special screenings) are available. " +
                    "The request body must be an array of event window objects containing event_id, event_starting, and event_ending dates.")
    @ApiResponses({
            @ApiResponse(responseCode = "200", description = "Event window updated successfully",
                    content = @Content(schema = @Schema(implementation = ResponseDto.class), mediaType = "application/json")),
            @ApiResponse(responseCode = "400", description = "Bad Request - Invalid input data",
                    content = @Content(schema = @Schema(implementation = ErrorResponseDto.class), mediaType = "application/json",
                            examples = {
                                    @ExampleObject(name = "Invalid JSON Format (4001)", description = "Input is not a valid JSON array",
                                            value = "{\"stat\":\"Fail\",\"error\":{\"code\":\"4001\",\"msg\":\"Invalid JSON Format\",\"desc\":\"Input Array is not provided!\"}}"),
                                    @ExampleObject(name = "Schema Validation Failed (4002)", description = "Event window JSON doesn't match schema",
                                            value = "{\"stat\":\"Fail\",\"error\":{\"code\":\"4002\",\"msg\":\"Malformed Body Content\",\"desc\":\"$.event_id: is missing but it is required\"}}"),
                                    @ExampleObject(name = "Invalid Parameter (4004)", description = "Query parameter is invalid",
                                            value = "{\"stat\":\"Fail\",\"error\":{\"code\":\"4004\",\"msg\":\"Invalid parameter\",\"desc\":\"Invalid parameter : 'program_id' is invalid!\"}}"),
                                    @ExampleObject(name = "Invalid Country (4005)", description = "Country code is invalid",
                                            value = "{\"stat\":\"Fail\",\"error\":{\"code\":\"4005\",\"msg\":\"Invalid Country\",\"desc\":\"Invalid Country Code - XX\"}}")
                            })),
            @ApiResponse(responseCode = "500", description = "Internal Server Error",
                    content = @Content(schema = @Schema(implementation = ErrorResponseDto.class), mediaType = "application/json",
                            examples = @ExampleObject(name = "Server Error (5001)",
                                    value = "{\"stat\":\"Fail\",\"error\":{\"code\":\"5001\",\"msg\":\"Internal Server Error\",\"desc\":\"Database operation failed\"}}"))),
            @ApiResponse(responseCode = "501", description = "Not Implemented",
                    content = @Content(schema = @Schema(implementation = ErrorResponseDto.class), mediaType = "application/json",
                            examples = @ExampleObject(name = "Not Implemented (5101)",
                                    value = "{\"stat\":\"Fail\",\"error\":{\"code\":\"5101\",\"msg\":\"Not Implemented\",\"desc\":\"Feature not yet available\"}}")))
    })
    @PostMapping("/event")
    public ResponseEntity<ResponseDto> changeEvent(
            @Parameter(description = "Unique program identifier", required = true, example = "movie_12345")
            @Valid @RequestParam("program_id") String program_id,
            @Parameter(description = "Two-letter country code", required = true, example = "US")
            @RequestParam("country_code") String country_code,
            @Parameter(description = "Content provider identifier", required = true, example = "netflix")
            @RequestParam("provider_id") String provider_id,
            @io.swagger.v3.oas.annotations.parameters.RequestBody(
                    description = "Array of event window objects",
                    required = true,
                    content = @Content(schema = @Schema(implementation = EventWindow[].class),
                            examples = @ExampleObject(name = "Event Windows",
                                    value = "[{\"event_id\":\"evt_001\",\"event_starting\":\"2024-06-15T20:00:00Z\",\"event_ending\":\"2024-06-15T23:00:00Z\"}]")))
            @RequestBody(required = false) ArrayNode event_window_json)
        throws NotImplementedException,
        InvalidParamException,
        InvalidCountryException,
        InvalidJsonFormatException {

        log.info("Change event request for programId {}, countryCode {}, providerId {}, event_window_json {}", program_id, country_code, provider_id, event_window_json);
        List<EventWindow> eventWindowList = new ArrayList<>();

        //Checking program_id input
        checkProgramId(program_id, EVENT);

        //Checking country_code input
        checkCountry(country_code, EVENT);

        //Checking provider_id input
        checkProvider(country_code, provider_id, EVENT);

        //Check for json input
        if (event_window_json == null) {
            log.error("Event : InvalidJsonFormatException: Input Array is not provided please check!");
            throw new InvalidJsonFormatException(INPUT_ARRAY_NOT_PROVIDED_EXCEPTION_MSG);
        }
        if (!event_window_json.isArray() || event_window_json.isEmpty()) {
            log.error("Event : InvalidJsonFormatException: Invalid Array provided please check!");
            throw new InvalidJsonFormatException(INPUT_ARRAY_INVALID_EXCEPTION_MSG);
        }

        //Json Validation check for Json input
        Set<ValidationMessage> errors;
        errors = jsonValidationService.validateEventJson(event_window_json);
        String responseError = "";
        if (!errors.isEmpty()) {
            responseError = jsonErrorFormatterService.formatErrors(errors);
            log.error("InvalidJsonFormatException : Invalid parameter : 'event_window_json' is invalid please check!");
            ReqForErrorNotification request = ReqForErrorNotification.builder()
                            .programId(program_id)
                            .providerId(provider_id)
                            .countryCode(country_code)
                            .inputJson(event_window_json.toString())
                            .responseError(responseError)
                            .errorCode(ErrorCode.ELEMENT_VALUE_CHECK_FAILED)
                            .apiType(EVENT).build();
            errorInsertService.insertApiErrorInDynamo(request);
            throw new ElementValueCheckException(responseError);
        }

        try {
            for (JsonNode node : event_window_json) {
                eventWindow = objectMapper.convertValue(node, EventWindow.class);
                eventWindowList.add(eventWindow);
            }

        } catch (IllegalArgumentException e) {
            log.error(JSON_SYNTAX_CONVERT_OBJECT_MAPPER_EXCEPTION_MSG);
            throw new IllegalArgumentException(e);
        } catch (InvalidInputArrayJsonException e) {
            log.error("Exception while checking duplicate event ids : {}", e.getMessage());
            throw new InvalidInputArrayJsonException(e.getMessage());
        }

        return new ResponseEntity<>(programService.changeEvent(program_id, country_code.toUpperCase(), provider_id, ACTION_LICENSE, eventWindowList, event_window_json), HttpStatus.OK);
    }

    @Tag(name = "Event")
    @Operation(
            summary = "Remove event window(s) from a program",
            description = "Deletes event window(s) from an existing program. You can either:\n" +
                    "1. Remove specific events by providing an array of event IDs in the request body\n" +
                    "2. Remove ALL events by setting event_type=ALL (no request body needed)")
    @ApiResponses({
            @ApiResponse(responseCode = "200", description = "Event window(s) removed successfully",
                    content = @Content(schema = @Schema(implementation = ResponseDto.class), mediaType = "application/json")),
            @ApiResponse(responseCode = "400", description = "Bad Request - Invalid input data",
                    content = @Content(schema = @Schema(implementation = ErrorResponseDto.class), mediaType = "application/json",
                            examples = {
                                    @ExampleObject(name = "Invalid JSON Format (4001)", description = "Event IDs array is missing or invalid",
                                            value = "{\"stat\":\"Fail\",\"error\":{\"code\":\"4001\",\"msg\":\"Invalid JSON Format\",\"desc\":\"Input Array is not provided!\"}}"),
                                    @ExampleObject(name = "Invalid Parameter (4004)", description = "Query parameter is invalid",
                                            value = "{\"stat\":\"Fail\",\"error\":{\"code\":\"4004\",\"msg\":\"Invalid parameter\",\"desc\":\"Invalid parameter: 'event_type' is invalid! Please provide 'ALL' to delete all events of asset or provide event ids to delete specific events of asset.\"}}"),
                                    @ExampleObject(name = "Invalid Country (4005)", description = "Country code is invalid",
                                            value = "{\"stat\":\"Fail\",\"error\":{\"code\":\"4005\",\"msg\":\"Invalid Country\",\"desc\":\"Invalid Country Code - XX\"}}"),
                                    @ExampleObject(name = "Region Not Found (4006)", description = "Country-provider mapping not found",
                                            value = "{\"stat\":\"Fail\",\"error\":{\"code\":\"4006\",\"msg\":\"Asset Validation Failed\",\"desc\":\"Country Region Mapping not found\"}}"),
                                    @ExampleObject(name = "Asset Not Found (4006)", description = "Program does not exist",
                                            value = "{\"stat\":\"Fail\",\"error\":{\"code\":\"4006\",\"msg\":\"Asset Validation Failed\",\"desc\":\"Asset Details not found\"}}")
                            })),
            @ApiResponse(responseCode = "500", description = "Internal Server Error",
                    content = @Content(schema = @Schema(implementation = ErrorResponseDto.class), mediaType = "application/json",
                            examples = @ExampleObject(name = "Server Error (5001)",
                                    value = "{\"stat\":\"Fail\",\"error\":{\"code\":\"5001\",\"msg\":\"Internal Server Error\",\"desc\":\"Database operation failed\"}}")))
    })
    @PostMapping("/event/remove")
    public ResponseEntity<ResponseDto> removeEventWindow(
            @Parameter(description = "Unique program identifier", required = true, example = "movie_12345")
            @Valid @RequestParam("program_id") String program_id,
            @Parameter(description = "Two-letter country code", required = true, example = "US")
            @RequestParam("country_code") String country_code,
            @Parameter(description = "Content provider identifier", required = true, example = "netflix")
            @RequestParam("provider_id") String provider_id,
            @Parameter(description = "Set to 'ALL' to remove all events, or omit to remove specific events by ID", example = "ALL")
            @RequestParam(name = "event_type", required = false) String event_type,
            @io.swagger.v3.oas.annotations.parameters.RequestBody(
                    description = "Array of event IDs to remove (required if event_type is not 'ALL')",
                    content = @Content(schema = @Schema(implementation = String[].class),
                            examples = @ExampleObject(name = "Event IDs",
                                    value = "[\"evt_001\", \"evt_002\", \"evt_003\"]")))
            @RequestBody(required = false) ArrayNode event_id_json)
            throws
            InvalidParamException,
            InvalidCountryException,
            InvalidJsonFormatException
    {
        String action = ACTION_DELETE;
        if(event_type == null){
            log.info("Event Type is not present hence will delete events according to given event_ids");
            checkValidArrayNode(event_id_json);
        }
        else if (event_type.equalsIgnoreCase("ALL")) {
            action = ACTION_DELETE_ALL;
            log.info("Remove All Events of Asset");
        } else {
            log.info("Invalid parameter: 'event_type' is invalid! Please provide 'ALL' to delete all events of asset or provide event ids to delete specific events of asset.");
            throw new InvalidParamException("Invalid parameter: 'event_type' is invalid! Please provide 'ALL' to delete all events of asset or provide event ids to delete specific events of asset.");
        }
        //Check for json input
        try {

            //Checking program_id input
            checkProgramId(program_id, EVENT);

            //Checking provider_id input
            checkProvider(country_code, provider_id, EVENT);

            //Checking country_code input
            checkCountry(country_code, EVENT);

            log.info("Remove Event Window : Request received for program_id {}, country_code {}, provider_id {}, event_id_json {}", program_id, country_code, provider_id, event_id_json);

        } catch (RegionNotFoundException e) {
            log.error("Event Remove : RegionNotFoundException : Region not found based on country - {} and provider - {} ", country_code, provider_id);
            throw new RegionNotFoundException(e.getMessage());
        } catch (InvalidParamException e) {
            log.error("Event Remove : InvalidParamException : Invalid Parameters either program id - {} or provider id - {} ", program_id, provider_id);
            throw new InvalidParamException(e.getMessage());
        } catch (InvalidCountryException e) {
            log.error("Event Remove : InvalidCountryException : Country Code is not provided or invalid  {} ", country_code);
            throw new InvalidCountryException(e.getMessage());
        } catch (PostGreSqlException e) {
            log.error("Event Remove : PostGreSqlException - Error while fetching region according to country and provider : {}", e.getMessage());
            throw new PostGreSqlException(e.getMessage());
        } catch (AssetDetailsNotFoundException e){
            log.error("Event Remove : AssetDetailsNotFoundException : Exception while fetching asset details from API: {}", e.getMessage());
            throw new AssetDetailsNotFoundException(e.getMessage());
        } catch (Exception e) {
            log.error("Event Remove : Exception : {}", e.getMessage());
            throw new GenericRuntimeException(e.getMessage());
        }
        return new ResponseEntity<>(programService.removeEventWindow(program_id, country_code.toUpperCase(), provider_id, event_id_json, action), HttpStatus.OK);
    }

    private void checkValidArrayNode(ArrayNode arrayNode) throws InvalidJsonFormatException {
        try{
            if (arrayNode == null) {
                log.error("Event Remove :InvalidJsonFormatException: Input Array not provided please check!");
                throw new InvalidJsonFormatException(INPUT_ARRAY_NOT_PROVIDED_EXCEPTION_MSG);
            }
            if (!arrayNode.isArray() || arrayNode.isEmpty()) {
                log.error("Event Remove :InvalidJsonFormatException: Invalid Array provided please check!");
                throw new InvalidJsonFormatException(INPUT_ARRAY_INVALID_EXCEPTION_MSG);
            }
        } catch(Exception e){
            throw new InvalidJsonFormatException(e.getMessage());
        }

    }

}
