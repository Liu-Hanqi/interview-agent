import json
from pathlib import Path

SCHEMA_KEYS = {"id", "pool", "category", "difficulty", "seed", "knowledge_anchors"}


def test_all_question_files_are_valid_json():
    questions_dir = Path(__file__).parent.parent / "questions"
    if not questions_dir.exists():
        return
    for pool_dir in questions_dir.iterdir():
        if not pool_dir.is_dir():
            continue
        for json_file in pool_dir.rglob("*.json"):
            with open(json_file) as f:
                data = json.load(f)
            # data is a list of question dicts
            for item in data:
                missing = SCHEMA_KEYS - set(item.keys())
                assert not missing, f"{json_file} missing keys: {missing}"


def test_question_ids_are_unique():
    questions_dir = Path(__file__).parent.parent / "questions"
    if not questions_dir.exists():
        return
    ids = []
    for pool_dir in questions_dir.iterdir():
        if not pool_dir.is_dir():
            continue
        for json_file in pool_dir.rglob("*.json"):
            with open(json_file) as f:
                data = json.load(f)
            for item in data:
                ids.append(item["id"])
    assert len(ids) == len(set(ids)), f"duplicate ids: {set([x for x in ids if ids.count(x)>1])}"