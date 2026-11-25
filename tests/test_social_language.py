from graph.workflow import create_content_workflow, initialize_state


def run(settings):
    app = create_content_workflow(checkpointer="memory")
    config = {"configurable": {"thread_id": "social-lang"}}
    list(app.stream(initialize_state("green tea", settings), config=config))
    return app.get_state(config).values


def test_social_posts_follow_the_translation_language(fake_agents):
    state = run({"word_count": 50, "languages": ["Nepali"]})
    assert state["social_media_posts"] == {"linkedin": "post in Nepali"}
    assert state["social_media_posts_by_language"] == {"Nepali": {"linkedin": "post in Nepali"}}


def test_one_set_of_posts_per_language(fake_agents):
    state = run({"word_count": 50, "languages": ["Nepali", "Spanish"]})
    assert list(state["social_media_posts_by_language"]) == ["Nepali", "Spanish"]


def test_social_posts_default_to_english(fake_agents):
    state = run({"word_count": 50})
    assert state["social_media_posts_by_language"] == {"English": {"linkedin": "post in English"}}
