# policy_config.py

ROLE_POLICIES = {
    "backend": {
        "shortlist_threshold": 0.65,
        "resume_min": 0.5,
        "resume_critical": 0.2,
        "github_min": 0.4,
        "leetcode_min": 0.4,
    },
    "frontend": {
        "shortlist_threshold": 0.6,
        "resume_min": 0.5,
        "resume_critical": 0.2,
        "github_min": 0.3,
        "leetcode_min": 0.2,
    },
    "default": {
        "shortlist_threshold": 0.6,
        "resume_min": 0.5,
        "resume_critical": 0.2,
        "github_min": 0.4,
        "leetcode_min": 0.4,
    }
}
