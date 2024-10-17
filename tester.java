import lombok.*;
import org.junit.jupiter.api.Assertions;
import java.lang.reflect.*;
import java.time.*;
import java.util.*;

public class ModelDtoTestUtility {

    public static <T> void testModelOrDto(Class<T> clazz) {
        testNoArgsConstructor(clazz);
        testAllArgsConstructor(clazz);
        testBuilder(clazz);
        testGettersAndSetters(clazz);
        if (clazz.isAnnotationPresent(Data.class) || clazz.isAnnotationPresent(EqualsAndHashCode.class)) {
            testEqualsAndHashCode(clazz);
        }
        if (clazz.isAnnotationPresent(Data.class) || clazz.isAnnotationPresent(ToString.class)) {
            testToString(clazz);
        }
    }

    private static <T> void testNoArgsConstructor(Class<T> clazz) {
        try {
            clazz.getDeclaredConstructor().newInstance();
        } catch (NoSuchMethodException e) {
            if (clazz.isAnnotationPresent(NoArgsConstructor.class)) {
                Assertions.fail("@NoArgsConstructor is present but no-args constructor is not accessible");
            }
        } catch (Exception e) {
            // If there's no no-args constructor, that's okay
        }
    }

    private static <T> void testAllArgsConstructor(Class<T> clazz) {
        if (!clazz.isAnnotationPresent(AllArgsConstructor.class)) {
            return;
        }
        Constructor<?>[] constructors = clazz.getDeclaredConstructors();
        Optional<Constructor<?>> allArgsConstructor = Arrays.stream(constructors)
                .filter(c -> c.getParameterCount() == clazz.getDeclaredFields().length)
                .findFirst();

        if (allArgsConstructor.isPresent()) {
            Constructor<?> constructor = allArgsConstructor.get();
            Object[] args = Arrays.stream(constructor.getParameterTypes())
                    .map(ModelDtoTestUtility::createDummyValue)
                    .toArray();

            try {
                constructor.setAccessible(true);
                Object instance = constructor.newInstance(args);
                Assertions.assertNotNull(instance);
            } catch (Exception e) {
                Assertions.fail("Failed to instantiate using all-args constructor: " + e.getMessage());
            }
        } else {
            Assertions.fail("@AllArgsConstructor is present but all-args constructor is not found");
        }
    }

    private static <T> void testBuilder(Class<T> clazz) {
        if (!clazz.isAnnotationPresent(Builder.class)) {
            return;
        }
        try {
            Method builderMethod = clazz.getDeclaredMethod("builder");
            Object builder = builderMethod.invoke(null);
            
            for (Field field : clazz.getDeclaredFields()) {
                String setterName = field.getName();
                try {
                    Method setter = builder.getClass().getMethod(setterName, field.getType());
                    Object dummyValue = createDummyValue(field.getType());
                    setter.invoke(builder, dummyValue);
                } catch (NoSuchMethodException e) {
                    // It's okay if some fields don't have a setter in the builder
                }
            }

            Method buildMethod = builder.getClass().getMethod("build");
            Object instance = buildMethod.invoke(builder);
            Assertions.assertNotNull(instance);
        } catch (Exception e) {
            Assertions.fail("Failed to use builder: " + e.getMessage());
        }
    }

    private static <T> void testGettersAndSetters(Class<T> clazz) {
        Object instance;
        try {
            instance = clazz.getDeclaredConstructor().newInstance();
        } catch (Exception e) {
            try {
                Method builderMethod = clazz.getDeclaredMethod("builder");
                Object builder = builderMethod.invoke(null);
                Method buildMethod = builder.getClass().getMethod("build");
                instance = buildMethod.invoke(builder);
            } catch (Exception ex) {
                // If we can't create an instance, we can't test getters and setters
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

                Object testValue = createDummyValue(field.getType());
                setter.invoke(instance, testValue);
                Object retrievedValue = getter.invoke(instance);
                Assertions.assertEquals(testValue, retrievedValue);
                
                // Test null value for non-primitive types
                if (!field.getType().isPrimitive()) {
                    setter.invoke(instance, (Object) null);
                    retrievedValue = getter.invoke(instance);
                    Assertions.assertNull(retrievedValue);
                }
            } catch (NoSuchMethodException e) {
                // It's okay if some fields don't have both getter and setter
            } catch (Exception e) {
                Assertions.fail("Failed to test getter/setter for " + fieldName + ": " + e.getMessage());
            }
        }
    }

