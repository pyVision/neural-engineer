"""
Tests for the GitHub Analytics module using real repository data
"""
import os
import unittest
import pandas as pd
from datetime import datetime
from wiki_ai.github_analytics import GitHubAnalytics
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class TestGitHubAnalytics(unittest.TestCase):
    def setUp(self):
        """Set up test environment before each test"""
        # Use environment variable for GitHub token
        self.analytics = GitHubAnalytics()
        # Use a test directory for saving plots
        self.test_output_dir = "test_output"
        os.makedirs(self.test_output_dir, exist_ok=True)

    def tearDown(self):
        """Clean up test environment after each test"""
        # Remove test output directory and its contents
        if os.path.exists(self.test_output_dir):
            for file in os.listdir(self.test_output_dir):
                print(f" test output file: {os.path.join(self.test_output_dir, file)}")
            #     os.remove(os.path.join(self.test_output_dir, file))
            # os.rmdir(self.test_output_dir)

    def test_generate_all_plots_real_repo(self):
        """Test generating plots using a real GitHub repository"""
        # Use a well-known repository for testing
        repo_name = "Neoteroi/BlackSheep"
        #repo_name = "miko-ai-org/llmbatching"
        
        # Generate plots and get data
        plots, timeline_data = self.analytics.generate_all_plots(
            repo_name, 
            save_dir=self.test_output_dir
        )
        
        print(f"Generated plots for repository: {repo_name}")
        # Verify plots were generated
        self.assertIsNotNone(plots)
        self.assertIsNotNone(timeline_data)

        print(f"verified plots and timeline data for repository: {repo_name}")
        
        # Check if plot files were created
        expected_files = [
            f"{repo_name.replace('/', '_')}_timeline.html",
            f"{repo_name.replace('/', '_')}_timeline.png",
            f"{repo_name.replace('/', '_')}_heatmap.html",
            f"{repo_name.replace('/', '_')}_heatmap.png"
        ]
        
        for file in expected_files:
            file_path = os.path.join(self.test_output_dir, file)
            self.assertTrue(os.path.exists(file_path), f"File {file} was not created")
            self.assertTrue(os.path.getsize(file_path) > 0, f"File {file} is empty")
        
        # Verify timeline data structure
        self.assertIn('stars_df', timeline_data)
        self.assertIn('forks_df', timeline_data)
        self.assertIn('timeline_df', timeline_data)
        self.assertIn('milestones_df', timeline_data)
        
        # Print some basic statistics
        timeline_df = timeline_data['timeline_df']
        print(f"\nRepository: {repo_name}")
        print(f"Total Stars: {timeline_df['cumulative_stars'].iloc[-1]:,}")
        print(f"Total Forks: {timeline_df['cumulative_forks'].iloc[-1]:,}")
        
        if timeline_data['milestones_df'] is not None:
            print("\nMilestones:")
            for _, milestone in timeline_data['milestones_df'].iterrows():
                print(f"{milestone['date'].strftime('%Y-%m-%d')}: {milestone['description']}")

if __name__ == '__main__':
    unittest.main()
