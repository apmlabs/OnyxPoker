# OnyxPoker Project - Chat History

## Initial Requirements Discussion

**User Need:** AI that helps to code, can do screenshots of the browser, analyze and work with them in real time using Chrome or Firefox.

**Challenge Identified:** User runs app on Windows with PyAutoGUI as frontend to click screen and make screenshots, needs AI backend to analyze. User connects via SSH to AWS Linux where Kiro CLI runs, creating a disconnect between Windows GUI automation and Linux AI environment.

## Solution Architecture Discussion

**Options Evaluated:**
1. **File-Based Communication** - Windows saves screenshots, transfers via SCP, manual CLI interaction (~3-5 seconds)
2. **API Integration** - HTTP bridge between Windows and Linux with automated responses (~1-2 seconds) 
3. **Real-Time Workflow** - Manual intervention required each cycle (~10-30 seconds)

**Selected Solution:** Option 2 (API Integration) for fastest automated performance.

## Key Technical Insights

**Kiro CLI Capabilities Confirmed:**
- Can analyze images and screenshots provided as files
- Has image analysis capabilities as core feature
- Can provide intelligent action decisions based on visual content

**Architecture Decision:**
- **Windows Client**: PyAutoGUI for screenshot capture and action execution
- **Linux Server**: Flask API server integrating with Kiro CLI for AI analysis
- **Communication**: HTTP REST API with base64 image transfer
- **Authentication**: Bearer token security

## Implementation Approach

**Windows Python App:**
```python
# Take screenshot
screenshot = pyautogui.screenshot()
# Convert to base64 and send via HTTP
# Receive AI decision
# Execute action with pyautogui.click()
```

**Linux Flask Server:**
```python
# Receive base64 image via HTTP POST
# Save to temp file
# Call Kiro CLI for analysis
# Return JSON action response
```

**Communication Flow:**
1. Windows captures screenshot
2. Sends base64 data to Linux server via HTTP
3. Linux server processes with Kiro CLI
4. Returns action decision (click coordinates, type text, etc.)
5. Windows executes the action
6. Loop continues for automated workflow

## Project Structure Created

Complete project structure with:
- Flask API server with Kiro CLI integration
- Windows PyAutoGUI automation client  
- HTTP communication protocol
- Authentication and security
- Comprehensive documentation
- Setup scripts for both environments

**Speed Advantage:** ~1-2 seconds per cycle vs 3-5 seconds for file-based approach, fully automated without manual intervention.

## Next Development Steps

1. Test basic Flask server setup
2. Integrate actual Kiro CLI subprocess calls (currently mock responses)
3. Deploy and test end-to-end Windows to Linux communication
4. Optimize performance and add advanced features
