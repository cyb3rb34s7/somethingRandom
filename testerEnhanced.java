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
                        .map(field -> createDummyValue(field.getType(), field.getGenericType()))
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
                for (Field field : clazz.getDeclaredFields()) {
                    String setterName = field.getName();
                    Method setter = builder.getClass().getMethod(setterName, field.getType());
                    Object dummyValue = createDummyValue(field.getType(), field.getGenericType());
                    setter.invoke(builder, dummyValue);
                }
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

            Object testValue = createDummyValue(field.getType(), field.getGenericType());
            Assertions.assertDoesNotThrow(() -> setter.invoke(instance, testValue));
            Object retrievedValue = Assertions.assertDoesNotThrow(() -> getter.invoke(instance));
            Assertions.assertEquals(testValue, retrievedValue);
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