from datetime import date

import pytest

from pipeline.assignees import resolve_assignee
from pipeline.deadlines import normalize_deadline
from pipeline.extract import Candidates, Reviews, Summary, _chunks, extract
from pipeline.llm import LocalLLMError, OllamaLLM, validate_local_url
from pipeline.models import Participant, Segment
from pipeline.settings import PipelineSettings

DAY = date(2026, 9, 23)
PEOPLE = [Participant(id=1, name="Ерлан Нурланов"), Participant(id=2, name="Дана Ахметова")]
QUOTE = "Хорошо, пусть Ерлан до конца недели подготовит претензию."


def seg(text=QUOTE):
    return Segment(start=0, end=5, speaker="speaker1", text=text, lang="ru")


class FakeLLM:
    def __init__(self, quote=QUOTE, name="Ерлан", deadline_raw="до конца недели", is_task=True):
        self.quote, self.name, self.deadline_raw, self.is_task = quote, name, deadline_raw, is_task

    def complete(self, instruction, data, schema):
        if schema is Candidates:
            return Candidates(
                tasks=[
                    {
                        "segment_index": 0,
                        "quote": self.quote,
                        "text": "Подготовить претензию",
                        "assignee_name": self.name,
                        "assignee_quote": self.quote,
                        "assignee_segment_index": 0,
                        "deadline_raw": self.deadline_raw,
                    }
                ]
            )
        if schema is Reviews:
            return Reviews(
                reviews=[
                    {
                        "candidate_index": 0,
                        "is_task": self.is_task,
                        "deadline": "2030-01-01",
                        "urgency": "normal",
                        "direction": "Юридическое",
                        "confidence": 0.9,
                    }
                ]
            )
        assert schema is Summary
        return Summary(summary="Обсудили подготовку претензии.")


def run(llm, people=PEOPLE):
    return extract(
        [seg()],
        DAY,
        people,
        ["Юридическое", "Другое"],
        "ru",
        PipelineSettings(_env_file=None),
        llm=llm,
    )


def test_erlan_task_evidence_deadline_and_person():
    task = run(FakeLLM()).tasks[0]
    assert task.assignee_participant_id == 1
    assert task.deadline == date(2026, 9, 25)  # code overrides wrong model date
    assert task.quote == QUOTE and task.segment_index == 0


def test_absent_erlan_is_not_askhat_erlanovich():
    task = run(FakeLLM(), [Participant(id=9, name="Асхат Ерланович")]).tasks[0]
    assert task.assignee_name == "Ерлан" and task.assignee_participant_id is None


def test_hallucinated_full_name_cannot_disambiguate_two_erlans():
    task = run(
        FakeLLM(name="Ерлан Нурланов"), PEOPLE + [Participant(id=3, name="Ерлан Касымов")]
    ).tasks[0]
    assert task.assignee_name == "Ерлан" and task.assignee_participant_id is None


def test_fabricated_quote_rejected():
    result = run(FakeLLM(quote="Дана, подготовь отчёт завтра."))
    assert result.tasks == [] and result.rejected == 1


def test_fabricated_fields_repaired_only_from_literal_evidence():
    task = run(FakeLLM(name="Дана", deadline_raw="завтра")).tasks[0]
    assert task.assignee_participant_id == 1 and task.assignee_name == "Ерлан"
    assert task.deadline == date(2026, 9, 25) and task.deadline_raw == "до конца недели"


def test_review_can_reject_candidate():
    assert run(FakeLLM(is_task=False)).tasks == []


