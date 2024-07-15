<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE mapper PUBLIC "-//mybatis.org//DTD Mapper 3.0//EN" "http://mybatis.org/dtd/mybatis-3-mapper.dtd">
<mapper namespace="com.example.usermanagement.mapper.UserHistoryMapper">
    <!-- batchInsertUserHistory remains the same -->

    <select id="getUserHistory" resultType="com.example.usermanagement.dto.UserHistoryResponseDTO">
        SELECT 
            uh.user_id as userId,
            uh.username,
            uh.change_date_time as changeDateTime,
            uh.upd_by_id as updById,
            u.role as currentRole,
            u.status as currentStatus,
            uh.change
        FROM 
            user_history uh
        JOIN 
            users u ON uh.user_id = u.id
        WHERE 
            uh.user_id = #{userId}
        ORDER BY 
            ${sortCol} ${sortOrder}
        LIMIT #{limit} OFFSET #{offset}
    </select>

    <!-- getActionName remains the same -->
</mapper>