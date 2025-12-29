# Card Recognition Quick Start

## 🎴 What's New

Your poker bot can now:
- ✅ **Auto-generate card templates** (52 cards)
- ✅ **Recognize cards** using OpenCV template matching
- ✅ **Validate with Kiro CLI** to ensure understanding is correct
- ✅ **Show validation status** in GUI with color coding

## 🚀 Quick Setup (2 minutes)

### Step 1: Generate Card Templates

```bash
cd client
python setup_cards.py
```

**Output:**
```
🎴 OnyxPoker Card Template Setup
==================================================
📝 Generating card templates...
✅ Generated 52 card templates in templates/
✅ Setup complete!
```

### Step 2: Launch GUI

```bash
python poker_gui.py
```

### Step 3: Test Card Recognition

1. **Calibration Tab**: Detect poker window
2. **Debug Tab**: Click "📸 Capture Now"
3. **Check OCR Analysis**: Should show detected cards
4. **Validate**: Click "✓ Validate State" to check with Kiro

## 🎯 How to Use

### In GUI

**Control Panel Tab:**
- Configure bot settings
- Start/stop bot
- Test connection and OCR

**Calibration Tab:**
- Scan for poker windows
- Auto-detect UI elements
- Save configuration

**Debug Tab:**
- Capture screenshots
- View OCR results
- **NEW**: Validate with Kiro CLI
- See raw game state

### Kiro Validation

**Two validation buttons:**

1. **✓ Validate State** - Checks if poker state makes sense
   - Are card values valid?
   - Is pot amount reasonable?
   - Do stacks make sense?
   - Returns confidence score

2. **✓ Validate UI** - Checks if UI detection is correct
   - Are all buttons found?
   - Is pot region detected?
   - Are card regions valid?

**Status Indicator:**
- 🟢 Green "✓ Valid" - Kiro confirms understanding
- 🔴 Red "✗ Invalid" - Kiro has concerns
- ⚪ Gray "Not validated" - Not checked yet

## 📊 What You'll See

### Before (Old System)
```
Cards: ['??', '??']
Board: []
```

### After (New System)
```
Cards: ['A♠', 'K♥']
Board: ['Q♦', 'J♣', '10♠']
```

### With Validation
```
✓ Valid (conf: 0.85)
Kiro: "This is a strong hand with AK offsuit..."
```

## 🔧 Troubleshooting

### Cards Show '??'

**Check:**
1. Templates generated? → Run `setup_cards.py`
2. Card regions calibrated? → Use Calibration tab
3. Poker window visible? → Must be on screen

**Test:**
```bash
cd client
python -c "from card_matcher import CardMatcher; m = CardMatcher(); print(f'{len(m.templates)} templates loaded')"
```

Should show: `52 templates loaded`

### Validation Fails

**Check:**
1. Kiro CLI installed? → `kiro-cli --version`
2. State captured? → Click "📸 Capture Now" first
3. Values reasonable? → Check OCR Analysis

**Test:**
```bash
echo "Is this a valid poker state: Cards As Kh, Pot 150?" | kiro-cli chat
```

## 🎮 Complete Workflow

1. **Setup** (one-time):
   ```bash
   python setup_cards.py
   ```

2. **Launch**:
   ```bash
   python poker_gui.py
   ```

3. **Calibrate**:
   - Calibration tab → Scan Windows
   - Select poker window
   - Auto-detect elements
   - Save config

4. **Test**:
   - Debug tab → Capture Now
   - Check cards detected
   - Validate State
   - Confirm Kiro understands

5. **Run Bot**:
   - Control Panel → Start Bot
   - Watch decisions
   - Monitor validation status

## 📈 Expected Performance

- **Template Generation**: < 1 second (one-time)
- **Card Matching**: < 50ms per card
- **Kiro Validation**: < 5 seconds
- **Total OCR + Validation**: < 7 seconds

## 🎯 Next Steps

1. **Test on Real Table**: Open PokerStars play money
2. **Measure Accuracy**: Log correct vs incorrect detections
3. **Adjust Threshold**: If too many false positives/negatives
4. **Capture Real Cards**: Replace synthetic templates if needed

## 📚 More Info

- **Full Documentation**: `client/CARD_RECOGNITION.md`
- **Code**: `card_template_generator.py`, `card_matcher.py`, `kiro_validator.py`
- **Configuration**: `config.py` (card regions)

## ✅ Success Checklist

- [ ] Templates generated (52 files in `templates/`)
- [ ] GUI launches without errors
- [ ] Cards detected (not '??')
- [ ] Kiro validation works
- [ ] Status shows green checkmark

**Ready to play poker with AI! 🎰🤖**
