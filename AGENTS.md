# OnyxPoker - AI-Powered GUI Automation Agent Context

## PROVEN SUCCESS FORMULA ✅
**Flask API + Kiro CLI + PyAutoGUI + HTTP Bridge = PERFECT real-time GUI automation**

## CRITICAL SECURITY RULES
**NEVER commit these files to git:**
- `.env*` files (contain API keys and authentication tokens)
- `screenshots/` directory (contains sensitive screen captures)
- `logs/` directory (may contain sensitive automation data)
- Windows client configuration files with credentials
- API authentication keys and secrets
- `SERVER_TEST_REPORT.md` (contains API keys and server details)
- `SERVER_QUICK_REFERENCE.md` (contains connection details)

**Before every commit, check for secrets:**
```bash
git diff --cached | grep -i "password\|secret\|key\|token\|api"
```

**If secrets are accidentally committed:**
1. Immediately rotate all exposed credentials
2. Remove from git history using filter-branch
3. Force push cleaned history
4. Update all affected systems

## Critical Infrastructure Requirements
- **Linux Server**: t3.medium (2 vCPU, 4GB RAM) - For Flask API + Kiro CLI
- **OS**: Ubuntu 22.04 (ami-0ea3c35c5c3284d82)
- **Disk**: 20GB minimum for logs and temporary screenshots
- **Security Group**: Ports 22 (SSH), 5000 (Flask API), 443 (HTTPS)
- **Windows Client**: Python 3.8+ with PyAutoGUI, requests, pillow

## ARCHITECTURE OVERVIEW ✅

### Windows Automation Client
- **Purpose**: Capture screenshots, execute mouse/keyboard actions
- **Technology**: Python + PyAutoGUI + requests
- **Communication**: HTTP POST to Linux server
- **Security**: API key authentication, encrypted image transfer

### Linux AI Analysis Server  
- **Purpose**: Process images with Kiro CLI, return action decisions
- **Technology**: Flask + subprocess + Kiro CLI integration
- **Communication**: HTTP API endpoints
- **Security**: Rate limiting, input validation, secure file handling

### HTTP Bridge Protocol
- **Endpoint**: POST /analyze-screenshot
- **Input**: Base64 encoded screenshot + context/goal
- **Output**: JSON with action type, coordinates, confidence
- **Authentication**: Bearer token or API key

## DEPLOYMENT STRATEGY ✅

### Phase 1: Core Infrastructure
1. Deploy Flask API server on Linux
2. Integrate Kiro CLI subprocess calls
3. Implement screenshot analysis endpoint
4. Add authentication and rate limiting

### Phase 2: Windows Client
1. Create PyAutoGUI automation script
2. Implement screenshot capture and HTTP upload
3. Add action execution based on API responses
4. Create configuration management

### Phase 3: Integration & Testing
1. End-to-end workflow testing
2. Performance optimization
3. Error handling and retry logic
4. Monitoring and logging

## SECURITY REQUIREMENTS ✅
- **API Authentication**: Bearer tokens for all endpoints
- **Input Validation**: Sanitize all uploaded images and parameters
- **Rate Limiting**: Prevent abuse with request throttling
- **Secure Storage**: Temporary files with proper cleanup
- **Audit Logging**: Track all automation actions and decisions
- **Network Security**: HTTPS only, firewall rules
- **Data Privacy**: No persistent storage of sensitive screenshots

## CRITICAL SUCCESS FACTORS
- **Real-time Performance**: Sub-2-second response times
- **Reliability**: Robust error handling and recovery
- **Scalability**: Handle multiple concurrent automation sessions
- **Maintainability**: Clean code structure and comprehensive logging
- **Security**: Zero-trust architecture with comprehensive validation

## MONITORING & ALERTING
- **API Health**: Endpoint availability and response times
- **Resource Usage**: CPU, memory, disk space monitoring
- **Error Rates**: Failed requests and automation errors
- **Security Events**: Authentication failures and suspicious activity
- **Performance Metrics**: Screenshot processing times and accuracy

## EMERGENCY PROCEDURES
- **API Downtime**: Fallback to manual operation mode
- **Security Breach**: Immediate credential rotation and system isolation
- **Performance Issues**: Auto-scaling and load balancing activation
- **Data Loss**: Backup and recovery procedures
