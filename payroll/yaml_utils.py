from decimal import Decimal

from moneyed import Money


def decimal_constructor(loader, node):
    value = loader.construct_scalar(node)
    return Decimal(value)


def decimal_representer(dumper, value):
    v = '{0:.2f}'.format(value)
    return dumper.represent_scalar(u'!decimal', v)


def money_constructor(loader, node):
    value = loader.construct_scalar(node)
    [currency, amount] = value.split(" ", 1)
    return Money(Decimal(amount), currency)


def money_representer(dumper, value):
    return dumper.represent_scalar(U'!money', F"{value.currency} {value.amount}")


def enum_constructor(loader, node):
    value = loader.construct_scalar(node)
    return str(value)


def enum_representer(dumper, value):
    return dumper.represent_scalar(u'!enum', u'{.value}'.format(value))
