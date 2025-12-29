"""
Kiro CLI Validator
Validates poker table understanding by asking Kiro CLI to interpret the state
"""

import subprocess
import json
from typing import Dict, Any

class KiroValidator:
    def __init__(self):
        self.kiro_path = 'kiro-cli'
    
    def validate_table_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send table state to Kiro CLI and get its understanding
        Returns: {
            'understood': bool,
            'interpretation': str,
            'concerns': list,
            'confidence': float
        }
        """
        prompt = self._build_validation_prompt(state)
        
        try:
            result = subprocess.run(
                ['kiro-cli', 'chat', prompt],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            response = result.stdout.strip()
            return self._parse_validation_response(response, state)
            
        except subprocess.TimeoutExpired:
            return {
                'understood': False,
                'interpretation': 'Timeout',
                'concerns': ['Kiro CLI timeout'],
                'confidence': 0.0
            }
        except Exception as e:
            return {
                'understood': False,
                'interpretation': f'Error: {str(e)}',
                'concerns': [str(e)],
                'confidence': 0.0
            }
    
    def _build_validation_prompt(self, state: Dict[str, Any]) -> str:
        """Build prompt asking Kiro to validate understanding"""
        return f"""I'm reading a poker table and got this state:

Cards: {state.get('hero_cards', [])}
Board: {state.get('community_cards', [])}
Pot: ${state.get('pot', 0)}
My Stack: ${state.get('hero_stack', 0)}
To Call: ${state.get('to_call', 0)}
Actions: {list(state.get('actions', {}).keys())}

Please validate:
1. Does this make sense as a poker situation?
2. Are there any impossible values?
3. What concerns do you have?
4. Rate confidence 0-1 that this is accurate.

Respond in format:
VALID: yes/no
CONCERNS: list any issues
CONFIDENCE: 0.0-1.0
INTERPRETATION: brief summary"""
    
    def _parse_validation_response(self, response: str, state: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Kiro's validation response"""
        lines = response.lower().split('\n')
        
        valid = False
        concerns = []
        confidence = 0.5
        interpretation = response[:200]  # First 200 chars
        
        for line in lines:
            if 'valid:' in line:
                valid = 'yes' in line or 'true' in line
            elif 'concern' in line:
                concerns.append(line.split(':', 1)[1].strip() if ':' in line else line)
            elif 'confidence:' in line:
                try:
                    conf_str = line.split(':', 1)[1].strip()
                    confidence = float(conf_str.split()[0])
                except:
                    pass
        
        return {
            'understood': valid,
            'interpretation': interpretation,
            'concerns': concerns if concerns else ['None'],
            'confidence': confidence
        }
    
    def validate_ui_detection(self, detected_elements: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate UI element detection (buttons, pot region, etc.)
        """
        prompt = f"""I detected these UI elements on a poker table:

Buttons found: {detected_elements.get('buttons', [])}
Pot region: {detected_elements.get('pot_region', 'Not found')}
Card regions: {detected_elements.get('card_regions', [])}
Confidence: {detected_elements.get('confidence', 0)}

Does this seem like a valid poker UI layout?
Are all required elements present?
Any concerns?

Respond: VALID yes/no, CONCERNS: list"""
        
        try:
            result = subprocess.run(
                ['kiro-cli', 'chat', prompt],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            response = result.stdout.strip().lower()
            valid = 'valid: yes' in response or 'valid yes' in response
            
            return {
                'valid': valid,
                'response': result.stdout.strip(),
                'concerns': self._extract_concerns(response)
            }
            
        except Exception as e:
            return {
                'valid': False,
                'response': f'Error: {str(e)}',
                'concerns': [str(e)]
            }
    
    def _extract_concerns(self, response: str) -> list:
        """Extract concerns from response"""
        concerns = []
        for line in response.split('\n'):
            if 'concern' in line.lower():
                concerns.append(line.strip())
        return concerns if concerns else ['None']

if __name__ == '__main__':
    validator = KiroValidator()
    
    # Test validation
    test_state = {
        'hero_cards': ['As', 'Kh'],
        'community_cards': [],
        'pot': 150,
        'hero_stack': 500,
        'to_call': 20,
        'actions': {'fold': 'Fold', 'call': 'Call 20', 'raise': 'Raise'}
    }
    
    result = validator.validate_table_state(test_state)
    print(f"Validation: {json.dumps(result, indent=2)}")
