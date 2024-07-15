package com.example.usermanagement.mapper;

import com.example.usermanagement.model.UserHistory;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import java.util.List;

@Mapper
public interface UserHistoryMapper {
    void batchInsertUserHistory(@Param("histories") List<UserHistory> histories);
    List<UserHistory> getUserHistory(@Param("userId") String userId, 
                                     @Param("sortCol") String sortCol, 
                                     @Param("sortOrder") String sortOrder, 
                                     @Param("limit") int limit, 
                                     @Param("offset") int offset);
    String getActionName(@Param("actionId") String actionId);
}