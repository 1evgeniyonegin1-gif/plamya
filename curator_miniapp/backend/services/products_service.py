"""
Products Service

Работа с каталогом продуктов NL International
"""
import json
import base64
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field


@dataclass
class Product:
    """Product data"""
    key: str
    name: str
    price: int
    pv: float
    category: str
    price_per_portion: Optional[float] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    image_folder: Optional[str] = None
    referral_link: Optional[str] = None
    line: Optional[str] = None
    image_count: int = 0


@dataclass
class ProductsResponse:
    """Response for products list"""
    total: int
    categories: list[str]
    products: list[Product]


class ProductsService:
    """
    Service for working with NL products catalog
    """

    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.products_db_path = self.project_root / "content" / "products_database.json"
        self.media_path = self.project_root / "content" / "unified_products"
        self.line_photos_path = self.project_root / "content" / "line_photos"
        self._products: Optional[dict] = None

    def load_products(self) -> dict:
        """Load products from JSON database"""
        if self._products is None:
            with open(self.products_db_path, encoding="utf-8") as f:
                self._products = json.load(f)
        return self._products

    def get_categories(self) -> list[str]:
        """Get list of product categories"""
        data = self.load_products()
        return list(data.get("categories", {}).keys())

    @staticmethod
    def _line_name_to_slug(name: str) -> str:
        """Convert line name to filesystem-safe slug."""
        import re
        slug = name.lower().strip().replace(" ", "_")
        slug = re.sub(r"[^\w.]", "", slug, flags=re.UNICODE)
        return slug

    def _get_line_image_url(self, line_name: str) -> Optional[str]:
        """Get image URL for a product line, if photo exists."""
        slug = self._line_name_to_slug(line_name)
        photo_path = self.line_photos_path / f"{slug}.jpg"
        if photo_path.exists():
            return f"/api/v1/products/lines/{slug}/image"
        return None

    def get_line_image_bytes(self, line_slug: str) -> Optional[bytes]:
        """Get line photo as bytes by slug."""
        photo_path = self.line_photos_path / f"{line_slug}.jpg"
        if photo_path.exists():
            return photo_path.read_bytes()
        return None

    def get_lines(self, category: Optional[str] = None) -> list[dict]:
        """Get list of product lines with counts, optionally filtered by category."""
        data = self.load_products()
        lines_count: dict[str, int] = {}

        for cat_name, cat_products in data.get("categories", {}).items():
            if category and cat_name.lower() != category.lower():
                continue
            for p in cat_products:
                line = p.get("line", "")
                if line:
                    lines_count[line] = lines_count.get(line, 0) + 1

        return [
            {"name": name, "product_count": count, "image_url": self._get_line_image_url(name)}
            for name, count in sorted(lines_count.items(), key=lambda x: -x[1])
        ]

    def get_products(
        self,
        category: Optional[str] = None,
        search: Optional[str] = None,
        line: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> ProductsResponse:
        """
        Get products with optional filtering

        Args:
            category: Filter by category name
            search: Search in product name
            limit: Maximum products to return
            offset: Skip first N products

        Returns:
            ProductsResponse with products list
        """
        data = self.load_products()
        all_products: list[Product] = []

        for cat_name, cat_products in data.get("categories", {}).items():
            # Filter by category
            if category and cat_name.lower() != category.lower():
                continue

            for product_data in cat_products:
                # Filter by search
                if search and search.lower() not in product_data["name"].lower():
                    continue

                # Filter by line
                if line and product_data.get("line", "").lower() != line.lower():
                    continue

                product_key = product_data.get("key", "")
                image_folder = product_data.get("image_folder")
                product = Product(
                    key=product_key,
                    name=product_data["name"],
                    price=product_data.get("price", 0),
                    pv=product_data.get("pv", 0),
                    category=product_data.get("category", cat_name),
                    price_per_portion=product_data.get("price_per_portion"),
                    description=product_data.get("description") or f"Категория: {cat_name}",
                    image_url=self._get_product_image_url(product_key, image_folder),
                    image_folder=image_folder,
                    referral_link=product_data.get("referral_link"),
                    line=product_data.get("line"),
                    image_count=product_data.get("image_count", 0),
                )
                all_products.append(product)

        # Apply pagination
        paginated = all_products[offset:offset + limit]

        return ProductsResponse(
            total=len(all_products),
            categories=self.get_categories(),
            products=paginated,
        )

    def get_product_by_key(self, product_key: str) -> Optional[Product]:
        """
        Get single product by key

        Args:
            product_key: Product unique key

        Returns:
            Product if found, None otherwise
        """
        data = self.load_products()

        for cat_name, cat_products in data.get("categories", {}).items():
            for product_data in cat_products:
                if product_data.get("key") == product_key:
                    image_folder = product_data.get("image_folder")
                    return Product(
                        key=product_data.get("key", ""),
                        name=product_data["name"],
                        price=product_data.get("price", 0),
                        pv=product_data.get("pv", 0),
                        category=product_data.get("category", cat_name),
                        price_per_portion=product_data.get("price_per_portion"),
                        description=product_data.get("description") or f"Категория: {cat_name}",
                        image_url=self._get_product_image_url(product_key, image_folder),
                        image_folder=image_folder,
                        referral_link=product_data.get("referral_link"),
                        line=product_data.get("line"),
                        image_count=product_data.get("image_count", 0),
                    )

        return None

    def _get_photos_dir(self, image_folder: Optional[str]) -> Optional[Path]:
        """Get photos directory for a product"""
        if not image_folder:
            return None
        photos_dir = self.media_path / image_folder / "photos"
        if photos_dir.exists():
            return photos_dir
        return None

    def _get_product_image_url(self, product_key: str, image_folder: Optional[str] = None) -> Optional[str]:
        """Get image URL for product"""
        photos_dir = self._get_photos_dir(image_folder)
        if photos_dir and list(photos_dir.glob("*.jpg")):
            return f"/api/v1/products/{product_key}/image"
        return None

    def get_product_image_base64(self, product_key: str, image_folder: Optional[str] = None, index: int = 1) -> Optional[str]:
        """Get product image as base64 string. index is 1-based."""
        photos_dir = self._get_photos_dir(image_folder)
        if not photos_dir:
            return None

        target = photos_dir / f"{index}.jpg"
        if target.exists():
            try:
                with open(target, "rb") as f:
                    return base64.b64encode(f.read()).decode()
            except Exception:
                return None
        return None

    def search_products(self, query: str, limit: int = 10) -> list[Product]:
        """
        Search products by query

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            List of matching products
        """
        response = self.get_products(search=query, limit=limit)
        return response.products


# Singleton instance
_products_service: Optional[ProductsService] = None


def get_products_service() -> ProductsService:
    """Get or create ProductsService singleton"""
    global _products_service
    if _products_service is None:
        _products_service = ProductsService()
    return _products_service
