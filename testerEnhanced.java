import lombok.*;
import org.junit.jupiter.api.Assertions;

import java.lang.reflect.*;
import java.time.*;
import java.util.*;
import java.util.stream.Collectors;

public class ModelDtoTestUtility {

    public static <T> void testModelOrDto(Class<T> clazz) {
        testNoArgsConstructor(clazz);
        testAllArgsConstructor(clazz);
        testBuilder(clazz);
        testGettersAndSetters(clazz);
    }

    private static <T> void testNoArgsConstructor(Class<T> clazz) {
        try {
            clazz.getDeclaredConstructor().newInstance();
        } catch (NoSuchMethodException e) {
            // No-args constructor doesn't exist, which is fine if it's not annotated
            if (clazz.isAnnotationPresent(NoArgsConstructor.class)) {
                Assertions.fail("@NoArgsConstructor is present but no-args constructor is not accessible");
            }
        } catch (Exception e) {
            Assertions.fail("Failed to instantiate using no-args constructor: " + e.getMessage());
        }
    }

    private static <T> void testAllArgsConstructor(Class<T> clazz) {
        Constructor<?>[] constructors = clazz.getDeclaredConstructors();
        Optional<Constructor<?>> allArgsConstructor = Arrays.stream(constructors)
                .filter(c -> c.getParameterCount() == clazz.getDeclaredFields().length)
                .findFirst();

        if (allArgsConstructor.isPresent()) {
            Constructor<?> constructor = allArgsConstructor.get();
            Object[] args = Arrays.stream(constructor.getParameterTypes())
                    .map(type -> createDummyValue(type, type))
                    .toArray();

            try {
                constructor.setAccessible(true);
                Object instance = constructor.newInstance(args);
                Assertions.assertNotNull(instance);
            } catch (Exception e) {
                Assertions.fail("Failed to instantiate using all-args constructor: " + e.getMessage());
            }
        } else if (clazz.isAnnotationPresent(AllArgsConstructor.class)) {
            Assertions.fail("@AllArgsConstructor is present but all-args constructor is not found");
        }
    }

    private static <T> void testBuilder(Class<T> clazz) {
        try {
            Method builderMethod = clazz.getDeclaredMethod("builder");
            Object builder = builderMethod.invoke(null);
            
            for (Field field : clazz.getDeclaredFields()) {
                String setterName = field.getName();
                try {
                    Method setter = builder.getClass().getMethod(setterName, field.getType());
                    Object dummyValue = createDummyValue(field.getType(), field.getGenericType());
                    setter.invoke(builder, dummyValue);
                } catch (NoSuchMethodException e) {
                    // It's okay if some fields don't have a setter in the builder
                }
            }

            Method buildMethod = builder.getClass().getMethod("build");
            Object instance = buildMethod.invoke(builder);
            Assertions.assertNotNull(instance);
        } catch (NoSuchMethodException e) {
            if (clazz.isAnnotationPresent(Builder.class)) {
                Assertions.fail("@Builder is present but builder method is not found");
            }
        } catch (Exception e) {
            Assertions.fail("Failed to use builder: " + e.getMessage());
        }
    }

    private static <T> void testGettersAndSetters(Class<T> clazz) {
        Object instance;
        try {
            instance = clazz.getDeclaredConstructor().newInstance();
        } catch (Exception e) {
            // If no-args constructor is not available, try to create instance using builder
            try {
                Method builderMethod = clazz.getDeclaredMethod("builder");
                Object builder = builderMethod.invoke(null);
                Method buildMethod = builder.getClass().getMethod("build");
                instance = buildMethod.invoke(builder);
            } catch (Exception ex) {
                Assertions.fail("Failed to create instance for getter/setter test: " + ex.getMessage());
                return;
            }
        }

        for (Field field : clazz.getDeclaredFields()) {
            String fieldName = field.getName();
            String getterName = "get" + capitalize(fieldName);
            String setterName = "set" + capitalize(fieldName);

            try {
                Method getter = clazz.getMethod(getterName);
                Method setter = clazz.getMethod(setterName, field.getType());

                Object testValue = createDummyValue(field.getType(), field.getGenericType());
                setter.invoke(instance, testValue);
                Object retrievedValue = getter.invoke(instance);
                Assertions.assertEquals(testValue, retrievedValue);
            } catch (NoSuchMethodException e) {
                // It's okay if some fields don't have both getter and setter
            } catch (Exception e) {
                Assertions.fail("Failed to test getter/setter for " + fieldName + ": " + e.getMessage());
            }
        }
    }

    // ... (rest of the methods remain the same)