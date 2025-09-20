# DevOps Pull Request Auto-Orchestrator

An intelligent GitHub App that automatically analyzes Pull Requests and provides comprehensive insights including security scanning, test suggestions, and review checklists.

## 🚀 Features

### Multi-Agent Analysis Pipeline
- **Repository Scanner**: Analyzes code changes, generates summaries, and categorizes changes
- **Risk & Security Agent**: Detects secrets, analyzes dependency changes, and calculates risk scores
- **Test Synthesizer**: Suggests missing test cases based on code changes
- **Reviewer Agent**: Generates comprehensive review checklists

### Key Capabilities
- ✅ Automatic PR analysis on open/synchronize events
- 🔐 Secret detection and security risk assessment
- 📊 Dependency change analysis with risk scoring
- 🧪 Intelligent test case suggestions
- ✅ Comprehensive review checklists
- 📝 Structured Markdown comments on PRs
- 🔄 Asynchronous processing with Redis queues
- 📈 Configurable risk scoring system

## 🏗️ Architecture

```
GitHub Webhook → FastAPI → Redis Queue → Multi-Agent Pipeline → PR Comment
                     ↓
                PostgreSQL (Analysis Storage)
```

### Components
- **FastAPI Web Service**: Handles webhooks and serves API
- **RQ Worker**: Processes analysis jobs asynchronously  
- **PostgreSQL**: Stores analysis results and metadata
- **Redis**: Task queue and caching
- **Multi-Agent System**: Specialized analysis modules

## 🛠️ Quick Start

### Prerequisites
- Docker and Docker Compose
- GitHub App credentials (for production)

### Local Development Setup

1. **Clone and Setup**
   ```bash
   git clone <repository-url>
   cd nikhilnagar503
   chmod +x scripts/setup.sh
   ./scripts/setup.sh
   ```

2. **Configure Environment**
   ```bash
   cp config/example.env .env
   # Edit .env with your GitHub App credentials
   ```

3. **Start Services**
   ```bash
   docker-compose up --build
   ```

4. **Verify Installation**
   - API: http://localhost:8000
   - Docs: http://localhost:8000/docs
   - Health: http://localhost:8000/healthz

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GITHUB_APP_ID` | GitHub App ID | Required |
| `GITHUB_PRIVATE_KEY_BASE64` | Base64 encoded private key | Required |
| `GITHUB_WEBHOOK_SECRET` | Webhook secret | Required |
| `OPENAI_API_KEY` | OpenAI API key (optional) | None |
| `DB_HOST` | PostgreSQL host | localhost |
| `REDIS_URL` | Redis connection URL | redis://localhost:6379/0 |
| `MAX_PATCH_BYTES` | Maximum patch size to analyze | 400000 |
| `ADDITIONS_THRESHOLD` | Risk threshold for large changes | 1000 |

### GitHub App Setup

1. Create a GitHub App with these permissions:
   - **Repository permissions:**
     - Contents: Read
     - Issues: Write  
     - Pull requests: Write
     - Metadata: Read

2. **Subscribe to events:**
   - Pull request (opened, synchronize)

3. **Set webhook URL:** `https://your-domain.com/webhook/github`

## 📊 Risk Scoring System

The system calculates risk scores (0-100) based on:

- **Secrets Detected** (+25 points)
- **Large Changes** (+10 points for >1000 additions)
- **High-Risk Dependencies** (+15 points)
- **Security Files Modified** (+10 points)
- **Large Individual Files** (+10 points)
- **Configuration Changes** (+5-12 points)
- **Database Changes** (+8 points)

## 🧪 Test Suggestions

Automatically suggests tests for:
- **Positive Cases**: Valid input scenarios
- **Negative Cases**: Error handling and invalid inputs
- **Boundary Cases**: Edge values and limits
- **Integration Cases**: API calls, database operations, file I/O

## 📝 Example Output

```markdown
### 🤖 PR Intelligence Summary

**High-Level Summary**  
Feature addition: Modifies 3 Python files with 127 additions and 23 deletions, including 1 test file.

**Changelog**
- **Features:**
  - Added new user authentication functionality
- **Tests:**
  - Enhanced tests in: test_auth.py

### 🔐 Risk & Security
Risk Score: **35 / 100**  
**Risk Factors:**
- Security-sensitive files modified: 1 files

**Secrets Detected:** None ✅

### 🧪 Suggested Tests
**`auth/login.py`:**
- **Positive Test (validate_user)**: Test validate_user with valid inputs
- **Negative Test (validate_user)**: Test validate_user with invalid inputs

### ✅ Review Checklist
**High Priority:**
- [ ] **Security**: Verify authentication and authorization logic is secure and properly tested

**Medium Priority:**
- [ ] Testing: Consider adding more test coverage for the modified code
```

## 🔧 Development

### Project Structure
```
backend/
  app/
    main.py              # FastAPI application
    config.py            # Configuration management
    webhook/             # Webhook handling
    orchestrator/        # Agent coordination
    agents/              # Analysis agents
      repo_scanner.py    # Code analysis
      risk_security.py   # Security scanning
      test_synthesizer.py # Test suggestions
      reviewer.py        # Review checklists
    services/            # Core services
      github_client.py   # GitHub API client
      secret_scanner.py  # Secret detection
      diff_parser.py     # Diff analysis
    models/              # Data models
    queue/               # Background processing
```

### Running Tests
```bash
# Unit tests
docker-compose exec web pytest tests/

# With coverage
docker-compose exec web pytest --cov=app tests/
```

### Adding New Agents

1. Create agent class inheriting from `AbstractAgent`
2. Implement `run(ctx: PRContext) -> AgentResult` method
3. Add to orchestrator pipeline
4. Update comment builder for new output

## 🚀 Deployment

### Production Deployment

1. **Set up GitHub App** with production webhook URL
2. **Configure environment** with production credentials
3. **Deploy services** using Docker Compose or Kubernetes
4. **Set up monitoring** for health checks and metrics

### Scaling Considerations

- **Horizontal scaling**: Add more worker containers
- **Redis clustering**: For high-throughput scenarios  
- **Database optimization**: Connection pooling and indexing
- **Rate limiting**: Respect GitHub API limits

## 🔒 Security

- ✅ Webhook signature validation (HMAC SHA256)
- ✅ Secrets never logged in plain text
- ✅ GitHub App JWT authentication
- ✅ Input validation and sanitization
- ✅ Rate limiting and timeout protection

## 📈 Monitoring

Built-in instrumentation for:
- Processing latency per agent
- Risk score distribution
- Secret detection counts
- API call rates and errors
- Worker queue metrics

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details.

## 🆘 Support

- **Issues**: GitHub Issues
- **Discussions**: GitHub Discussions
- **Documentation**: `/docs` endpoint when running

---

**Generated by DevOps PR Auto-Orchestrator** 🤖