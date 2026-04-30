from app.models import Product, Category, GenericStatus
from app.extensions import db

class ProductService:
    @staticmethod
    def get_full_menu():
        # 1. Obtener todas las categorías
        categories = db.session.query(Category).all()
        
        # 2. Obtener productos activos usando la columna correcta y el Enum
        active_products = db.session.query(Product).filter(
            Product.status == GenericStatus.ACTIVE
        ).all()
        
        # 3. Serialización: Estructurar los datos en diccionarios anidados
        menu_data = []
        for category in categories:
            # Filtrar en memoria los productos que pertenecen a esta categoría
            category_products = [p for p in active_products if p.category_id == category.id]
            
            # Evitar enviar categorías vacías al frontend
            if not category_products:
                continue
                
            menu_data.append({
                "category_id": str(category.id),
                "category_name": category.name,
                "products": [
                    {
                        "product_id": str(product.id),
                        "name": product.name,
                        "price": float(product.price),
                        "sku": product.sku
                    } for product in category_products
                ]
            })
            
        return menu_data