import logging
import os
import re
from radon.complexity import cc_visit
from radon.metrics import mi_visit
from radon.raw import analyze

logger = logging.getLogger(__name__)

class CodeAnalyzer:
    """Analyzes code repositories and individual files for quality, complexity, and patterns."""
    
    def __init__(self):
        # Define supported languages and their file extensions
        self.supported_languages = {
            'python': ['.py'],
            'javascript': ['.js'],
            'typescript': ['.ts', '.tsx'],
            'java': ['.java'],
            'html': ['.html', '.htm'],
            'css': ['.css'],
            'markdown': ['.md']
        }
    
    def scan_repository(self, repo_path):
        """Scan an entire repository and analyze its code."""
        try:
            logger.info(f"Scanning repository at: {repo_path}")
            
            results = {
                'summary': {
                    'analyzed_files': 0,
                    'languages': {},
                    'complexity': {
                        'total_score': 0,
                        'average_score': 0
                    },
                    'lines': {
                        'code': 0,
                        'comment': 0,
                        'blank': 0,
                        'total': 0
                    }
                },
                'files': []
            }
            
            # Walk through repository
            for root, _, files in os.walk(repo_path):
                # Skip version control directories
                if '.git' in root:
                    continue
                    
                for file in files:
                    # Get file extension
                    _, ext = os.path.splitext(file)
                    ext = ext.lower()
                    
                    # Determine language based on extension
                    language = None
                    for lang, extensions in self.supported_languages.items():
                        if ext in extensions:
                            language = lang
                            break
                    
                    if not language:
                        continue  # Skip unsupported file types
                    
                    # Update language statistics
                    if language not in results['summary']['languages']:
                        results['summary']['languages'][language] = 0
                    results['summary']['languages'][language] += 1
                    
                    file_path = os.path.join(root, file)
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            
                        # Skip empty files
                        if not content.strip():
                            continue
                        
                        # Analyze the file
                        analysis = self.analyze_code(content, language)
                        
                        # Update summary statistics
                        results['summary']['analyzed_files'] += 1
                        results['summary']['complexity']['total_score'] += analysis.get('complexity', 0)
                        
                        results['summary']['lines']['code'] += analysis.get('lines', {}).get('code', 0)
                        results['summary']['lines']['comment'] += analysis.get('lines', {}).get('comment', 0)
                        results['summary']['lines']['blank'] += analysis.get('lines', {}).get('blank', 0)
                        results['summary']['lines']['total'] += analysis.get('lines', {}).get('total', 0)
                        
                        # Add file analysis
                        rel_path = os.path.relpath(file_path, repo_path)
                        results['files'].append({
                            'path': rel_path,
                            'language': language,
                            'analysis': analysis
                        })
                        
                    except Exception as e:
                        logger.warning(f"Could not analyze file {file_path}: {e}")
            
            # Calculate average complexity
            if results['summary']['analyzed_files'] > 0:
                results['summary']['complexity']['average_score'] = (
                    results['summary']['complexity']['total_score'] / results['summary']['analyzed_files']
                )
            
            return results
            
        except Exception as e:
            logger.error(f"Error scanning repository: {e}")
            return {"error": str(e)}
    
    def analyze_code(self, code, language):
        """Analyze a piece of code in a specified language."""
        try:
            analysis = {
                'language': language,
                'complexity': 0,
                'lines': {
                    'code': 0,
                    'comment': 0, 
                    'blank': 0,
                    'total': 0
                },
                'quality': 0,  # 0-100 scale
                'patterns': {},
                'issues': []
            }
            
            # Common analysis for all types: count lines
            total_lines = code.count('\n') + 1
            blank_lines = code.count('\n\n') + sum(1 for line in code.split('\n') if not line.strip())
            analysis['lines']['total'] = total_lines
            analysis['lines']['blank'] = blank_lines
            
            # Language-specific analysis
            if language == 'python':
                return self._analyze_python(code, analysis)
            elif language in ['javascript', 'typescript']:
                return self._analyze_js_ts(code, analysis)
            elif language == 'java':
                return self._analyze_java(code, analysis)
            else:
                # Basic analysis for other languages
                analysis['lines']['code'] = total_lines - blank_lines
                analysis['complexity'] = self._estimate_complexity(code)
                return analysis
                
        except Exception as e:
            logger.error(f"Error analyzing code: {e}")
            return {
                'language': language,
                'error': str(e),
                'complexity': 0,
                'lines': {
                    'total': code.count('\n') + 1,
                    'blank': 0,
                    'code': 0,
                    'comment': 0
                }
            }
    
    def _analyze_python(self, code, analysis):
        """Analyze Python code."""
        try:
            # Use radon for Python code analysis
            complexity_results = cc_visit(code)
            raw_metrics = analyze(code)
            maintainability = mi_visit(code, True)
            
            # Update analysis with radon results
            analysis['complexity'] = sum(item.complexity for item in complexity_results) if complexity_results else 0
            
            # Extract lines information
            analysis['lines']['code'] = raw_metrics.loc
            analysis['lines']['comment'] = raw_metrics.comments
            analysis['lines']['blank'] = raw_metrics.blank
            
            # Calculate quality score (0-100) based on maintainability index
            if maintainability:
                mi_score = maintainability[0].mi if maintainability else 0
                analysis['quality'] = min(100, max(0, mi_score))
            
            # Detect patterns and issues
            analysis['patterns'] = {
                'imports': len(re.findall(r'^import\s+|^from\s+.*\s+import', code, re.MULTILINE)),
                'classes': len(re.findall(r'^class\s+', code, re.MULTILINE)),
                'functions': len(re.findall(r'^def\s+', code, re.MULTILINE)),
                'todo_comments': len(re.findall(r'#.*TODO', code, re.IGNORECASE))
            }
            
            # Identify potential issues
            if analysis['complexity'] > 10:
                analysis['issues'].append({
                    'type': 'complexity',
                    'message': 'High cyclomatic complexity',
                    'severity': 'medium'
                })
            
            if analysis['quality'] < 50:
                analysis['issues'].append({
                    'type': 'quality',
                    'message': 'Low maintainability score',
                    'severity': 'medium'
                })
            
            # Check for long functions
            functions = re.findall(r'def\s+\w+\([^)]*\):\s*\n((?:\s+.*\n)+)', code)
            for func in functions:
                if func.count('\n') > 50:
                    analysis['issues'].append({
                        'type': 'function_length',
                        'message': 'Function is too long (>50 lines)',
                        'severity': 'low'
                    })
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error in Python analysis: {e}")
            analysis['error'] = str(e)
            return analysis
    
    def _analyze_js_ts(self, code, analysis):
        """Analyze JavaScript or TypeScript code."""
        # Count comment lines (simplified)
        single_line_comments = len(re.findall(r'^\s*\/\/.*$', code, re.MULTILINE))
        multi_line_comments = len(re.findall(r'\/\*[\s\S]*?\*\/', code))
        analysis['lines']['comment'] = single_line_comments + multi_line_comments
        analysis['lines']['code'] = analysis['lines']['total'] - analysis['lines']['blank'] - analysis['lines']['comment']
        
        # Estimate complexity
        analysis['complexity'] = self._estimate_complexity(code)
        
        # Calculate a basic quality score
        analysis['quality'] = max(0, min(100, 100 - (analysis['complexity'] * 5)))
        
        # Detect patterns
        analysis['patterns'] = {
            'imports': len(re.findall(r'^import\s+|^const\s+.*\s+=\s+require\(', code, re.MULTILINE)),
            'classes': len(re.findall(r'class\s+\w+', code)),
            'functions': len(re.findall(r'function\s+\w+|const\s+\w+\s+=\s+\(.*\)\s+=>', code)),
            'todo_comments': len(re.findall(r'\/\/.*TODO|\/\*.*TODO.*\*\/', code, re.IGNORECASE))
        }
        
        # Identify potential issues
        if analysis['complexity'] > 10:
            analysis['issues'].append({
                'type': 'complexity',
                'message': 'High cyclomatic complexity',
                'severity': 'medium'
            })
            
        # Check for long functions
        functions = re.findall(r'function\s+\w+\s*\([^)]*\)\s*{([\s\S]*?)}', code)
        for func in functions:
            if func.count('\n') > 50:
                analysis['issues'].append({
                    'type': 'function_length',
                    'message': 'Function is too long (>50 lines)',
                    'severity': 'low'
                })
        
        return analysis
    
    def _analyze_java(self, code, analysis):
        """Analyze Java code."""
        # Count comment lines (simplified)
        single_line_comments = len(re.findall(r'^\s*\/\/.*$', code, re.MULTILINE))
        multi_line_comments = len(re.findall(r'\/\*[\s\S]*?\*\/', code))
        analysis['lines']['comment'] = single_line_comments + multi_line_comments
        analysis['lines']['code'] = analysis['lines']['total'] - analysis['lines']['blank'] - analysis['lines']['comment']
        
        # Estimate complexity
        analysis['complexity'] = self._estimate_complexity(code)
        
        # Calculate a basic quality score
        analysis['quality'] = max(0, min(100, 100 - (analysis['complexity'] * 5)))
        
        # Detect patterns
        analysis['patterns'] = {
            'imports': len(re.findall(r'import\s+.*;', code)),
            'classes': len(re.findall(r'class\s+\w+|interface\s+\w+|enum\s+\w+', code)),
            'methods': len(re.findall(r'(public|private|protected|static|\s) +[\w<>\[\]]+\s+(\w+) *\([^\)]*\)', code)),
            'todo_comments': len(re.findall(r'\/\/.*TODO|\/\*.*TODO.*\*\/', code, re.IGNORECASE))
        }
        
        # Identify potential issues
        if analysis['complexity'] > 10:
            analysis['issues'].append({
                'type': 'complexity',
                'message': 'High cyclomatic complexity',
                'severity': 'medium'
            })
            
        # Check for long methods
        methods = re.findall(r'(public|private|protected|static|\s) +[\w<>\[\]]+\s+(\w+) *\([^\)]*\) *\{([\s\S]*?)\}', code)
        for method in methods:
            method_body = method[2] if len(method) > 2 else ""
            if method_body.count('\n') > 50:
                analysis['issues'].append({
                    'type': 'method_length',
                    'message': 'Method is too long (>50 lines)',
                    'severity': 'low'
                })
        
        return analysis
    
    def _estimate_complexity(self, code):
        """Estimate code complexity for any language."""
        # A basic estimation based on control structures
        # This is a simplified approach - real analysis would be more nuanced
        control_structures = len(re.findall(r'\b(if|else|for|while|switch|case|catch|try)\b', code))
        methods = len(re.findall(r'\b(function|def|method|procedure)\b', code))
        nestings = len(re.findall(r'{[^{}]*{', code))
        
        # Basic formula that weights different aspects
        complexity = control_structures + methods + (nestings * 2)
        
        # Normalize to a reasonable scale
        return min(30, max(1, complexity))
    
    def suggest_improvements(self, analysis):
        """Generate suggestions based on code analysis."""
        suggestions = []
        
        # Add suggestions from issues
        for issue in analysis.get('issues', []):
            suggestion = {
                'type': issue['type'],
                'message': issue['message'],
                'priority': 'high' if issue['severity'] == 'high' else 'medium' if issue['severity'] == 'medium' else 'low'
            }
            suggestions.append(suggestion)
        
        # Suggest adding comments if there's little documentation
        if analysis.get('lines', {}).get('comment', 0) < (analysis.get('lines', {}).get('code', 0) / 10):
            suggestions.append({
                'type': 'documentation',
                'message': 'Consider adding more comments - code has low documentation ratio',
                'priority': 'medium'
            })
        
        # Suggest refactoring if complexity is high
        complexity = analysis.get('complexity', 0)
        if complexity > 15:
            suggestions.append({
                'type': 'refactoring',
                'message': f'Consider refactoring - code has very high complexity ({complexity})',
                'priority': 'high'
            })
        elif complexity > 10:
            suggestions.append({
                'type': 'refactoring',
                'message': f'Consider breaking down complex parts - code has high complexity ({complexity})',
                'priority': 'medium'
            })
        
        # Suggest addressing TODOs
        todo_count = analysis.get('patterns', {}).get('todo_comments', 0)
        if todo_count > 0:
            suggestions.append({
                'type': 'todos',
                'message': f'Address {todo_count} TODOs in the code',
                'priority': 'low'
            })
        
        return suggestions
