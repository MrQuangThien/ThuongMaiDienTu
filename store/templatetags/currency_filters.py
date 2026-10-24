from django import template

register = template.Library()

@register.filter
def vnd(value):
    try:
        return f"{int(value):,}".replace(",", ".") + "đ"
    except (ValueError, TypeError):
        return values