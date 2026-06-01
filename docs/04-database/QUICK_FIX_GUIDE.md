# 数据库服务快速修复指南

## 🎯 核心转换模式

### 基础模式：查询
```python
# ❌ 删除
def _get_by_id_sync(self, id):
    from database.connection import sync_session_factory
    session = sync_session_factory()
    try:
        stmt = select(Model).where(Model.id == id)
        return session.execute(stmt).scalar_one_or_none()
    finally:
        session.close()

async def get_by_id(self, id):
    return await asyncio.get_event_loop().run_in_executor(
        executor, self._get_by_id_sync, id
    )

# ✅ 改为
async def get_by_id(self, id):
    async with DatabaseManager.get_session() as session:
        stmt = select(Model).where(Model.id == id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
```

### 创建模式
```python
# ❌ 删除
def _create_sync(self, data):
    from database.connection import sync_session_factory
    session = sync_session_factory()
    try:
        obj = Model(**data.dict())
        session.add(obj)
        session.commit()
        session.refresh(obj)
        return obj
    finally:
        session.close()

async def create(self, data):
    return await asyncio.get_event_loop().run_in_executor(
        executor, self._create_sync, data
    )

# ✅ 改为
async def create(self, data):
    async with DatabaseManager.get_session() as session:
        obj = Model(**data.dict())
        session.add(obj)
        await session.commit()
        await session.refresh(obj)
        return obj
```

### 更新模式
```python
# ❌ 删除
def _update_sync(self, id, data):
    from database.connection import sync_session_factory
    session = sync_session_factory()
    try:
        stmt = update(Model).where(Model.id == id).values(**data).returning(Model)
        result = session.execute(stmt)
        obj = result.scalar_one_or_none()
        if obj:
            session.commit()
        return obj
    finally:
        session.close()

async def update(self, id, data):
    return await asyncio.get_event_loop().run_in_executor(
        executor, self._update_sync, id, data
    )

# ✅ 改为
async def update(self, id, data):
    async with DatabaseManager.get_session() as session:
        stmt = update(Model).where(Model.id == id).values(**data).returning(Model)
        result = await session.execute(stmt)
        obj = result.scalar_one_or_none()
        if obj:
            await session.commit()
        return obj
```

### 删除模式
```python
# ❌ 删除
def _delete_sync(self, id):
    from database.connection import sync_session_factory
    session = sync_session_factory()
    try:
        stmt = delete(Model).where(Model.id == id)
        result = session.execute(stmt)
        session.commit()
        return result.rowcount > 0
    finally:
        session.close()

async def delete(self, id):
    return await asyncio.get_event_loop().run_in_executor(
        executor, self._delete_sync, id
    )

# ✅ 改为
async def delete(self, id):
    async with DatabaseManager.get_session() as session:
        stmt = delete(Model).where(Model.id == id)
        result = await session.execute(stmt)
        await session.commit()
        return result.rowcount > 0
```

### 列表查询模式
```python
# ❌ 删除
def _get_all_sync(self, limit, offset):
    from database.connection import sync_session_factory
    session = sync_session_factory()
    try:
        stmt = select(Model).limit(limit).offset(offset)
        result = session.execute(stmt)
        return result.scalars().all()
    finally:
        session.close()

async def get_all(self, limit, offset):
    return await asyncio.get_event_loop().run_in_executor(
        executor, self._get_all_sync, limit, offset
    )

# ✅ 改为
async def get_all(self, limit, offset):
    async with DatabaseManager.get_session() as session:
        stmt = select(Model).limit(limit).offset(offset)
        result = await session.execute(stmt)
        return result.scalars().all()
```

## 📋 关键检查清单

每个方法修复后检查:

- [ ] 删除了 `_xxx_sync` 方法
- [ ] 删除了 `loop.run_in_executor(executor, ...)`
- [ ] 删除了方法内的 `from database.connection import sync_session_factory`
- [ ] 使用 `async with DatabaseManager.get_session() as session:`
- [ ] 所有 `session.execute()` 改为 `await session.execute()`
- [ ] 所有 `session.commit()` 改为 `await session.commit()`
- [ ] 所有 `session.flush()` 改为 `await session.flush()`
- [ ] 所有 `session.refresh()` 改为 `await session.refresh()`
- [ ] 删除了 `session.close()` (async with 自动处理)
- [ ] 删除了 `try-finally` (async with 自动处理)

