from app.agent.schemas import GeneratedTestCase, LessonContent

_TYPE_KEYS = {"type", "anyOf", "oneOf", "allOf"}


def _resolve_ref(node: dict, defs: dict[str, object]) -> dict:
    ref = node.get("$ref")
    if not isinstance(ref, str):
        return node
    name = ref.rsplit("/", 1)[-1]
    resolved = defs.get(name)
    if not isinstance(resolved, dict):
        return node
    extra = {key: value for key, value in node.items() if key != "$ref"}
    merged = {**resolved, **extra}
    return _resolve_ref(merged, defs)


def _collect_untyped_schema_paths(
    schema: object,
    path: tuple[str, ...] = (),
    defs: dict[str, object] | None = None,
) -> list[str]:
    """Find property/items schemas that OpenAI would reject for missing type."""
    paths: list[str] = []
    if not isinstance(schema, dict):
        if isinstance(schema, list):
            for index, value in enumerate(schema):
                paths.extend(
                    _collect_untyped_schema_paths(value, (*path, str(index)), defs)
                )
        return paths

    active_defs = defs if defs is not None else schema.get("$defs", {})
    if not isinstance(active_defs, dict):
        active_defs = {}

    properties = schema.get("properties")
    if isinstance(properties, dict):
        for name, value in properties.items():
            if isinstance(value, dict):
                resolved = _resolve_ref(value, active_defs)
                if not _TYPE_KEYS.intersection(resolved):
                    paths.append(".".join((*path, "properties", name)))
                paths.extend(
                    _collect_untyped_schema_paths(
                        resolved, (*path, "properties", name), active_defs
                    )
                )

    items = schema.get("items")
    if isinstance(items, dict):
        resolved_items = _resolve_ref(items, active_defs)
        if not _TYPE_KEYS.intersection(resolved_items):
            paths.append(".".join((*path, "items")))
        paths.extend(
            _collect_untyped_schema_paths(resolved_items, (*path, "items"), active_defs)
        )

    for key in ("anyOf", "oneOf", "allOf"):
        variants = schema.get(key)
        if isinstance(variants, list):
            for index, value in enumerate(variants):
                paths.extend(
                    _collect_untyped_schema_paths(
                        value, (*path, key, str(index)), active_defs
                    )
                )

    defs_node = schema.get("$defs")
    if path == () and isinstance(defs_node, dict):
        for name, value in defs_node.items():
            paths.extend(
                _collect_untyped_schema_paths(value, ("$defs", name), active_defs)
            )

    return paths


def test_generated_test_case_schema_uses_json_encoded_strings():
    schema = LessonContent.model_json_schema()
    generated_test_case = schema["$defs"]["GeneratedTestCase"]["properties"]

    assert generated_test_case["input"]["type"] == "array"
    assert generated_test_case["input"]["items"]["type"] == "string"
    assert generated_test_case["expected_output"]["type"] == "string"
    assert "JsonValue" not in schema.get("$defs", {})


def test_lesson_content_schema_properties_and_items_have_types():
    schema = LessonContent.model_json_schema()

    # OpenAI structured output rejects property/items nodes with no `type`
    # (including `$ref` to an empty JsonValue definition).
    assert _collect_untyped_schema_paths(schema) == []


def test_generated_test_case_accepts_native_json_values():
    case = GeneratedTestCase(input=[1, "hello", True], expected_output=None)
    assert case.input == [1, "hello", True]
    assert case.expected_output is None


def test_generated_test_case_parses_json_encoded_strings():
    case = GeneratedTestCase.model_validate(
        {
            "input": ["1", '"hello"', "true", "[1, 2]"],
            "expected_output": '{"ok": true}',
        }
    )
    assert case.input == [1, "hello", True, [1, 2]]
    assert case.expected_output == {"ok": True}
