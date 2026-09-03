from app.agent.schemas import LessonContent


def _collect_empty_items_paths(schema: object, path: tuple[str, ...] = ()) -> list[str]:
    paths: list[str] = []
    if isinstance(schema, dict):
        items = schema.get("items")
        if items == {}:
            paths.append(".".join((*path, "items")))
        for key, value in schema.items():
            paths.extend(_collect_empty_items_paths(value, (*path, str(key))))
    elif isinstance(schema, list):
        for index, value in enumerate(schema):
            paths.extend(_collect_empty_items_paths(value, (*path, str(index))))
    return paths


def test_generated_test_case_uses_typed_json_values():
    schema = LessonContent.model_json_schema()
    generated_test_case = schema["$defs"]["GeneratedTestCase"]["properties"]

    assert generated_test_case["input"]["items"] == {"$ref": "#/$defs/JsonValue"}
    assert generated_test_case["expected_output"]["$ref"] == "#/$defs/JsonValue"


def test_lesson_content_schema_has_no_untyped_array_items():
    schema = LessonContent.model_json_schema()

    # OpenAI structured output rejects schemas with bare `items: {}`.
    assert _collect_empty_items_paths(schema) == []
