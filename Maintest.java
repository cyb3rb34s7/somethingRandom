import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.context.ApplicationContext;

import static org.assertj.core.api.Assertions.assertThat;

@SpringBootTest
class MyApplicationTests {

    @Test
    void contextLoads(ApplicationContext context) {
        assertThat(context).isNotNull();
    }

    @Test
    void mainMethodDoesNotThrowException() {
        assertThat(invokeMain(MyApplication.class)).doesNotThrowAnyException();
    }

    private static Runnable invokeMain(Class<?> clazz) {
        return () -> {
            try {
                clazz.getMethod("main", String[].class).invoke(null, (Object) new String[0]);
            } catch (Exception e) {
                throw new RuntimeException(e);
            }
        };
    }
}