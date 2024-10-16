import lombok.Builder;
import lombok.Getter;
import lombok.Setter;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.function.Executable;

import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.util.Arrays;
import java.util.HashMap;
import java.util.Map;
import java.util.function.Supplier;

public class ModelDtoTestUtility {

    public static <T> void testModelOrDto(Class<T> clazz) {
        testNoArgsConstructor(clazz);
        testAllArgsConstructor(clazz);
        testBuilder(clazz);
        testGettersAndSetters(clazz);
    }

    private static <T> void testNoArgsConstructor(Class<T> clazz) {
        if (clazz.isAnnotationPresent(NoArgsConstructor.class)) {
            Assertions.assertDoesNotThrow(() -> clazz.getDeclaredConstructor().newInstance());
        }
    }

    private static <T> void testAllArgsConstructor(Class<T> clazz) {
        if (clazz.isAnnotationPresent(AllArgsConstructor.class)) {
            Constructor<?>[] constructors = clazz.getDeclaredConstructors();
            Constructor<?> allArgsConstructor = Arrays.stream(constructors)
                    .filter(c -> c.getParameterCount() == clazz.getDeclaredFields().length)
                    .findFirst()
                    .orElseThrow(() -> new AssertionError("AllArgsConstructor not found"));

            Assertions.assertDoesNotThrow(() -> {
                Object[] args = Arrays.stream(clazz.getDeclaredFields())
                        .map(field -> getDefaultValue(field.getType()))
                        .toArray();
                allArgsConstructor.newInstance(args);
            });
        }
    }

    private static <T> void testBuilder(Class<T> clazz) {
        if (clazz.isAnnotationPresent(Builder.class)) {
            Method builderMethod = Arrays.stream(clazz.getDeclaredMethods())
                    .filter(m -> m.getName().equals("builder"))
                    .findFirst()
                    .orElseThrow(() -> new AssertionError("Builder method not found"));

            Assertions.assertDoesNotThrow(() -> {
                Object builder = builderMethod.invoke(null);
                Method buildMethod = builder.getClass().getMethod("build");
                buildMethod.invoke(builder);
            });
        }
    }

    private static <T> void testGettersAndSetters(Class<T> clazz) {
        Object instance = Assertions.assertDoesNotThrow(() -> clazz.getDeclaredConstructor().newInstance());

        for (Field field : clazz.getDeclaredFields()) {
            String fieldName = field.getName();
            String getterName = "get" + capitalize(fieldName);
            String setterName = "set" + capitalize(fieldName);

            Method getter = Assertions.assertDoesNotThrow(() -> clazz.getMethod(getterName));
            Method setter = Assertions.assertDoesNotThrow(() -> clazz.getMethod(setterName, field.getType()));

            Object testValue = getDefaultValue(field.getType());
            Assertions.assertDoesNotThrow(() -> setter.invoke(instance, testValue));
            Object retrievedValue = Assertions.assertDoesNotThrow(() -> getter.invoke(instance));
            Assertions.assertEquals(testValue, retrievedValue);
        }
    }

    private static String capitalize(String str) {
        return str.substring(0, 1).toUpperCase() + str.substring(1);
    }

    private static Object getDefaultValue(Class<?> type) {
        if (type == boolean.class) return false;
        if (type == char.class) return '\u0000';
        if (type == byte.class) return (byte) 0;
        if (type == short.class) return (short) 0;
        if (type == int.class) return 0;
        if (type == long.class) return 0L;
        if (type == float.class) return 0.0f;
        if (type == double.class) return 0.0d;
        return null;
    }
}