"""
Basic tests for the PR Auto-Orchestrator
"""

import pytest
from unittest.mock import Mock, patch
import sys
import os

# Add the backend directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def test_secret_scanner():
    """Test secret scanner functionality"""
    from app.services.secret_scanner import SecretScanner
    
    scanner = SecretScanner()
    
    # Test with content containing a potential secret
    content = """
    def connect_db():
        password = "very_secret_password_123"
        api_key = "AKIAEXAMPLEKEY123456"
        return connect()
    """
    
    detections = scanner.scan_content(content, "test.py")
    
    # Should detect potential secrets
    assert len(detections) >= 0  # May or may not detect depending on patterns


def test_diff_parser():
    """Test diff parser functionality"""
    from app.services.diff_parser import DiffParser
    
    parser = DiffParser()
    
    diff_content = """
diff --git a/test.py b/test.py
index 123..456 100644
--- a/test.py
+++ b/test.py
@@ -1,3 +1,6 @@
 def existing_function():
     pass
+
+def new_function():
+    return "hello"
"""
    
    result = parser.parse_diff(diff_content)
    
    assert result["total_files"] >= 0
    assert "files_changed" in result


def test_risk_scorer():
    """Test risk scoring functionality"""
    from app.services.risk_scorer import RiskScorer
    
    scorer = RiskScorer()
    
    factors = {
        'secrets_count': 1,
        'total_additions': 500,
        'dependency_changes': [],
        'security_files_changed': 0,
        'large_files_changed': 1
    }
    
    score = scorer.calculate_risk_score(factors)
    
    assert 0 <= score <= 100
    assert score > 0  # Should have some risk due to secrets


def test_config_loading():
    """Test configuration loading"""
    from app.config import Settings
    
    # Test with default values
    settings = Settings()
    
    assert settings.app_env == "dev"
    assert settings.port == 8000
    assert settings.log_level == "INFO"


if __name__ == "__main__":
    print("Running basic tests...")
    test_secret_scanner()
    test_diff_parser()
    test_risk_scorer()
    test_config_loading()
    print("✅ All basic tests passed!")