from pipeline.identity import Identities, identify_speakers
from pipeline.models import Participant, Segment, SpeakerMapping


def s(speaker, text, start):
    return Segment(start=start, end=start + 2, speaker=speaker, text=text, lang="ru")


PEOPLE = [Participant(id=7, name="Батагус Нурлановна")]
MAPPINGS = [
    SpeakerMapping(speaker=f"speaker{i}", participant_id=None, source="none", confidence=0)
    for i in (1, 2, 3)
]


class LLM:
    def __init__(self, quote="Начнем с Батагус Нурлановны.", response=1):
        self.quote, self.response = quote, response

    def complete(self, *args):
        return Identities(
            hints=[
                {
                    "name": "Батагус Нурлановны",
                    "evidence_index": 0,
                    "quote": self.quote,
                    "response_index": self.response,
                }
            ]
        )


def test_handoff_maps_next_substantive_voice():
    segments = [
        s("speaker1", "Начнем с Батагус Нурлановны.", 0),
        s("speaker2", "Спасибо. По нашему направлению подготовлен отчет.", 3),
    ]
    mapped, count = identify_speakers(segments, MAPPINGS, PEOPLE, LLM())
    assert mapped[1].participant_id == 7 and mapped[1].source == "llm" and count == 1
    assert mapped[0].participant_id is None


def test_task_recipient_does_not_identify_next_voice():
    quote = "Батагус Нурлановна, подготовьте отчет завтра."
    segments = [s("speaker1", quote, 0), s("speaker2", "Я теперь расскажу о бюджете.", 3)]
    mapped, _ = identify_speakers(segments, MAPPINGS, PEOPLE, LLM(quote))
    assert all(m.participant_id is None for m in mapped)


def test_dont_skip_actual_response_or_accept_short_acknowledgement():
    segments = [
        s("speaker1", "Начнем с Батагус Нурлановны.", 0),
        s("speaker2", "Да.", 3),
        s("speaker3", "Спасибо. Сейчас доложу о результатах.", 5),
    ]
    mapped, _ = identify_speakers(segments, MAPPINGS, PEOPLE, LLM())
    assert all(m.participant_id is None for m in mapped)
    mapped, _ = identify_speakers(segments, MAPPINGS, PEOPLE, LLM(response=2))
    assert mapped[2].participant_id == 7
    segments[1].text = "Спасибо. Сейчас доложу о результатах."
    mapped, _ = identify_speakers(segments, MAPPINGS, PEOPLE, LLM(response=2))
    assert all(m.participant_id is None for m in mapped)


def test_unknown_person_ambiguous_name_and_manual_mapping_preserved():
    segments = [
        s("speaker1", "Начнем с Батагус Нурлановны.", 0),
        s("speaker2", "Спасибо. Сейчас доложу о результатах.", 3),
    ]
    mapped, _ = identify_speakers(segments, MAPPINGS, [], LLM())
    assert all(m.participant_id is None for m in mapped)
    assert mapped[1].participant_name == "Батагус Нурлановны"
    assert mapped[1].source == "llm"  # backend creates the verified guest
    manual = [
        MAPPINGS[0],
        SpeakerMapping(speaker="speaker2", participant_id=9, source="manual", confidence=1),
    ]
    mapped, _ = identify_speakers(segments, manual, PEOPLE, LLM())
    assert mapped[1].participant_id == 9 and mapped[1].source == "manual"


def test_conflicting_handoffs_do_not_assign_the_cluster():
    segments = [
        s("speaker1", "Начнем с Батагус Нурлановны.", 0),
        s("speaker2", "Спасибо. Сейчас доложу о результатах.", 3),
        s("speaker1", "Ерлан, вам слово.", 7),
        s("speaker2", "По юридическому направлению подготовлена претензия.", 10),
    ]

    class ConflictingLLM:
        def complete(self, *args):
            return Identities(
                hints=[
                    {
                        "name": "Батагус Нурлановны",
                        "evidence_index": 0,
                        "quote": segments[0].text,
                        "response_index": 1,
                    },
                    {
                        "name": "Ерлан",
                        "evidence_index": 2,
                        "quote": segments[2].text,
                        "response_index": 3,
                    },
                ]
            )

    people = PEOPLE + [Participant(id=8, name="Ерлан")]
    mapped, count = identify_speakers(segments, MAPPINGS, people, ConflictingLLM())
    assert count == 2 and mapped[1].participant_id is None
