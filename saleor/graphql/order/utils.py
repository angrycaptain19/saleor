from django.core.exceptions import ValidationError

from ...core.exceptions import InsufficientStock
from ...order.error_codes import OrderErrorCode
from ...product.models import Product
from ...warehouse.availability import check_stock_quantity


def validate_total_quantity(order):
    if order.get_total_quantity() == 0:
        raise ValidationError(
            {
                "lines": ValidationError(
                    "Could not create order without any products.",
                    code=OrderErrorCode.REQUIRED,
                )
            }
        )


def validate_shipping_method(order):
    method = order.shipping_method
    shipping_address = order.shipping_address
    shipping_not_valid = (
        method
        and shipping_address
        and shipping_address.country.code not in method.shipping_zone.countries
    )  # noqa
    if shipping_not_valid:
        raise ValidationError(
            {
                "shipping": ValidationError(
                    "Shipping method is not valid for chosen shipping address",
                    code=OrderErrorCode.SHIPPING_METHOD_NOT_APPLICABLE,
                )
            }
        )


def validate_order_lines(order, country):
    for line in order:
        if line.variant is None:
            raise ValidationError(
                {
                    "lines": ValidationError(
                        "Could not create orders with non-existing products.",
                        code=OrderErrorCode.NOT_FOUND,
                    )
                }
            )
        if line.variant.track_inventory:
            try:
                check_stock_quantity(line.variant, country, line.quantity)
            except InsufficientStock as exc:
                raise ValidationError(
                    {
                        "lines": ValidationError(
                            f"Insufficient product stock: {exc.item}",
                            code=OrderErrorCode.INSUFFICIENT_STOCK,
                        )
                    }
                )


def validate_product_is_published(order):
    variant_ids = []
    for line in order:
        variant_ids.append(line.variant_id)
    unpublished_product = Product.objects.filter(
        variants__id__in=variant_ids
    ).not_published(order.channel.slug)
    if unpublished_product.exists():
        raise ValidationError(
            {
                "lines": ValidationError(
                    "Can't finalize draft with unpublished product.",
                    code=OrderErrorCode.PRODUCT_NOT_PUBLISHED,
                )
            }
        )


def validate_product_is_available_for_purchase(order):
    for line in order:
        if not line.variant.product.is_available_for_purchase():
            raise ValidationError(
                {
                    "lines": ValidationError(
                        "Can't finalize draft with product unavailable for purchase.",
                        code=OrderErrorCode.PRODUCT_UNAVAILABLE_FOR_PURCHASE,
                    )
                }
            )


def validate_channel_is_active(channel):
    if not channel.is_active:
        raise ValidationError(
            {
                "channel": ValidationError(
                    "Cannot complete draft order with inactive channel.",
                    code=OrderErrorCode.CHANNEL_INACTIVE.value,
                )
            }
        )


def validate_draft_order(order, country):
    """Check if the given order contains the proper data.

    - Has proper customer data,
    - Shipping address and method are set up,
    - Product variants for order lines still exists in database.
    - Product variants are available in requested quantity.
    - Product variants are published.

    Returns a list of errors if any were found.
    """
    if order.is_shipping_required():
        validate_shipping_method(order)
    validate_total_quantity(order)
    validate_order_lines(order, country)
    validate_product_is_published(order)
    validate_product_is_available_for_purchase(order)
    validate_channel_is_active(order.channel)
