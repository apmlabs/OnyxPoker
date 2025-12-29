# OnyxPoker

**OnyxPoker** is a modular skeleton project for building a poker‐playing bot that can interact with online poker tables via screen capture and automatically execute actions.  The primary goal is to provide a clear starting point for research and experimentation, not a complete, polished bot.  The architecture separates the **frontend** (screen reading and UI interaction) from the **backend** (decision logic), so you can swap in more sophisticated strategies as your research evolves.

## Project Structure

```text
onyxpoker/
├── README.md            # This document – overview and usage instructions
├── requirements.txt      # Python dependencies
├── bot.py                # Top‑level script that ties the frontend and backend together
├── config.py             # Configuration constants (e.g. screen regions, timeouts)
├── frontend/
│   ├── __init__.py
│   └── screen_reader.py  # Functions for screen capture and OCR parsing
├── backend/
│   ├── __init__.py
│   └── strategy_gpt.py   # GPT‑based decision engine
└── utils.py              # Shared helper functions (e.g. card encoding)
```

The repository intentionally avoids complex features such as table selection, multi‑tabling or advanced game theory.  These are left as exercises for future research.

## Installation

### 1. Clone the repository

Use Git to clone your fork of this project.  If you’re reading this from GitHub, make sure you have appropriate permissions, then run:

```bash
git clone https://github.com/apmlabs/OnyxPoker.git
cd OnyxPoker
```

### 2. Install Python dependencies

It’s recommended to use a Python 3.9 or later virtual environment.  Install dependencies from `requirements.txt`:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

The key libraries include:

* **PyAutoGUI** – for taking screenshots and controlling the mouse/keyboard.
* **Pillow** (PIL) – image processing support used by PyAutoGUI.
* **pytesseract** – Python wrapper around Google’s Tesseract OCR engine to read numbers and text on the table.
* **opencv-python** – optional but useful for preprocessing images and template matching.
* **imagehash** – for perceptual hashing of card images (template matching alternative).
* **openai** – to call GPT models for decision making.  You must supply your own API key via the `OPENAI_API_KEY` environment variable.

If you plan to run OCR, make sure you have the Tesseract binary installed on your system.  On Ubuntu, you can install it with:

```bash
sudo apt-get update
sudo apt-get install tesseract-ocr
```

On macOS, `brew install tesseract` will install it.  See the [Tesseract documentation](https://tesseract-ocr.github.io/) for details.

### 3. Configure the table layout

Poker clients like PokerStars have different themes and can be resized.  To make screen capture reliable, the bot needs to know exactly where to look for cards, bets and buttons.  Edit `config.py` to set pixel coordinates (relative to the top‑left of the table window) for:

* `TABLE_REGION` – bounding box for the entire table (x, y, width, height).
* `HOLE_CARD_REGIONS` – list of bounding boxes for your two hole cards.
* `COMMUNITY_CARD_REGIONS` – bounding boxes for flop, turn and river cards.
* `POT_REGION` – region where the pot size is displayed.
* `STACK_REGIONS` – bounding boxes for each player’s stack count.
* `BUTTON_REGIONS` – bounding boxes for Fold, Call/Check and Raise buttons.

You can use a tool like screenshot software or Python’s `pyautogui.position()` interactive prompt to find these coordinates.  Make sure the table is always displayed at the same position and size on your screen.  If the layout changes (different theme or resolution), update these values accordingly.

## Usage

After installing dependencies and configuring the screen regions, you can run the bot with:

```bash
python bot.py
```

The bot will loop, waiting for your turn.  When it’s your turn, it will:

1. Capture relevant portions of the screen.
2. Use OCR and template matching to parse the current game state (hole cards, board cards, pot size, stack sizes, available actions, etc.).
3. Construct a prompt describing the situation and send it to the OpenAI API via the GPT‑based backend (see `backend/strategy_gpt.py`).
4. Parse the model’s response (expected to be `fold`, `call`, or `raise <amount>`).
5. Use PyAutoGUI to click the appropriate button and type any bet amount.

The default implementation is conservative.  It will log each decision to the console.  The actual call to the OpenAI API is wrapped in a timeout; if no response is received within the configured time (`GPT_TIMEOUT` in `config.py`), it will default to folding to avoid timing out at the table.

**Important:** Using automation on real money poker sites may violate their terms of service.  This project is provided for educational and research purposes only.  Do not use it on accounts or platforms where bots are prohibited.  You assume all responsibility for compliance with local laws and platform policies.

## Upgrading the Strategy

The current backend uses a GPT model as a simple decision engine.  It is easy to replace or augment this with a more sophisticated strategy.  Some possibilities:

* **Monte Carlo Equity Calculation** – Use a library like `eval7` to simulate random outcomes and estimate your hand’s equity against a range of opponent hands.  Decide based on pot odds.
* **Counterfactual Regret Minimization (CFR)** – Train a CFR agent offline on an abstracted version of Hold’em and load the resulting strategy into the backend.  You can integrate an existing library such as OpenSpiel or PyCFR.
* **Reinforcement Learning** – Use self‑play and deep RL (e.g. NFSP or ReBeL) to train a policy network.  Log game states and decisions from your bot and use them as training data.  Replace the GPT backend with your own neural network model.

To implement a different strategy, create a new module (e.g. `backend/strategy_montecarlo.py`) that exposes a `decide_action(state)` function returning an action dictionary.  Then update `bot.py` to import and use your new module.  Because the project is modular, you shouldn’t need to modify the frontend to change the decision logic.

## Logging

To aid in research and debugging, the bot prints and optionally logs each parsed state and decision.  You can redirect output to a file or integrate a proper logging library.  This log will be valuable for analyzing strategy performance, training RL models, or identifying OCR errors.

## Known Limitations

* **Screen Recognition Fragility** – If the table layout changes (different skin, theme, or resolution), you must update the coordinates in `config.py`.
* **Latency** – The OpenAI API introduces network delay.  For live play, keep response times short; the default timeout is 5 seconds.
* **No Table Selection** – The skeleton does not automatically find or join tables.  It operates on the assumption that you are already seated at a fixed table.
* **Terms of Service** – Many online poker sites forbid botting.  Use at your own risk.

## Contributing

If you extend the project or fix bugs, please document your changes and consider sending a pull request.  Contributions that improve parsing accuracy, reduce latency, or add new strategy backends are welcome.

## License

This project is open source under the MIT License.  See `LICENSE` for details.