from backend.services import extraction


def test_extract_profession_fact():
    facts = extraction.extract_facts("я работаю системным администратором в компании Альфа")
    assert any(f.key == "profession" for f in facts)


def test_extract_age_fact():
    facts = extraction.extract_facts("мне 27, живу в Минске")
    assert any(f.key == "age" and f.value == "27" for f in facts)


def test_detect_user_initiated_work_access():
    hits = extraction.detect_user_initiated_flags("у меня есть доступ к серверу на работе")
    assert any(h["code"] == "WORK_ACCESS_DISCLOSED" for h in hits)


def test_real_credential_like_content_blocked():
    assert extraction.contains_real_credential_like_content("вот мой пароль: Sup3rSecret!")
    assert extraction.contains_real_credential_like_content("моя карта 4111111111111111")
    assert not extraction.contains_real_credential_like_content("привет, как твои дела?")


def test_classify_boundary_response():
    assert extraction.classify_boundary_response("да, конечно давай") == "accept"
    assert extraction.classify_boundary_response("нет, не хочу") == "refuse"
    assert extraction.classify_boundary_response("мне кажется ты мошенница") == "suspicious"
    assert extraction.classify_boundary_response("ну не знаю, посмотрим") == "ambiguous"
