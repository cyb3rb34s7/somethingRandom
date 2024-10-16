import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.context.ApplicationContext;

import static org.assertj.core.api.Assertions.assertThat;

@SpringBootTest
class CmsHistoryApplicationTests {

    @Test
    void contextLoads(ApplicationContext context) {
        assertThat(context).isNotNull();
    }

    @Test
    void mainMethodDoesNotThrowException() {
        assertThat(() -> {
            try {
                CmsHistoryApplication.main(new String[]{});
            } catch (Exception e) {
                throw new AssertionError("Main method threw an exception", e);
            }
        }).doesNotThrowAnyException();
    }
}