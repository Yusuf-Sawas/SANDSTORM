# ZAVIQ
ZAVIQ is a phone-first smart development workspace. the long-term vision is project and file management, architecture planning, sourced technical research, error diagnosis, patch review, and export preparation.
this repository is at an early stage. It currently contains one small, real workflow:
**Dune planning workflow powered by an LLM**
```
prompt -> input validation -> real model request -> JSON -> pydantic validation -> saved JSON artifact
```
it is not a multi-agent system and it is not autonomous. the model is asked once for a structured plan, the result is validation, and the result is saved. Nothing the model suggests is executed or created on disk.

## Scope of this stage

Bulit:
- Python package `zaviq` (schemas, model client layer, Dune worklow, command-line entry point).
- Offline tests that need no network and no API Key.
- Github Actions: automatic offline tests, plus a manual live run.

Not built Yet:
- Fixer and Scout agnet.
- Any user interface.
- A permanent API or server.
- Database, hosting, deployment

## Offline tests vs. live model call

- **Offline tests**
ests_dune.py`) use a fake model client. They make no network calls and use no API key. Test data is fake and exists only inside the tests. Passing tests show that validation and error handling work. they do not show that a real model produces good plans.
- **Live run** is a manual Github Actions run that calls the real Gemini API with your key. only this proves the model integration works. Access to the Gemini API depends on your account, region, and model. It is not assumed.

## One-time setup on Github (works from a phone)

if you do not see the repository Settings tab, open the repository in your browser with "Desktop site" enabled.

1. repository -> Settings -> Secrets and variables -> Actions.
2. Tab **Secrets** -> New repository secret. Name: `GEMINI_API_KEY`. Paste your key into GitHub's from only. never put it in code, README, issues, chats, or workflow input.
3. Tab **Variables** -> New repository variable. Name: `GEMINI_MODEL`. Value: a model name that your own account can actually use (check it in Google Ai Studio). Do not guess a name.

## Run the tests form your phone

1. Commit or push any change to the repository.
2. Open the **Actions** tab -> the latest **ZAVIQ checks** run.
3. the job `tests` should be green. It uses no secrets.

## Run the live model tests manually

1. Actions tab -> **ZAVIQ chacks** ->> **Run workflow**.
2. Choose branch `main`, type a general, non-sensitive project idea in `prompt`, and run.
3. When the job `live-dune-run` succeeds, open the run page and download the artiface `dune-plan`. It is a zip file co