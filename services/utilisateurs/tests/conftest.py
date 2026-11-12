import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_sentransport.db")
os.environ.setdefault("JWT_SECRET", "tests-only-secret-with-more-than-32-characters")
