from unittest.mock import MagicMock

import pytest

from agents.editor import EditorAgent, EditResult, lost_facts

DRAFT = """# Halvard in 2026

The Halo floor lamp launches in September at €349 [1]. Halvard sold 412,000 lamps in 2025 [2].

1. Plug it in.
2. Hold the dial for 15 seconds.
"""


def test_lost_facts_finds_dropped_figures_and_citations():
    edited = "# Halvard in 2026\n\nHalvard sold 412,000 lamps in 2025 [2].\n\n- Plug it in.\n- Hold the dial for 15 seconds.\n"
    assert lost_facts(DRAFT, edited) == ["349", "[1]"]


def test_rewording_and_list_changes_are_not_losses():
    edited = ("# Halvard in 2026\n\nIn September the Halo floor lamp arrives, priced at €349 [1]. "
              "Lamp sales reached 412000 in 2025 [2].\n\n- Plug it in.\n- Hold the dial for 15 seconds.\n")
    assert lost_facts(DRAFT, edited) == []


@pytest.fixture
def editor(mocker):
    db = MagicMock()
    db.query.return_value = []
    mocker.patch("agents.editor.ChromaDBManager", return_value=db)
    return EditorAgent()


def test_editor_gets_findings(editor, mocker):
    invoke = mocker.patch.object(editor, "invoke", return_value=EditResult(content=DRAFT, changes=["ok"]))
    editor.edit(DRAFT, {"title": "t"}, findings="Halo costs €349 [1]")
    assert invoke.call_args.args[0]["findings"] == "Halo costs €349 [1]"
    assert invoke.call_count == 1


def test_editor_retries_once_when_facts_are_dropped(editor, mocker):
    dropped = DRAFT.replace(" at €349 [1]", "")
    invoke = mocker.patch.object(editor, "invoke", side_effect=[
        EditResult(content=dropped, changes=["trimmed"]),
        EditResult(content=DRAFT.replace("launches", "arrives"), changes=["kept facts"]),
    ])
    content, notes = editor.edit(DRAFT, {}, findings="f")
    assert invoke.call_count == 2
    assert "349" in invoke.call_args.args[0]["extra"] and "[1]" in invoke.call_args.args[0]["extra"]
    assert "arrives" in content
    assert notes == "- kept facts"


def test_editor_falls_back_to_draft_when_retry_still_drops(editor, mocker):
    dropped = DRAFT.replace(" at €349 [1]", "")
    mocker.patch.object(editor, "invoke", return_value=EditResult(content=dropped, changes=["trimmed"]))
    content, notes = editor.edit(DRAFT, {}, findings="f")
    assert content == DRAFT
    assert "Kept the writer's draft" in notes and "349" in notes
