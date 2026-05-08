from app.extensions import db
from app.models.domain import Product, GenericStatus
from sqlalchemy.exc import SQLAlchemyError
from typing import List, Optional

class ProductService:
    @staticmethod
    def get_all_products(category_id: str = None, is_active: bool = True) -> List[Product]:
        query = db.session.query(Product)
        
        if is_active:
            query = query.filter(Product.status == GenericStatus.ACTIVE)
            
        if category_id:
            query = query.filter(Product.category_id == category_id)
            
        return query.order_by(Product.name.asc()).all()

    @staticmethod
    def get_product_by_id(product_id: str) -> Optional[Product]:
        return db.session.get(Product, product_id)

    @staticmethod
    def create_product(data: dict) -> Product:
        try:
            product = Product(
                name=data.get('name'),
                price=data.get('price'),
                category_id=data.get('category_id'),
                sku=data.get('sku'),
                description=data.get('description'),
                unit_cost=data.get('unit_cost', 0),
                stock=data.get('stock', 0),
                min_stock=data.get('min_stock', 0),
                image_url=data.get('image_url')
            )
            db.session.add(product)
            db.session.commit()
            return product
        except SQLAlchemyError as e:
            db.session.rollback()
            raise RuntimeError(f"Error al crear producto: {str(e)}")

    @staticmethod
    def update_product(product_id: str, data: dict) -> Product:
        product = ProductService.get_product_by_id(product_id)
        if not product:
            raise ValueError("Producto no encontrado.")

        try:
            # Actualizar solo los campos permitidos y proporcionados
            updateable_fields = ['name', 'price', 'category_id', 'sku', 'description', 
                                 'unit_cost', 'stock', 'min_stock', 'image_url', 'status']
            
            for field in updateable_fields:
                if field in data:
                    # Parsear status si viene como string
                    if field == 'status' and isinstance(data[field], str):
                        setattr(product, field, GenericStatus(data[field]))
                    else:
                        setattr(product, field, data[field])

            db.session.commit()
            return product
        except SQLAlchemyError as e:
            db.session.rollback()
            raise RuntimeError(f"Error al actualizar producto: {str(e)}")

    @staticmethod
    def delete_product(product_id: str) -> bool:
        product = ProductService.get_product_by_id(product_id)
        if not product:
            raise ValueError("Producto no encontrado.")
            
        try:
            # Borrado lógico
            product.status = GenericStatus.ARCHIVED
            db.session.commit()
            return True
        except SQLAlchemyError as e:
            db.session.rollback()
            raise RuntimeError(f"Error al eliminar producto: {str(e)}")

    @staticmethod
    def update_stock(product_id: str, quantity_change: int) -> Product:
        product = ProductService.get_product_by_id(product_id)
        if not product:
            raise ValueError("Producto no encontrado.")
            
        try:
            product.stock += quantity_change
            db.session.commit()
            return product
        except SQLAlchemyError as e:
            db.session.rollback()
            raise RuntimeError(f"Error al actualizar stock: {str(e)}")