## ⚠️ 常见陷阱

### 1. 忘记 await
```python
# ❌ 错误
result = session.execute(stmt)  # 缺少 await

# ✅ 正确
result = await session.execute(stmt)
```

### 2. 忘记 commit
```python
# ❌ 错误 (写操作未提交)
async def update(self, id, data):
    async with DatabaseManager.get_session() as session:
        session.add(obj)
        # 缺少 commit!
        return obj

# ✅ 正确
async def update(self, id, data):
    async with DatabaseManager.get_session() as session:
        session.add(obj)
        await session.commit()  # 必须commit
        return obj
```

### 3. 错误的异常处理
```python
# ❌ 错误 (async with 已处理)
async def method(self):
    async with DatabaseManager.get_session() as session:
        try:
            result = await session.execute(stmt)
            await session.commit()
            return result
        finally:
            await session.close()  # 不需要!async with自动处理

# ✅ 正确
async def method(self):
    async with DatabaseManager.get_session() as session:
        try:
            result = await session.execute(stmt)
            await session.commit()
            return result
        except Exception as e:
            await session.rollback()  # 只需要rollback
            raise
```

### 4. 参数传递问题
```python
# ❌ 错误 (直接传递Pydantic对象)
async def create(self, data: CreateModel):
    return await asyncio.get_event_loop().run_in_executor(
        executor, self._create_sync, data  # Pydantic对象无法序列化!
    )

# ✅ 正确方案1 (不需要executor)
async def create(self, data: CreateModel):
    async with DatabaseManager.get_session() as session:
        obj = Model(**data.dict())
        session.add(obj)
        await session.commit()
        return obj

# ✅ 正确方案2 (如果必须用executor,先转换)
# 但现在不需要executor了!
```

## 🔧 批量搜索命令

找到需要修复的方法:
```bash
# 查找所有 _sync 方法
grep -n "def _.*_sync(" services/*.py

# 查找所有 run_in_executor
grep -n "run_in_executor" services/*.py

# 查找方法内的懒加载导入
grep -n "from database.connection import sync_session_factory" services/*.py
```

## 📊 进度追踪

| 文件 | 方法数 | 状态 |
|------|--------|------|
| ai_analysis_log_service.py | 5 | ⏳ 待修复 |
| roi_schedule_service.py | 2 | ⏳ 待修复 |
| ai_config_manager.py | 6 | ⏳ 待修复 |
| ai_model_service.py | 8 | ⏳ 待修复 |
| video_file_service.py | 11 | ⏳ 待修复 |
| video_analysis_template_service.py | 2 | ⏳ 待修复 |
| ai_provider_service.py | 8 | ⏳ 待修复 |
| video_stream_service.py | 12 | ⏳ 待修复 |

## 🎬 快速开始

1. **选择文件**: 从优先级列表选择
2. **找到方法**: 搜索 `def _xxx_sync(`
3. **应用模式**: 根据上面的模式重写
4. **检查清单**: 逐项检查
5. **测试**: 运行相关测试
6. **提交**: Git commit
7. **下一个**: 重复步骤1

## 🚀 提速技巧

**使用编辑器的查找替换功能:**

1. 查找: `def _(\w+)_sync\(`
   替换: `async def $1(`

2. 查找: `from database.connection import sync_session_factory`
   替换: (删除行)

3. 查找: `session = sync_session_factory\(\)`
   替换: `async with DatabaseManager.get_session() as session:`

4. 查找: `session\.execute\(`
   替换: `await session.execute(`

5. 查找: `session\.commit\(\)`
   替换: `await session.commit()`

**注意**: 正则替换后仍需要手动检查和调整!

---

**最后更新**: 2025-10-28
**使用此指南可以大幅提升修复效率!** 🎉
