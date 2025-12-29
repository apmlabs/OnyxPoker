# Card Recognition System

## Overview

Automated card recognition using template matching with OpenCV. The system generates synthetic card templates and matches them against poker table screenshots.

## Components

### 1. Card Template Generator (`card_template_generator.py`)
- Generates 52 card templates (13 ranks × 4 suits)
- Creates synthetic card images with rank and suit symbols
- Saves templates to `templates/` directory
- Format: `{rank}{suit}.png` (e.g., `As.png`, `Kh.png`)

### 2. Card Matcher (`card_matcher.py`)
- Loads card templates on initialization
- Uses OpenCV template matching (TM_CCOEFF_NORMED)
- Returns card name and confidence score
- Formats cards for display (e.g., 'As' → 'A♠')

### 3. Kiro CLI Validator (`kiro_validator.py`)
- Validates poker table state with Kiro CLI
- Checks if detected values make sense
- Validates UI element detection
- Returns confidence scores and concerns

## Setup

### Step 1: Generate Templates

```bash
cd client
python setup_cards.py
```

This creates 52 card templates in `templates/` directory.

### Step 2: Verify Templates

Check that `templates/` contains files like:
- `As.png`, `Ah.png`, `Ad.png`, `Ac.png` (Aces)
- `Ks.png`, `Kh.png`, `Kd.png`, `Kc.png` (Kings)
- ... (all 52 cards)

## Usage

### In Code

```python
from card_matcher import CardMatcher
import cv2

# Initialize matcher
matcher = CardMatcher()

# Match a card image
card_image = cv2.imread('card_screenshot.png')
card_name, confidence = matcher.match_card(card_image)

print(f"Detected: {matcher.format_card(card_name)} (confidence: {confidence:.2f})")
```

### In GUI

1. **Generate Templates**: Run `setup_cards.py` once
2. **Calibrate**: Use Calibration tab to detect poker window
3. **Test OCR**: Click "📸 Test OCR" to see card detection
4. **Validate**: Use "✓ Validate State" to check with Kiro CLI

## How It Works

### Template Matching Process

1. **Capture**: Screenshot card region from poker table
2. **Convert**: Convert to grayscale for matching
3. **Resize**: Resize template to match card size
4. **Match**: Use OpenCV template matching
5. **Score**: Return best match with confidence
6. **Threshold**: Only accept matches > 0.7 confidence

### Kiro CLI Validation

1. **Parse State**: Extract cards, pot, stacks from OCR
2. **Build Prompt**: Create validation prompt for Kiro
3. **Send to Kiro**: Ask Kiro if state makes sense
4. **Parse Response**: Extract validity, concerns, confidence
5. **Display**: Show validation result in GUI

## Configuration

### Card Regions (`config.py`)

```python
HOLE_CARD_REGIONS = [
    (350, 500, 50, 70),  # Card 1: (x, y, width, height)
    (420, 500, 50, 70),  # Card 2
]

COMMUNITY_CARD_REGIONS = [
    (300, 250, 50, 70),  # Flop 1
    (360, 250, 50, 70),  # Flop 2
    (420, 250, 50, 70),  # Flop 3
    (480, 250, 50, 70),  # Turn
    (540, 250, 50, 70),  # River
]
```

### Matching Threshold

Adjust in `card_matcher.py`:
```python
def match_card(self, card_image, threshold=0.7):  # Lower = more lenient
```

## Troubleshooting

### Cards Not Detected ('??')

**Possible causes:**
1. Templates not generated → Run `setup_cards.py`
2. Card regions not calibrated → Use Calibration tab
3. Confidence too low → Lower threshold in `card_matcher.py`
4. Card images too different → Adjust template generation

**Solutions:**
- Check `templates/` directory exists with 52 files
- Verify card regions in `config.py` are correct
- Test with Debug tab → "📸 Capture Now"
- Check OCR Analysis output

### Low Confidence Scores

**Causes:**
- Different card design (PokerStars theme)
- Card size mismatch
- Poor image quality
- Lighting/color differences

**Solutions:**
- Capture actual card images from your table
- Replace synthetic templates with real captures
- Adjust preprocessing (grayscale, threshold)
- Use multiple templates per card

### Kiro Validation Fails

**Causes:**
- Kiro CLI not installed
- Invalid state (OCR errors)
- Timeout (slow response)

**Solutions:**
- Test Kiro CLI: `echo "test" | kiro-cli chat`
- Check OCR values are reasonable
- Increase timeout in `kiro_validator.py`

## Advanced: Custom Templates

### Capture Real Card Images

```python
from poker_reader import PokerScreenReader
import cv2

reader = PokerScreenReader()

# Capture your actual cards
for i, region in enumerate(config.HOLE_CARD_REGIONS):
    img = reader.capture_region(region)
    cv2.imwrite(f'real_card_{i}.png', img)
```

### Replace Templates

1. Capture cards from your poker table
2. Rename to match format: `As.png`, `Kh.png`, etc.
3. Place in `templates/` directory
4. Restart bot

## Performance

**Expected:**
- Template generation: < 1 second (one-time)
- Card matching: < 50ms per card
- Kiro validation: < 5 seconds

**Optimization:**
- Cache loaded templates (already done)
- Parallel matching for multiple cards
- Reduce template resolution if needed

## Integration with Bot

The card recognition is automatically integrated:

1. **poker_reader.py**: Uses `CardMatcher` for `get_hole_cards()`
2. **poker_gui.py**: Shows cards in Game State panel
3. **kiro_validator.py**: Validates detected cards
4. **poker_bot.py**: Uses cards for decision-making

## Next Steps

1. **Test on Real Table**: Open PokerStars, run bot
2. **Measure Accuracy**: Log correct vs incorrect detections
3. **Improve Templates**: Use real card captures if needed
4. **Optimize Threshold**: Adjust based on accuracy metrics

## Files

- `card_template_generator.py` - Template generation
- `card_matcher.py` - Template matching
- `kiro_validator.py` - Kiro CLI validation
- `setup_cards.py` - One-time setup script
- `templates/` - Generated card templates (52 files)

## Status

✅ Template generation implemented
✅ Template matching implemented
✅ Kiro validation implemented
✅ GUI integration complete
🔄 Testing on real tables (next step)
