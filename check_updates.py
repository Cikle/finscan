"""
Update Checker for FinScan Qt

Copyright (c) 2025 Cyril Lutziger
License: MIT (see LICENSE file for details)
"""
import os
import sys
import json
import subprocess
import requests
import platform
from datetime import datetime
import webbrowser

# Current version
VERSION = "1.0.1"  # Update this when releasing new versions

class UpdateChecker:
    """Handles checking for and applying updates to the FinScan application"""
    
    def __init__(self, auto_check=True, parent_window=None):
        """Initialize the update checker
        
        Args:
            auto_check (bool): Whether to check for updates automatically on initialization
            parent_window: Parent window for showing UI dialogs (if any)
        """
        self.parent = parent_window
        self.version = VERSION
        self.latest_version = None
        self.update_available = False
        self.update_info = {}
        
        if auto_check:
            self.check_for_updates()
    def check_for_updates(self):
        """Check for available updates using multiple methods
        
        Returns:
            bool: True if updates are available, False otherwise
        """
        # Try local Git repository first (if exists)
        if self._check_git_updates():
            return True
            
        # Try GitHub API (if repository releases exist)
        if self._check_github_updates():
            return True
        
        # Try direct version check from a server (if configured)
        if self._check_server_updates():
            return True
        
        # No updates found
        return False
    
    def _check_github_updates(self):
        """Check for updates using GitHub API"""
        try:
            # Check if a GitHub configuration file exists
            if not os.path.exists('github_config.json'):
                return False
            
            # Load GitHub configuration
            with open('github_config.json', 'r') as f:
                config = json.load(f)
            
            # Check if required fields are present
            if 'repo_owner' not in config or 'repo_name' not in config:
                return False
            
            # Prepare GitHub API URL
            owner = config['repo_owner']
            repo = config['repo_name']
            api_url = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"
              # Request latest release info
            print(f"Checking for updates at: {api_url}")
            response = requests.get(api_url, timeout=10)
            
            if response.status_code == 200:
                release_info = response.json()
                latest_version = release_info.get('tag_name', '').lstrip('v')
                
                print(f"Found remote version: {latest_version}, local version: {self.version}")
                
                # Compare versions
                if self._compare_versions(latest_version, self.version) > 0:
                    self.update_available = True
                    self.latest_version = latest_version
                    
                    # Store update info
                    self.update_info = {
                        'version': latest_version,
                        'release_notes': release_info.get('body', ''),
                        'download_url': release_info.get('html_url', ''),
                        'assets': release_info.get('assets', []),
                        'published_date': release_info.get('published_at', '')
                    }
                    return True
            else:
                # Handle API errors
                error_info = response.json() if response.content else {"message": "No response content"}
                print(f"GitHub API Error: {response.status_code} - {error_info.get('message', 'Unknown error')}")
                print(f"Make sure the repository {owner}/{repo} exists and has releases.")
            
            return False
            
        except Exception as e:
            print(f"Error checking GitHub updates: {e}")
            return False
    def _check_git_updates(self):
        """Check for updates using Git commands (if the app is in a Git repo)"""
        try:
            # Check if .git directory exists
            if not os.path.exists('.git'):
                print("No Git repository found (.git directory not found)")
                return False
                
            print("Git repository found. Fetching latest updates...")
            
            # Try to run git fetch
            fetch_result = subprocess.run(
                ['git', 'fetch'], 
                capture_output=True, 
                text=True,
                check=False
            )
            if fetch_result.returncode != 0:
                print(f"Git fetch failed: {fetch_result.stderr}")
                return False
                
            # Check if we're behind the remote
            status_result = subprocess.run(
                ['git', 'status', '-uno'], 
                capture_output=True, 
                text=True,
                check=False
            )
            
            print(f"Git status: {status_result.stdout.strip()}")
            
            # Get current branch
            branch_result = subprocess.run(
                ['git', 'branch', '--show-current'], 
                capture_output=True, 
                text=True,
                check=False
            )
            current_branch = branch_result.stdout.strip()
            if not current_branch:
                current_branch = "main"  # Default to main if branch detection fails
            
            # If we're behind, updates are available
            if "Your branch is behind" in status_result.stdout:
                # Get the number of commits behind
                count_result = subprocess.run(
                    ['git', 'rev-list', f'HEAD..origin/{current_branch}', '--count'], 
                    capture_output=True, 
                    text=True,
                    check=False
                )
                commit_count = count_result.stdout.strip()
                
                print(f"Updates available: {commit_count} commits behind origin/{current_branch}")
                
                # Store update information
                self.update_available = True
                self.update_info = {
                    'type': 'git',
                    'commits_behind': commit_count,
                    'branch': current_branch,
                    'message': f"Your local version is {commit_count} commits behind the latest version."
                }
                
                return True
            else:
                print("Your local version is up to date with the remote repository.")
                
            return False
            
        except Exception as e:
            print(f"Error checking Git updates: {e}")
            return False
    
    def _check_server_updates(self):
        """Check for updates from a server if configured"""
        try:
            # Check if server configuration exists
            if not os.path.exists('update_config.json'):
                return False
                
            # Load server configuration
            with open('update_config.json', 'r') as f:
                config = json.load(f)
            
            # Check if required fields are present
            if 'update_url' not in config:
                return False
                
            # Prepare update check URL
            update_url = config['update_url']
            
            # Make request to update server
            response = requests.get(update_url, timeout=10)
            if response.status_code == 200:
                update_info = response.json()
                
                # Check if response contains version information
                if 'version' in update_info:
                    latest_version = update_info['version']
                    
                    # Compare versions
                    if self._compare_versions(latest_version, self.version) > 0:
                        self.update_available = True
                        self.latest_version = latest_version
                        self.update_info = update_info
                        return True
            
            return False
            
        except Exception as e:
            print(f"Error checking server updates: {e}")
            return False
    
    def _compare_versions(self, version1, version2):
        """Compare two version strings (semantic versioning)
        
        Args:
            version1 (str): First version string (e.g., "1.2.3")
            version2 (str): Second version string (e.g., "1.2.4")
            
        Returns:
            int: 1 if version1 > version2, -1 if version1 < version2, 0 if equal
        """
        try:
            # Clean up version strings
            v1 = version1.lstrip('v')
            v2 = version2.lstrip('v')
            
            # Split into components
            v1_parts = [int(x) for x in v1.split('.')]
            v2_parts = [int(x) for x in v2.split('.')]
            
            # Ensure both have same number of components
            while len(v1_parts) < 3:
                v1_parts.append(0)
            while len(v2_parts) < 3:
                v2_parts.append(0)
                
            # Compare major.minor.patch
            for i in range(3):
                if v1_parts[i] > v2_parts[i]:
                    return 1
                if v1_parts[i] < v2_parts[i]:
                    return -1
                    
            # Versions are equal
            return 0
            
        except Exception:
            # If parsing fails, fall back to string comparison
            return 0
    
    def get_update_message(self):
        """Get a user-friendly update message"""
        if not self.update_available:
            return "Your application is up to date."
        
        if 'type' in self.update_info and self.update_info['type'] == 'git':
            return f"Update available from Git repository. " + self.update_info['message']
        
        if self.latest_version:
            return f"Version {self.latest_version} is available (you have {self.version})."
        
        return "An update is available."
    
    def apply_update(self):
        """Apply the available update
        
        Returns:
            bool: True if update started successfully, False otherwise
        """
        if not self.update_available:
            return False
            
        try:
            # If it's a Git update
            if 'type' in self.update_info and self.update_info['type'] == 'git':
                subprocess.Popen(['git', 'pull'], shell=True)
                return True
            
            # If it's a release with a download URL
            if 'download_url' in self.update_info:
                webbrowser.open(self.update_info['download_url'])
                return True
                
            # Otherwise, run the update script
            update_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'update_finscan.bat')
            if os.path.exists(update_script):
                if platform.system() == 'Windows':
                    subprocess.Popen(['start', update_script], shell=True)
                else:
                    subprocess.Popen([update_script], shell=True)
                return True
            
            return False
        
        except Exception as e:
            print(f"Error applying update: {e}")
            return False

# Example usage
if __name__ == "__main__":
    print("FinScan Qt Update Checker")
    print("========================")
    
    checker = UpdateChecker(auto_check=True)
    
    if checker.update_available:
        print(f"✅ {checker.get_update_message()}")
        
        # Ask if user wants to update
        answer = input("Do you want to update now? (y/n): ")
        if answer.lower() in ('y', 'yes'):
            success = checker.apply_update()
            if success:
                print("Update process started.")
            else:
                print("Failed to start update process.")
    else:
        print("✅ Your application is up to date.")
