import logging
import os
from git import Repo
import tempfile
from django.conf import settings
from .code_analyzer import CodeAnalyzer
from integrations.github.client import GitHubConnector
from context_builder.trackers.models import ActivityEvent

logger = logging.getLogger(__name__)

class CodeAnalysisService:
    """Service to analyze code repositories and integrate with activity tracking"""
    
    def __init__(self):
        self.analyzer = CodeAnalyzer()
    
    def analyze_repository(self, repo_url, user_id=None, team_id=None):
        """Clone and analyze a Git repository."""
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                # Clone the repository
                logger.info(f"Cloning repository {repo_url} to {temp_dir}")
                repo = Repo.clone_from(repo_url, temp_dir)
                
                # Analyze the repository
                analysis_results = self.analyzer.scan_repository(temp_dir)
                
                # Track this analysis activity if user_id is provided
                if user_id:
                    from context_builder.trackers.models import ActivityTracker
                    tracker = ActivityTracker()
                    tracker.track_event(
                        user_id=user_id,
                        event_type='code_analysis',
                        title=f"Code analysis for {repo_url}",
                        description=f"Analyzed {analysis_results['summary']['analyzed_files']} files",
                        metadata={
                            'repository': repo_url,
                            'summary': analysis_results['summary']
                        },
                        source_system='pulsebot',
                        source_id=''
                    )
                
                return analysis_results
                
            except Exception as e:
                logger.error(f"Error analyzing repository {repo_url}: {e}")
                return {"error": f"Error analyzing repository: {str(e)}"}
    
    def analyze_github_pr(self, owner, repo, pr_number, user_id=None, team_id=None):
        """Analyze a specific GitHub pull request."""
        try:
            # Connect to GitHub
            github = GitHubConnector(user_id=user_id, team_id=team_id)
            
            # Get PR details
            pr_details = github._make_request('GET', f'/repos/{owner}/{repo}/pulls/{pr_number}')
            if not pr_details:
                return {"error": "Could not retrieve PR details"}
            
            # Get PR files
            files = github._make_request('GET', f'/repos/{owner}/{repo}/pulls/{pr_number}/files')
            if not files:
                return {"error": "Could not retrieve PR files"}
            
            results = {
                "pr": {
                    "number": pr_number,
                    "title": pr_details.get('title'),
                    "author": pr_details.get('user', {}).get('login'),
                    "created_at": pr_details.get('created_at'),
                    "updated_at": pr_details.get('updated_at')
                },
                "files_analyzed": 0,
                "languages": {},
                "complexity_score": 0,
                "suggestions": [],
                "file_analyses": []
            }
            
            # Analyze each file in the PR
            for file in files:
                filename = file.get('filename')
                status = file.get('status') # 'added', 'modified', 'removed'
                
                # Skip deleted files or files we can't analyze
                if status == 'removed' or not filename:
                    continue
                
                # Get file extension
                _, ext = os.path.splitext(filename)
                ext = ext.lower()
                
                # Determine language based on extension
                language_map = {
                    '.py': 'python',
                    '.js': 'javascript', 
                    '.ts': 'typescript',
                    '.java': 'java'
                }
                
                language = language_map.get(ext)
                if not language:
                    continue  # Skip unsupported file types
                
                # Get file content
                if file.get('raw_url'):
                    # Use the raw content URL if available
                    import requests
                    response = requests.get(file.get('raw_url'))
                    if response.status_code == 200:
                        content = response.text
                    else:
                        continue
                else:
                    # Otherwise try to get content via API
                    content_data = github._make_request('GET', f'/repos/{owner}/{repo}/contents/{filename}', 
                                                       params={'ref': pr_details.get('head', {}).get('ref')})
                    if not content_data or 'content' not in content_data:
                        continue
                    
                    import base64
                    content = base64.b64decode(content_data['content']).decode('utf-8')
                
                # Analyze the file
                analysis = self.analyzer.analyze_code(content, language)
                
                # Update statistics
                results["files_analyzed"] += 1
                if language not in results["languages"]:
                    results["languages"][language] = 0
                results["languages"][language] += 1
                
                results["complexity_score"] += analysis.get('complexity', 0)
                
                # Get suggestions
                suggestions = self.analyzer.suggest_improvements(analysis)
                for suggestion in suggestions:
                    suggestion['file'] = filename
                    results["suggestions"].append(suggestion)
                
                # Add file analysis
                results["file_analyses"].append({
                    "filename": filename,
                    "language": language,
                    "analysis": analysis
                })
            
            # Track this analysis
            if user_id:
                from context_builder.trackers.models import ActivityTracker
                tracker = ActivityTracker()
                tracker.track_event(
                    user_id=user_id,
                    event_type='pr_analysis',
                    title=f"PR analysis for {owner}/{repo}#{pr_number}",
                    description=f"Analyzed {results['files_analyzed']} files with {len(results['suggestions'])} suggestions",
                    metadata=results,
                    source_system='github',
                    source_id=str(pr_number)
                )
            
            return results
            
        except Exception as e:
            logger.error(f"Error analyzing PR {owner}/{repo}#{pr_number}: {e}")
            return {"error": f"Error analyzing PR: {str(e)}"}

    def analyze_code_snippet(self, code, language, user_id=None):
        """Analyze a single code snippet."""
        try:
            analysis = self.analyzer.analyze_code(code, language)
            suggestions = self.analyzer.suggest_improvements(analysis)
            
            results = {
                "language": language,
                "analysis": analysis,
                "suggestions": suggestions
            }
            
            # Track this analysis if user_id provided
            if user_id:
                from context_builder.trackers.models import ActivityTracker
                tracker = ActivityTracker()
                tracker.track_event(
                    user_id=user_id,
                    event_type='code_snippet_analysis',
                    title=f"Code snippet analysis ({language})",
                    description=f"Analyzed code snippet with {len(suggestions)} suggestions",
                    metadata=results,
                    source_system='pulsebot',
                    source_id=''
                )
            
            return results
            
        except Exception as e:
            logger.error(f"Error analyzing code snippet: {e}")
            return {"error": f"Error analyzing code: {str(e)}"}