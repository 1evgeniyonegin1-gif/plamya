"""
Products API

Каталог продуктов NL International
"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..config import settings
from ..services.products_service import get_products_service, Product
from ..models.user import CuratorUser
from ..models.analytics import ProductView
from .auth import get_current_user

router = APIRouter(prefix="/products", tags=["Products"])


# Pydantic models
class ProductResponse(BaseModel):
    """Single product response"""
    key: str
    name: str
    price: int
    pv: float
    category: str
    line: Optional[str] = None
    price_per_portion: Optional[float] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    image_count: int = 0
    referral_link: str


class ProductsListResponse(BaseModel):
    """Products list response"""
    total: int
    categories: list[str]
    products: list[ProductResponse]
    referral_catalog: str


class CategoryResponse(BaseModel):
    """Category info"""
    name: str
    product_count: int


class CategoriesResponse(BaseModel):
    """Categories list response"""
    categories: list[CategoryResponse]


class LineResponse(BaseModel):
    """Product line info"""
    name: str
    product_count: int
    image_url: Optional[str] = None


class LinesResponse(BaseModel):
    """Lines list response"""
    lines: list[LineResponse]


def product_to_response(product: Product) -> ProductResponse:
    """Convert Product to ProductResponse with referral link"""
    return ProductResponse(
        key=product.key,
        name=product.name,
        price=product.price,
        pv=product.pv,
        category=product.category,
        line=product.line,
        price_per_portion=product.price_per_portion,
        description=product.description,
        image_url=product.image_url,
        image_count=product.image_count,
        referral_link=product.referral_link or settings.referral_catalog,
    )


@router.get("", response_model=ProductsListResponse)
async def get_products(
    category: Optional[str] = Query(None, description="Filter by category"),
    line: Optional[str] = Query(None, description="Filter by product line"),
    search: Optional[str] = Query(None, description="Search in product name"),
    limit: int = Query(20, ge=1, le=100, description="Max products to return"),
    offset: int = Query(0, ge=0, description="Skip first N products"),
):
    """
    Get list of products with optional filtering

    - **category**: Filter by category name
    - **line**: Filter by product line within category
    - **search**: Search in product name (case-insensitive)
    - **limit**: Maximum products to return (default 20, max 100)
    - **offset**: Skip first N products for pagination
    """
    service = get_products_service()
    result = service.get_products(
        category=category,
        search=search,
        line=line,
        limit=limit,
        offset=offset,
    )

    return ProductsListResponse(
        total=result.total,
        categories=result.categories,
        products=[product_to_response(p) for p in result.products],
        referral_catalog=settings.referral_catalog,
    )


@router.get("/lines", response_model=LinesResponse)
async def get_lines(
    category: Optional[str] = Query(None, description="Filter by category"),
):
    """
    Get list of product lines with counts, optionally filtered by category
    """
    service = get_products_service()
    lines_data = service.get_lines(category=category)

    return LinesResponse(
        lines=[LineResponse(**ld) for ld in lines_data]
    )


@router.get("/lines/{line_slug}/image")
async def get_line_image(line_slug: str):
    """Get line cover photo by slug."""
    service = get_products_service()
    image_bytes = service.get_line_image_bytes(line_slug)
    if not image_bytes:
        raise HTTPException(status_code=404, detail="Line image not found")
    return Response(
        content=image_bytes,
        media_type="image/jpeg",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@router.get("/categories", response_model=CategoriesResponse)
async def get_categories():
    """
    Get list of product categories with counts
    """
    service = get_products_service()
    data = service.load_products()

    categories = []
    for cat_name, cat_products in data.get("categories", {}).items():
        categories.append(CategoryResponse(
            name=cat_name,
            product_count=len(cat_products),
        ))

    # Sort by product count
    categories.sort(key=lambda x: x.product_count, reverse=True)

    return CategoriesResponse(categories=categories)


@router.get("/{product_key}", response_model=ProductResponse)
async def get_product(product_key: str):
    """
    Get single product by key
    """
    service = get_products_service()
    product = service.get_product_by_key(product_key)

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    return product_to_response(product)


@router.get("/{product_key}/image")
async def get_product_image(
    product_key: str,
    index: int = Query(1, ge=1, le=10, description="Image index (1-based)"),
):
    """
    Get product image by index (1-based).
    Default returns the first image.
    """
    service = get_products_service()
    product = service.get_product_by_key(product_key)
    image_folder = product.image_folder if product else None
    image_base64 = service.get_product_image_base64(product_key, image_folder, index=index)

    if not image_base64:
        raise HTTPException(status_code=404, detail="Image not found")

    import base64
    image_bytes = base64.b64decode(image_base64)

    return Response(
        content=image_bytes,
        media_type="image/jpeg",
        headers={"Cache-Control": "public, max-age=3600"},
    )


@router.post("/{product_key}/view")
async def track_product_view(
    product_key: str,
    clicked_link: bool = False,
    db: AsyncSession = Depends(get_db),
    user: CuratorUser = Depends(get_current_user),
):
    """
    Track product view for analytics

    - **product_key**: Product that was viewed
    - **clicked_link**: True if user clicked referral link
    """
    service = get_products_service()
    product = service.get_product_by_key(product_key)

    # Create view record
    view = ProductView(
        user_id=user.id,
        telegram_id=user.telegram_id,
        product_key=product_key,
        category=product.category if product else None,
        clicked_link=clicked_link,
        viewed_at=datetime.utcnow(),
    )
    db.add(view)

    # Update user stats
    user.products_viewed += 1

    await db.commit()

    return {"success": True}


@router.get("/links/referral")
async def get_referral_links():
    """
    Get all referral links for products
    """
    return {
        "registration": settings.referral_registration,
        "catalog": settings.referral_catalog,
        "promo": settings.referral_promo,
        "new_products": settings.referral_new_products,
        "starter_kits": settings.referral_starter_kits,
    }
