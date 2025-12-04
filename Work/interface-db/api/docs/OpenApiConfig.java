package com.cms.dbinterface.smfparser.configurations;

import com.cms.dbinterface.smfparser.common.constant.Constants;
import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.info.Info;
import io.swagger.v3.oas.models.tags.Tag;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.util.List;

@Configuration
public class OpenApiConfig {

    @Bean
    public OpenAPI openAPI() {
        Info info = new Info();
        info.title(Constants.OPEN_API_TITLE);
        info.description(Constants.OPEN_API_DESCRIPTION);
        info.version(Constants.OPEN_API_VERSION);

        return new OpenAPI()
                .info(info)
                .tags(List.of(
                        new Tag().name("Asset").description("Asset management operations - Create and retrieve VOD program assets"),
                        new Tag().name("License").description("License window management - Update license availability windows for programs"),
                        new Tag().name("Media").description("Media information management - Edit media metadata and streaming details"),
                        new Tag().name("Event").description("Event window management - Manage event scheduling windows for programs"),
                        new Tag().name("Health").description("Health check operations - Verify database connectivity status")
                ));
    }
}
