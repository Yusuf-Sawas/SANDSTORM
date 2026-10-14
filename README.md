# ZAVIQ
ZAVIQ is a phone-first smart development workspace. the long-term vision is project and file management, architecture planning, sourced technical research, error diagnosis, patch review, and export preparation.
this repository is at an early stage. It currently contains one small, real workflow:
**Dune planning workflow powered by an LLM**
```
prompt -> input validation -> real model request -> JSON -> pydantic validation -> saved JSON artifact
```
it is not a multi-agent system and it is not autonomous. the model is asked once for a structured plan, the result is validation, and the result is saved. Nothing the model suggests is executed or created on disk.
