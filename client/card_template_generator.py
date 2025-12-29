"""
Automated Card Template Generator
Generates synthetic card templates for template matching
"""

from PIL import Image, ImageDraw, ImageFont
import os

class CardTemplateGenerator:
    def __init__(self, output_dir='templates'):
        self.output_dir = output_dir
        self.ranks = ['A', 'K', 'Q', 'J', '10', '9', '8', '7', '6', '5', '4', '3', '2']
        self.suits = {
            's': '♠',  # Spades
            'h': '♥',  # Hearts
            'd': '♦',  # Diamonds
            'c': '♣'   # Clubs
        }
        self.suit_colors = {
            's': (0, 0, 0),      # Black
            'h': (255, 0, 0),    # Red
            'd': (255, 0, 0),    # Red
            'c': (0, 0, 0)       # Black
        }
        
    def generate_all_templates(self, card_width=50, card_height=70):
        """Generate templates for all 52 cards"""
        os.makedirs(self.output_dir, exist_ok=True)
        
        for rank in self.ranks:
            for suit_code, suit_symbol in self.suits.items():
                self._generate_card_template(rank, suit_code, suit_symbol, card_width, card_height)
        
        print(f"Generated 52 card templates in {self.output_dir}/")
    
    def _generate_card_template(self, rank, suit_code, suit_symbol, width, height):
        """Generate a single card template"""
        # Create white card background
        img = Image.new('RGB', (width, height), color='white')
        draw = ImageDraw.Draw(img)
        
        # Draw border
        draw.rectangle([0, 0, width-1, height-1], outline='black', width=2)
        
        # Get color for suit
        color = self.suit_colors[suit_code]
        
        # Try to use a font, fallback to default
        try:
            font_rank = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
            font_suit = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
        except:
            font_rank = ImageFont.load_default()
            font_suit = ImageFont.load_default()
        
        # Draw rank in top-left
        draw.text((5, 2), rank, fill=color, font=font_rank)
        
        # Draw suit below rank
        draw.text((5, 22), suit_symbol, fill=color, font=font_suit)
        
        # Draw rank in bottom-right (rotated)
        draw.text((width-20, height-25), rank, fill=color, font=font_rank)
        draw.text((width-20, height-45), suit_symbol, fill=color, font=font_suit)
        
        # Save template
        filename = f"{rank}{suit_code}.png"
        filepath = os.path.join(self.output_dir, filename)
        img.save(filepath)

if __name__ == '__main__':
    generator = CardTemplateGenerator()
    generator.generate_all_templates()
    print("Card templates ready for matching!")
