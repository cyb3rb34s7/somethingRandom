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
        if (clazz.isAnnotationPresent(Data.class)) {
            testEqualsAndHashCode(clazz);
            testToString(clazz);
        }
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
                Object originalValue = field.get(instance2);
                Object differentValue = createDifferentDummyValue(field.getType(), field.getGenericType());
                field.set(instance2, differentValue);
                Assertions.assertNotEquals(instance1, instance2);
                Assertions.assertNotEquals(instance1.hashCode(), instance2.hashCode());
                field.set(instance2, originalValue); // Reset for next iteration
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
            Assertions.assertTrue(toString.contains(clazz.getSimpleName()));
            for (Field field : clazz.getDeclaredFields()) {
                Assertions.assertTrue(toString.contains(field.getName()));
            }
        } catch (Exception e) {
            Assertions.fail("Failed to test toString: " + e.getMessage());
        }
    }

    private static String capitalize(String str) {
        return str.substring(0, 1).toUpperCase() + str.substring(1);
    }

    private static Object createDummyValue(Class<?> type, Type genericType) {
        if (type.isPrimitive()) {
            return getPrimitiveDefaultValue(type);
        } else if (type == String.class) {
            return "dummyString";
        } else if (type.isEnum()) {
            return type.getEnumConstants()[0];
        } else if (List.class.isAssignableFrom(type)) {
            return createDummyList(genericType);
        } else if (Set.class.isAssignableFrom(type)) {
            return createDummySet(genericType);
        } else if (Map.class.isAssignableFrom(type)) {
            return createDummyMap(genericType);
        } else if (type.isArray()) {
            return Array.newInstance(type.getComponentType(), 1);
        } else if (type == Date.class) {
            return new Date();
        } else if (type == Instant.class) {
            return Instant.now();
        } else if (type == LocalDate.class) {
            return LocalDate.now();
        } else if (type == LocalTime.class) {
            return LocalTime.now();
        } else if (type == LocalDateTime.class) {
            return LocalDateTime.now();
        } else if (Exception.class.isAssignableFrom(type)) {
            return new Exception("Dummy exception");
        } else {
            try {
                return type.getDeclaredConstructor().newInstance();
            } catch (Exception e) {
                return null;
            }
        }
    }

    private static Object createDifferentDummyValue(Class<?> type, Type genericType) {
        Object dummyValue = createDummyValue(type, genericType);
        if (type == boolean.class || type == Boolean.class) {
            return !(boolean) dummyValue;
        } else if (type.isPrimitive() || Number.class.isAssignableFrom(type)) {
            return ((Number) dummyValue).intValue() + 1;
        } else if (type == String.class) {
            return "different" + dummyValue;
        } else if (type.isEnum()) {
            Object[] constants = type.getEnumConstants();
            return constants[constants.length > 1 ? 1 : 0];
        }
        // For other types, we'll return a new instance or null if we can't create one
        return createDummyValue(type, genericType);
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

    private static List<?> createDummyList(Type genericType) {
        if (genericType instanceof ParameterizedType) {
            Type[] typeArguments = ((ParameterizedType) genericType).getActualTypeArguments();
            if (typeArguments.length > 0) {
                Type elementType = typeArguments[0];
                Object element = createDummyValue((Class<?>) elementType, elementType);
                return Collections.singletonList(element);
            }
        }
        return Collections.emptyList();
    }

    private static Set<?> createDummySet(Type genericType) {
        if (genericType instanceof ParameterizedType) {
            Type[] typeArguments = ((ParameterizedType) genericType).getActualTypeArguments();
            if (typeArguments.length > 0) {
                Type elementType = typeArguments[0];
                Object element = createDummyValue((Class<?>) elementType, elementType);
                return Collections.singleton(element);
            }
        }
        return Collections.emptySet();
    }

    private static Map<?, ?> createDummyMap(Type genericType) {
        if (genericType instanceof ParameterizedType) {
            Type[] typeArguments = ((ParameterizedType) genericType).getActualTypeArguments();
            if (typeArguments.length > 1) {
                Type keyType = typeArguments[0];
                Type valueType = typeArguments[1];
                Object key = createDummyValue((Class<?>) keyType, keyType);
                Object value = createDummyValue((Class<?>) valueType, valueType);
                return Collections.singletonMap(key, value);
            }
        }
        return Collections.emptyMap();
    }
}