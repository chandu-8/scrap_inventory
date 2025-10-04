from typing import List, Dict, Any
import os

class RequirementsManager:
    def __init__(self):
        self.current_file = None
        self.requirements = []
        self.current_file_path = None
    
    def load_file(self, file_path: str) -> bool:
        """Load and parse a cutlist file"""
        try:
            from excel_processor import parse_cutlist
            self.requirements = parse_cutlist(file_path)
            self.current_file = os.path.basename(file_path)
            self.current_file_path = file_path
            return True
        except Exception as e:
            print(f"Error loading file: {e}")
            return False
    
    def get_requirements(self) -> List[Dict]:
        """Get current requirements"""
        return self.requirements
    
    def get_unprocessed_requirements(self) -> List[Dict]:
        """Get requirements that haven't been processed yet"""
        return [req for req in self.requirements if not req['processed']]
    
    def clear_requirements(self):
        """Clear current requirements"""
        self.requirements = []
        self.current_file = None
        self.current_file_path = None
    
    def has_requirements(self) -> bool:
        """Check if there are any requirements"""
        return len(self.requirements) > 0
    
    def get_summary(self) -> Dict:
        """Get summary of requirements"""
        total_reqs = len(self.requirements)
        processed_reqs = len([req for req in self.requirements if req['processed']])
        unprocessed_reqs = total_reqs - processed_reqs
        
        return {
            'total_requirements': total_reqs,
            'processed_requirements': processed_reqs,
            'unprocessed_requirements': unprocessed_reqs,
            'current_file': self.current_file
        }
