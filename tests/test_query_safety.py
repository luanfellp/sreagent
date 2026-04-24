from app.core.query_safety import build_label_matchers, escape_label_value


def test_escape_label_value_escapes_quotes_backslashes_and_newlines() -> None:
    value = 'checkout"prod\\blue\nnext'
    escaped = escape_label_value(value)

    assert escaped == 'checkout\\"prod\\\\blue\\nnext'


def test_build_label_matchers_quotes_each_value_safely() -> None:
    matchers = build_label_matchers(
        {
            "service": 'checkout"prod',
            "environment": "prod\\blue",
        }
    )

    assert matchers == 'service="checkout\\"prod",environment="prod\\\\blue"'
