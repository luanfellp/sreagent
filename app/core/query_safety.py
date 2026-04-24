from collections.abc import Mapping


def escape_label_value(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace("\n", "\\n")
        .replace('"', '\\"')
    )


def build_label_matchers(labels: Mapping[str, str]) -> str:
    matchers: list[str] = []
    for key, value in labels.items():
        matchers.append(f'{key}="{escape_label_value(str(value))}"')
    return ",".join(matchers)
