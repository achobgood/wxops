import json
from wxcli.output import format_as_json, _resolve_accessor

def test_format_json_list():
    data = [{"id": "1", "name": "Test"}]
    result = format_as_json(data)
    parsed = json.loads(result)
    assert parsed == [{"id": "1", "name": "Test"}]

def test_format_json_single():
    data = {"id": "1", "name": "Test"}
    result = format_as_json(data)
    parsed = json.loads(result)
    assert parsed == {"id": "1", "name": "Test"}

def test_resolve_accessor_dict():
    data = {"name": "Wilmington", "address": {"city": "Wilmington"}}
    assert _resolve_accessor(data, "name") == "Wilmington"
    assert _resolve_accessor(data, "address.city") == "Wilmington"

def test_resolve_accessor_missing():
    data = {"name": "Test"}
    assert _resolve_accessor(data, "nonexistent") is None
    assert _resolve_accessor(data, "a.b.c") is None

def test_resolve_accessor_list():
    data = {"emails": ["a@b.com", "c@d.com"]}
    assert _resolve_accessor(data, "emails") == "a@b.com"

class FakeObj:
    def __init__(self):
        self.name = "Test"
        self.nested = type("N", (), {"city": "Wilmington"})()

def test_resolve_accessor_object():
    obj = FakeObj()
    assert _resolve_accessor(obj, "name") == "Test"
    assert _resolve_accessor(obj, "nested.city") == "Wilmington"
