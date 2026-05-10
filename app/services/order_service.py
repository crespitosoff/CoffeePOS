# app/services/order_service.py
# COF-33: Backend – Servicio de gestión de órdenes
from __future__ import annotations

import decimal
from typing import List, Optional

from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.models.domain import (
    Order,
    OrderItem,
    OrderStatus,
    Product,
    StoreSetting,
    GenericStatus,
)


class OrderService:
    """Encapsula el ciclo de vida completo de una orden POS."""

    # ------------------------------------------------------------------
    # Helpers privados
    # ------------------------------------------------------------------

    @staticmethod
    def _get_tax_rate() -> decimal.Decimal:
        """Lee el porcentaje de impuesto desde store_settings (primer registro)."""
        setting = db.session.query(StoreSetting).first()
        if setting and setting.tax_percentage is not None:
            return decimal.Decimal(str(setting.tax_percentage)) / decimal.Decimal("100")
        return decimal.Decimal("0.19")  # 19 % por defecto (IVA Colombia)

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------

    @staticmethod
    def get_order_by_id(order_id: str) -> Optional[Order]:
        """Retorna una orden por su UUID o None."""
        return db.session.get(Order, order_id)

    @staticmethod
    def get_open_orders() -> List[Order]:
        """Retorna todas las órdenes en estado OPEN."""
        return (
            db.session.query(Order)
            .filter(Order.status == OrderStatus.OPEN)
            .order_by(Order.created_at.asc())
            .all()
        )

    @staticmethod
    def get_orders_by_session(register_session_id: str) -> List[Order]:
        """Retorna todas las órdenes asociadas a una sesión de caja."""
        return (
            db.session.query(Order)
            .filter(Order.register_session_id == register_session_id)
            .order_by(Order.created_at.asc())
            .all()
        )

    # ------------------------------------------------------------------
    # Ciclo de vida de la orden
    # ------------------------------------------------------------------

    @staticmethod
    def create_order(
        user_id: str,
        register_session_id: str,
        table_id: Optional[str] = None,
        customer_name: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Order:
        """
        Crea una nueva orden en estado OPEN.

        Parámetros:
            user_id              – UUID del cajero que crea la orden.
            register_session_id  – UUID de la sesión de caja activa (obligatorio).
            table_id             – UUID de la mesa (opcional para pedidos para llevar).
            customer_name        – Nombre del cliente (opcional).
            notes                – Notas adicionales (opcional).
        """
        if not user_id:
            raise ValueError("El ID de usuario es obligatorio para crear una orden.")
        if not register_session_id:
            raise ValueError(
                "Se requiere una sesión de caja activa para crear una orden."
            )

        try:
            order = Order(
                user_id=user_id,
                register_session_id=register_session_id,
                table_id=table_id,
                customer_name=customer_name,
                notes=notes,
                subtotal=decimal.Decimal("0"),
                tax=decimal.Decimal("0"),
                total=decimal.Decimal("0"),
                status=OrderStatus.OPEN,
            )
            db.session.add(order)
            db.session.commit()
            return order
        except SQLAlchemyError as e:
            db.session.rollback()
            raise RuntimeError(f"Error al crear la orden: {e}") from e

    @staticmethod
    def add_item_to_order(
        order_id: str,
        product_id: str,
        quantity: int,
        notes: Optional[str] = None,
    ) -> OrderItem:
        """
        Agrega un ítem a la orden.

        Valida:
            - La orden existe y está en estado OPEN.
            - El producto existe, está ACTIVE y tiene stock suficiente.
            - La cantidad es un entero positivo.

        Actualiza automáticamente subtotal/tax/total de la orden.
        """
        order = OrderService.get_order_by_id(order_id)
        if not order:
            raise ValueError("Orden no encontrada.")
        if order.status != OrderStatus.OPEN:
            raise ValueError(
                f"No se pueden agregar ítems a una orden en estado '{order.status.value}'."
            )

        if not isinstance(quantity, int) or quantity <= 0:
            raise ValueError("La cantidad debe ser un número entero positivo.")

        product: Optional[Product] = db.session.get(Product, product_id)
        if not product:
            raise ValueError("Producto no encontrado.")
        if product.status == GenericStatus.ARCHIVED:
            raise ValueError(f"El producto '{product.name}' está archivado.")
        if product.stock is not None and product.stock < quantity:
            raise ValueError(
                f"Stock insuficiente para '{product.name}'. "
                f"Disponible: {product.stock}, solicitado: {quantity}."
            )

        try:
            base_price = decimal.Decimal(str(product.price))
            qty_decimal = decimal.Decimal(quantity)
            item_subtotal = base_price * qty_decimal
            historical_cost = (
                decimal.Decimal(str(product.unit_cost))
                if product.unit_cost is not None
                else decimal.Decimal("0")
            )

            item = OrderItem(
                order_id=order_id,
                product_id=product_id,
                quantity=quantity,
                base_price=base_price,
                subtotal=item_subtotal,
                historical_cost=historical_cost * qty_decimal,
                notes=notes,
            )
            db.session.add(item)

            # Descontar stock
            product.stock = (product.stock or 0) - quantity

            # Recalcular totales de la orden
            OrderService._recalculate_totals(order)

            db.session.commit()
            return item
        except SQLAlchemyError as e:
            db.session.rollback()
            raise RuntimeError(f"Error al agregar ítem a la orden: {e}") from e

    @staticmethod
    def remove_item_from_order(order_item_id: str) -> bool:
        """
        Elimina un ítem de la orden y repone el stock del producto.
        Solo operaciones sobre órdenes en estado OPEN.
        """
        item: Optional[OrderItem] = db.session.get(OrderItem, order_item_id)
        if not item:
            raise ValueError("Ítem de orden no encontrado.")

        order = item.order
        if not order or order.status != OrderStatus.OPEN:
            raise ValueError(
                "Solo se pueden eliminar ítems de órdenes en estado 'open'."
            )

        try:
            # Reponer stock
            product: Optional[Product] = db.session.get(Product, item.product_id)
            if product and product.stock is not None:
                product.stock += item.quantity

            db.session.delete(item)
            OrderService._recalculate_totals(order)
            db.session.commit()
            return True
        except SQLAlchemyError as e:
            db.session.rollback()
            raise RuntimeError(f"Error al eliminar ítem: {e}") from e

    @staticmethod
    def update_item_quantity(order_item_id: str, new_quantity: int) -> OrderItem:
        """
        Actualiza la cantidad de un ítem existente ajustando stock y totales.
        Solo válido para órdenes en estado OPEN.
        """
        if not isinstance(new_quantity, int) or new_quantity <= 0:
            raise ValueError("La nueva cantidad debe ser un número entero positivo.")

        item: Optional[OrderItem] = db.session.get(OrderItem, order_item_id)
        if not item:
            raise ValueError("Ítem de orden no encontrado.")

        order = item.order
        if not order or order.status != OrderStatus.OPEN:
            raise ValueError(
                "Solo se puede modificar la cantidad en órdenes con estado 'open'."
            )

        product: Optional[Product] = db.session.get(Product, item.product_id)
        if not product:
            raise ValueError("Producto asociado no encontrado.")

        quantity_diff = new_quantity - item.quantity  # positivo → necesita más stock
        if quantity_diff > 0 and product.stock is not None and product.stock < quantity_diff:
            raise ValueError(
                f"Stock insuficiente para '{product.name}'. "
                f"Disponible: {product.stock}, adicional requerido: {quantity_diff}."
            )

        try:
            # Ajustar stock
            if product.stock is not None:
                product.stock -= quantity_diff

            # Actualizar ítem
            item.quantity = new_quantity
            base_price = decimal.Decimal(str(item.base_price))
            item.subtotal = base_price * decimal.Decimal(new_quantity)
            historical_cost_unit = (
                decimal.Decimal(str(product.unit_cost))
                if product.unit_cost is not None
                else decimal.Decimal("0")
            )
            item.historical_cost = historical_cost_unit * decimal.Decimal(new_quantity)

            OrderService._recalculate_totals(order)
            db.session.commit()
            return item
        except SQLAlchemyError as e:
            db.session.rollback()
            raise RuntimeError(f"Error al actualizar cantidad del ítem: {e}") from e

    @staticmethod
    def calculate_order_total(order_id: str) -> dict:
        """
        Calcula y persiste subtotal, tax y total de la orden.
        Retorna un dict con los tres valores como Decimal.
        """
        order = OrderService.get_order_by_id(order_id)
        if not order:
            raise ValueError("Orden no encontrada.")

        try:
            OrderService._recalculate_totals(order)
            db.session.commit()
            return {
                "subtotal": order.subtotal,
                "tax": order.tax,
                "total": order.total,
            }
        except SQLAlchemyError as e:
            db.session.rollback()
            raise RuntimeError(f"Error al calcular total de la orden: {e}") from e

    @staticmethod
    def cancel_order(order_id: str) -> Order:
        """
        Cancela una orden en estado OPEN o PREPARING, devolviendo el stock.
        No se puede cancelar una orden PAID o ya CANCELLED.
        """
        order = OrderService.get_order_by_id(order_id)
        if not order:
            raise ValueError("Orden no encontrada.")
        if order.status in (OrderStatus.PAID, OrderStatus.CANCELLED):
            raise ValueError(
                f"La orden ya está en estado '{order.status.value}' y no puede cancelarse."
            )

        try:
            # Reponer stock de cada ítem
            for item in order.order_items:
                product: Optional[Product] = db.session.get(Product, item.product_id)
                if product and product.stock is not None:
                    product.stock += item.quantity

            import datetime
            order.status = OrderStatus.CANCELLED
            order.closed_at = datetime.datetime.utcnow()
            db.session.commit()
            return order
        except SQLAlchemyError as e:
            db.session.rollback()
            raise RuntimeError(f"Error al cancelar la orden: {e}") from e

    # ------------------------------------------------------------------
    # Helpers internos
    # ------------------------------------------------------------------

    @staticmethod
    def _recalculate_totals(order: Order) -> None:
        """
        Recalcula subtotal, tax y total de la orden a partir de sus ítems.
        Opera exclusivamente con decimal.Decimal para evitar errores de tipo.
        """
        subtotal = decimal.Decimal("0")
        for item in order.order_items:
            subtotal += decimal.Decimal(str(item.subtotal))

        tax_rate = OrderService._get_tax_rate()
        tax = subtotal * tax_rate
        total = subtotal + tax

        order.subtotal = subtotal.quantize(decimal.Decimal("0.01"))
        order.tax = tax.quantize(decimal.Decimal("0.01"))
        order.total = total.quantize(decimal.Decimal("0.01"))