def test_missing_review_is_an_error_not_a_silent_empty_task_list():
    class IncompleteLLM(FakeLLM):
        def complete(self, instruction, data, schema):
            if schema is Reviews:
                assert data["candidates"][0]["candidate_index"] == 0
                return Reviews(reviews=[])
            return super().complete(instruction, data, schema)

    with pytest.raises(LocalLLMError, match="verification"):
        run(IncompleteLLM())


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("ертең", "2026-09-24"),
        ("завтра", "2026-09-24"),
        ("до пятницы", "2026-09-25"),
        ("до конца недели", "2026-09-25"),
        ("апта соңына дейін", "2026-09-25"),
        ("айдың соңына дейін", "2026-09-30"),
        ("келесі аптаға дейін", "2026-09-28"),
        ("через неделю", "2026-09-30"),
        ("бүрсігүні", "2026-09-25"),
        ("через 3 дня", "2026-09-26"),
        ("3 күннен кейін", "2026-09-26"),
        ("15.10.2026", "2026-10-15"),
        ("до среды", "2026-09-23"),
        ("келесі жұма", "2026-10-02"),
    ],
)
def test_deadlines(raw, expected):
    assert normalize_deadline(raw, DAY).isoformat() == expected


def test_ambiguous_date_and_invalid_date_are_not_invented():
    assert normalize_deadline("потом", DAY) is None
    assert normalize_deadline("31.02.2026", DAY) is None


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("за две недели", "2026-10-07"),
        ("За неделю", "2026-09-30"),
        ("на этой неделе", "2026-09-25"),
        ("за месяц", "2026-10-23"),
        ("не больше недели", "2026-09-30"),
        ("до конца следующей недели", "2026-10-02"),
        ("10 дней", "2026-10-03"),
        ("неделя максимум 10 дней", "2026-10-03"),
    ],
)
def test_recording_duration_regressions(raw, expected):
    assert normalize_deadline(raw, DAY).isoformat() == expected


def test_names_case_transliteration_and_ambiguity():
    assert resolve_assignee("Ерлану", PEOPLE) == 1
    assert resolve_assignee("Erlan", PEOPLE) == 1
    assert resolve_assignee("Дане", PEOPLE) == 2
    assert resolve_assignee("Дану", PEOPLE) == 2
    assert resolve_assignee("Ерлан", PEOPLE + [Participant(id=3, name="Ерлан Касымов")]) is None
    assert resolve_assignee("Ерлан Касымов", PEOPLE) is None
    assert resolve_assignee("Нурлан", [Participant(id=4, name="Нурланбек Садыков")]) is None
    assert (
        resolve_assignee("Батагос Нурлановна", [Participant(id=9, name="Батагус Нурлановна")]) == 9
    )
    assert resolve_assignee("Батагос", [Participant(id=9, name="Батагус Нурлановна")]) is None


def test_prompt_chunks_are_bounded_and_keep_indices():
    chunks = _chunks([seg("a" * 20000), seg("end")])
    assert len(chunks) > 1
    assert all(sum(len(s["text"]) + 80 for s in c) <= 8000 for c in chunks)
    assert chunks[-1][-1]["segment_index"] == 1


@pytest.mark.parametrize(
    "url",
    [
        "https://ollama.com",
        "http://8.8.8.8:11434",
        "http://169.254.169.254",
        "http://0.0.0.0",
        "http://user:pass@localhost:11434",
        "http://127.0.0.1:11434/api",
        "http://127.0.0.1:11434?host=evil",
    ],
)
def test_external_llm_origins_rejected(url):
    with pytest.raises(LocalLLMError):
        validate_local_url(url)


def test_cloud_model_rejected():
    with pytest.raises(LocalLLMError, match="Cloud"):
        OllamaLLM(PipelineSettings(_env_file=None, llm_model="qwen3-cloud"))


def test_cloud_proxy_not_sent_any_transcript(monkeypatch):
    import httpx

    calls = []

    class Client:
        def __init__(self, **kwargs):
            assert kwargs["trust_env"] is False and kwargs["follow_redirects"] is False

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def post(self, path, **kwargs):
            calls.append(path)
            return httpx.Response(
                200,
                json={"remote_host": "ollama.com"},
                request=httpx.Request("POST", "http://localhost"),
            )

    monkeypatch.setattr(httpx, "Client", Client)
    with pytest.raises(LocalLLMError, match="Remote"):
        OllamaLLM(PipelineSettings(_env_file=None)).complete("x", {"secret": "private"}, Summary)
    assert calls == ["/api/show"]
