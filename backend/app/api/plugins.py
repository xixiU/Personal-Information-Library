"""Plugin API - 插件管理接口."""
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.plugin import Plugin
from app.schemas.plugin import PluginCreate, PluginUpdate, PluginResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/plugins", tags=["plugins"])


@router.post("", response_model=PluginResponse, status_code=201)
async def create_plugin(plugin: PluginCreate, db: Session = Depends(get_db)):
    """创建插件."""
    # 检查名称是否已存在
    existing = db.query(Plugin).filter(Plugin.name == plugin.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Plugin name already exists")

    # 创建插件
    db_plugin = Plugin(**plugin.model_dump())
    db.add(db_plugin)
    db.commit()
    db.refresh(db_plugin)

    logger.info(f"Created plugin: {db_plugin.id}")
    return db_plugin


@router.get("", response_model=List[PluginResponse])
async def list_plugins(
    skip: int = 0,
    limit: int = 100,
    enabled: bool = None,
    db: Session = Depends(get_db),
):
    """获取插件列表."""
    query = db.query(Plugin)

    if enabled is not None:
        query = query.filter(Plugin.enabled == enabled)

    plugins = query.offset(skip).limit(limit).all()
    return plugins


@router.get("/{plugin_id}", response_model=PluginResponse)
async def get_plugin(plugin_id: int, db: Session = Depends(get_db)):
    """获取插件详情."""
    plugin = db.query(Plugin).filter(Plugin.id == plugin_id).first()
    if not plugin:
        raise HTTPException(status_code=404, detail="Plugin not found")
    return plugin


@router.put("/{plugin_id}", response_model=PluginResponse)
async def update_plugin(
    plugin_id: int, plugin: PluginUpdate, db: Session = Depends(get_db)
):
    """更新插件."""
    db_plugin = db.query(Plugin).filter(Plugin.id == plugin_id).first()
    if not db_plugin:
        raise HTTPException(status_code=404, detail="Plugin not found")

    # 更新字段
    update_data = plugin.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_plugin, field, value)

    db.commit()
    db.refresh(db_plugin)

    logger.info(f"Updated plugin: {plugin_id}")
    return db_plugin


@router.delete("/{plugin_id}", status_code=204)
async def delete_plugin(plugin_id: int, db: Session = Depends(get_db)):
    """删除插件."""
    db_plugin = db.query(Plugin).filter(Plugin.id == plugin_id).first()
    if not db_plugin:
        raise HTTPException(status_code=404, detail="Plugin not found")

    db.delete(db_plugin)
    db.commit()

    logger.info(f"Deleted plugin: {plugin_id}")
