"""
Quick setup script to generate card templates
Run this once before using the bot
"""

from card_template_generator import CardTemplateGenerator
import os

def main():
    print("🎴 OnyxPoker Card Template Setup")
    print("=" * 50)
    
    # Check if templates already exist
    if os.path.exists('templates') and len(os.listdir('templates')) > 0:
        response = input("Templates already exist. Regenerate? (y/n): ")
        if response.lower() != 'y':
            print("✅ Using existing templates")
            return
    
    print("\n📝 Generating card templates...")
    generator = CardTemplateGenerator()
    generator.generate_all_templates()
    
    print("\n✅ Setup complete!")
    print("\nCard templates created in 'templates/' directory")
    print("You can now run the poker bot with card recognition enabled")
    print("\nNext steps:")
    print("1. Run poker_gui.py")
    print("2. Use Calibration tab to detect poker window")
    print("3. Test card recognition in Debug tab")

if __name__ == '__main__':
    main()
