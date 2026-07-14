# 当前项目结构

backend/

├── app/
│
├── core/
│   ├── config.py
│   └── logger.py
│
├── prompts/
│   ├── prompt_manager.py
│   └── templates/
│
├── schemas/
│   ├── chat.py
│   ├── resume.py
│   ├── jd.py
│   └── match.py
│
├── services/
│   ├── base_service.py
│   ├── llm_service.py
│   ├── resume_service.py
│   ├── jd_service.py
│   └── match_service.py
│
└── tests/
    ├── test_resume_service.py
    ├── test_jd_service.py
    └── test_match_service.py