    private static <T> void testEqualsAndHashCode(Class<T> clazz) {
        try {
            T instance1 = clazz.getDeclaredConstructor().newInstance();
            T instance2 = clazz.getDeclaredConstructor().newInstance();
            
            // Test reflexivity
            Assertions.assertEquals(instance1, instance1);
            
            // Test symmetry
            Assertions.assertEquals(instance1, instance2);
            Assertions.assertEquals(instance2, instance1);
            
            // Test hashCode consistency
            Assertions.assertEquals(instance1.hashCode(), instance2.hashCode());
            
            // Test with null
            Assertions.assertNotEquals(instance1, null);
            
            // Test with different type
            Assertions.assertNotEquals(instance1, new Object());
            
            // Test with different values
            for (Field field : clazz.getDeclaredFields()) {
                field.setAccessible(true);
                Object differentValue = createDifferentDummyValue(field.getType());
                field.set(instance2, differentValue);
                Assertions.assertNotEquals(instance1, instance2, "Instances should not be equal when " + field.getName() + " is different");
                field.set(instance2, field.get(instance1)); // Reset for next iteration
            }
        } catch (Exception e) {
            Assertions.fail("Failed to test equals/hashCode: " + e.getMessage());
        }
    }

    private static <T> void testToString(Class<T> clazz) {
        try {
            T instance = clazz.getDeclaredConstructor().newInstance();
            String toString = instance.toString();
            Assertions.assertNotNull(toString);
            Assertions.assertFalse(toString.isEmpty());
            // We won't check for field names in toString as implementations may vary
        } catch (Exception e) {
            Assertions.fail("Failed to test toString: " + e.getMessage());
        }
    }

    private static String capitalize(String str) {
        return str.substring(0, 1).toUpperCase() + str.substring(1);
    }

    private static Object createDummyValue(Class<?> type) {
        if (type.isPrimitive()) return getPrimitiveDefaultValue(type);
        if (type == String.class) return "dummyString";
        if (type.isEnum()) return type.getEnumConstants()[0];
        if (List.class.isAssignableFrom(type)) return new ArrayList<>();
        if (Set.class.isAssignableFrom(type)) return new HashSet<>();
        if (Map.class.isAssignableFrom(type)) return new HashMap<>();
        if (type.isArray()) return Array.newInstance(type.getComponentType(), 0);
        if (type == Date.class) return new Date();
        if (type == Instant.class) return Instant.now();
        if (type == LocalDate.class) return LocalDate.now();
        if (type == LocalTime.class) return LocalTime.now();
        if (type == LocalDateTime.class) return LocalDateTime.now();
        if (Exception.class.isAssignableFrom(type)) return new Exception("Dummy exception");
        try {
            return type.getDeclaredConstructor().newInstance();
        } catch (Exception e) {
            return null;
        }
    }

    private static Object createDifferentDummyValue(Class<?> type) {
        if (type == boolean.class || type == Boolean.class) return true;
        if (type == char.class || type == Character.class) return 'X';
        if (type == byte.class || type == Byte.class) return (byte) 1;
        if (type == short.class || type == Short.class) return (short) 1;
        if (type == int.class || type == Integer.class) return 1;
        if (type == long.class || type == Long.class) return 1L;
        if (type == float.class || type == Float.class) return 1.0f;
        if (type == double.class || type == Double.class) return 1.0d;
        if (type == String.class) return "differentDummyString";
        if (type.isEnum()) {
            Object[] constants = type.getEnumConstants();
            return constants.length > 1 ? constants[1] : constants[0];
        }
        // For other types, we'll return a different instance or null
        return createDummyValue(type);
    }

    private static Object getPrimitiveDefaultValue(Class<?> type) {
        if (type == boolean.class) return false;
        if (type == char.class) return '\u0000';
        if (type == byte.class) return (byte) 0;
        if (type == short.class) return (short) 0;
        if (type == int.class) return 0;
        if (type == long.class) return 0L;
        if (type == float.class) return 0.0f;
        if (type == double.class) return 0.0d;
        throw new IllegalArgumentException("Unknown primitive type: " + type);
    }
}