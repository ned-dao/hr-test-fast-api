from app.services.search_service import SearchService


def test_sanitize_allowed_columns_filters_unknown_and_keeps_id_first() -> None:
    cols = ["password", "name", "id", "email", "name", "__hack__"]
    sanitized = SearchService._sanitize_allowed_columns(cols)

    assert sanitized[0] == "id"
    assert "password" not in sanitized
    assert "__hack__" not in sanitized
    assert sanitized.count("name") == 1
