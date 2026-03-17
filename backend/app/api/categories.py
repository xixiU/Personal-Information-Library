"""Category API - 分类管理接口."""
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.category import Category
from app.models.source import Source
from app.schemas.category import CategoryCreate, CategoryUpdate, CategoryResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/categories", tags=["categories"])


@router.post("", response_model=CategoryResponse, status_code=201)
async def create_category(category: CategoryCreate, db: Session = Depends(get_db)):
    """创建分类."""
    existing = db.query(Category).filter(Category.name == category.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Category name already exists")

    db_category = Category(**category.model_dump())
    db.add(db_category)
    db.commit()
    db.refresh(db_category)

    logger.info(f"Created category: {db_category.id}")
    return db_category


@router.get("", response_model=List[CategoryResponse])
async def list_categories(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """获取分类列表."""
    categories = db.query(Category).offset(skip).limit(limit).all()
    return categories


@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(category_id: int, db: Session = Depends(get_db)):
    """获取分类详情."""
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category


@router.put("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: int, category_update: CategoryUpdate, db: Session = Depends(get_db)
):
    """更新分类."""
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    update_data = category_update.model_dump(exclude_unset=True)

    # 检查名称唯一性
    if "name" in update_data:
        existing = db.query(Category).filter(
            Category.name == update_data["name"], Category.id != category_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Category name already exists")

    for field, value in update_data.items():
        setattr(category, field, value)

    db.commit()
    db.refresh(category)

    logger.info(f"Updated category: {category_id}")
    return category


@router.delete("/{category_id}", status_code=204)
async def delete_category(category_id: int, db: Session = Depends(get_db)):
    """删除分类（需检查是否有关联信源）."""
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    # 检查是否有关联信源
    source_count = db.query(Source).filter(Source.category_id == category_id).count()
    if source_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete category with {source_count} associated sources"
        )

    db.delete(category)
    db.commit()

    logger.info(f"Deleted category: {category_id}")
    return None
