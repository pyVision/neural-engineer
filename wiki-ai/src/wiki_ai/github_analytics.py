"""
GitHub Repository Analytics Module

This module provides functionality to analyze GitHub repository metrics such as stars and forks over time.
"""

import os
import io
import getpass
from PIL import Image
from github import Github
import pandas as pd
import numpy as np
from datetime import datetime
from tqdm import tqdm
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.io as pio

class GitHubAnalytics:
    """A class to analyze GitHub repository metrics like stars and forks."""
    
    def __init__(self, github_token=None):
        """
        Initialize the GitHub analytics client.
        
        Parameters:
        -----------
        github_token : str, optional
            GitHub personal access token. If not provided, will try to get from
            environment variable GITHUB_TOKEN or prompt user for input.
        """
        self.github_token = github_token or os.environ.get('GITHUB_TOKEN') or getpass.getpass('Enter your GitHub token: ')
        self.github_client = Github(self.github_token)

    def fetch_repo_data(self, repo_name):
        """
        Fetch stars and forks data for a given repository.
        
        Parameters:
        -----------
        repo_name : str
            Repository name in format "owner/repo" (e.g., "facebook/react")
            
        Returns:
        --------
        tuple
            Pandas DataFrames containing stars and forks data
        """
        print(f"Fetching data for repository: {repo_name}")
        
        try:
            # Get repository
            repo = self.github_client.get_repo(repo_name)
            
            # Get basic repository info
            print(f"Repository: {repo.full_name}")
            print(f"Description: {repo.description}")
            print(f"Stars: {repo.stargazers_count}")
            print(f"Forks: {repo.forks_count}")
            
            # Fetch stargazers data with pagination
            stars_data = []
            try:
                stars_paginated = repo.get_stargazers_with_dates()
                total_stars = repo.stargazers_count
                
                # Calculate number of pages (30 items per page is GitHub's default)
                total_pages = (total_stars + 29) // 30
                
                print(f"\nFetching {total_stars:,} stars data across {total_pages:,} pages...")
                
                # Initialize progress bar for pages
                with tqdm(total=total_stars, desc="Fetching stars") as pbar:
                    page_count = 0
                    batch_size = 100  # Process stars in batches
                    current_batch = []
                    
                    for star in stars_paginated:
                        current_batch.append({
                            'user': star.user.login,
                            'starred_at': star.starred_at
                        })
                        
                        # When batch is full or on last page, process it
                        if len(current_batch) >= batch_size or page_count >= total_pages - 1:
                            stars_data.extend(current_batch)
                            pbar.update(len(current_batch))
                            current_batch = []
                        
                            # Print progress every 100 stars
                            if len(stars_data) % 100 == 0:
                                print(f"\nProgress: {len(stars_data):,}/{total_stars:,} stars processed")
                        
                        page_count = len(stars_data) // 30


                            
            except Exception as star_error:
                print(f"\nError fetching stargazers with dates: {star_error}")
                # Fallback to basic stargazers info
                stars_data=[]

            
            # Fetch forks data with pagination
            forks_data = []
            total_forks = repo.forks_count
            forks_paginated = repo.get_forks()
            
            print(f"\nFetching {total_forks:,} forks data...")
            
            with tqdm(total=total_forks, desc="Fetching forks") as pbar:
                batch_size = 100
                current_batch = []
                
                for fork in forks_paginated:
                    current_batch.append({
                        'user': fork.owner.login,
                        'forked_at': fork.created_at
                    })
                    
                    # When batch is full, process it
                    if len(current_batch) >= batch_size:
                        forks_data.extend(current_batch)
                        pbar.update(len(current_batch))
                        current_batch = []
                        
                        # Print progress every 1000 forks
                        if len(forks_data) % 100 == 0:
                            print(f"\nProgress: {len(forks_data):,}/{total_forks:,} forks processed")
                
                # Process remaining items in the last batch
                if current_batch:
                    forks_data.extend(current_batch)
                    pbar.update(len(current_batch))
            
            # Convert to DataFrames
            stars_df = pd.DataFrame(stars_data)
            forks_df = pd.DataFrame(forks_data)
            
            return stars_df, forks_df
        
        except Exception as e:
            print(f"Error fetching repository data: {e}")
            return None, None

    def process_timeline_data(self, stars_df, forks_df, freq='D'):
        """
        Process the stars and forks data to create timeline dataset.
        
        Parameters:
        -----------
        stars_df : pandas.DataFrame
            DataFrame containing stars data
        forks_df : pandas.DataFrame
            DataFrame containing forks data
        freq : str
            Frequency for grouping ('D' for daily, 'W' for weekly, 'M' for monthly)
            
        Returns:
        --------
        pandas.DataFrame
            DataFrame with timeline data
        """
        if stars_df is None or forks_df is None or stars_df.empty or forks_df.empty:
            print("No data available to process")
            return None
        
        # Ensure datetime format
        if not pd.api.types.is_datetime64_dtype(stars_df['starred_at']):
            stars_df['starred_at'] = pd.to_datetime(stars_df['starred_at'])
        
        if not pd.api.types.is_datetime64_dtype(forks_df['forked_at']):
            forks_df['forked_at'] = pd.to_datetime(forks_df['forked_at'])
        
        # Group by date with specified frequency
        stars_count = stars_df.groupby(pd.Grouper(key='starred_at', freq=freq)).size()
        forks_count = forks_df.groupby(pd.Grouper(key='forked_at', freq=freq)).size()
        
        min1=min(stars_count.index)
        # Create a complete date range
        start_date = min(stars_count.index.min(), forks_count.index.min())
        print(f"Start date: {start_date} {stars_df['starred_at'].min()} {forks_df['forked_at'].min()}")
        end_date = max(stars_count.index.max(), forks_count.index.max())
        # Create index with complete date range
        date_range = pd.date_range(start=start_date, end=end_date, freq=freq)
        
        # Create final DataFrame
        timeline_df = pd.DataFrame(index=date_range)
        timeline_df['stars'] = stars_count
        timeline_df['forks'] = forks_count
        
        # Fill NaN values with 0
        timeline_df = timeline_df.fillna(0)
        
        # Add cumulative columns
        timeline_df['cumulative_stars'] = timeline_df['stars'].cumsum()
        timeline_df['cumulative_forks'] = timeline_df['forks'].cumsum()
        
        # Add new stars and forks columns
        timeline_df['new_stars'] = timeline_df['stars'].diff().fillna(0)
        timeline_df['new_forks'] = timeline_df['forks'].diff().fillna(0)
        
        return timeline_df

    def get_repo_info(self, repo_name):
        """
        Get basic information about a repository.
        
        Parameters:
        -----------
        repo_name : str
            Repository name in format "owner/repo"
            
        Returns:
        --------
        dict
            Dictionary containing repository information
        """
        try:
            repo = self.github_client.get_repo(repo_name)
            return {
                'name': repo.name,
                'full_name': repo.full_name,
                'description': repo.description,
                'stars': repo.stargazers_count,
                'forks': repo.forks_count,
                'language': repo.language,
                'created_at': repo.created_at,
                'updated_at': repo.updated_at,
                'homepage': repo.homepage,
                'topics': repo.get_topics()
            }
        except Exception as e:
            print(f"Error fetching repository info: {e}")
            return None

    def identify_milestones(self, timeline_df):
        """
        Identify key milestones and interesting points in the repository's history.
        
        Parameters:
        -----------
        timeline_df : pandas.DataFrame
            DataFrame containing timeline data
            
        Returns:
        --------
        pandas.DataFrame
            DataFrame with milestone information
        """
        if timeline_df is None or timeline_df.empty:
            return None
        
        milestones = []
        
        # 1. Find dates when the repository hit significant star counts
        significant_counts = [100, 1000, 5000, 10000, 25000, 50000, 100000]
        
        for count in significant_counts:
            milestone_row = timeline_df[timeline_df['cumulative_stars'] >= count].iloc[0] if any(timeline_df['cumulative_stars'] >= count) else None
            if milestone_row is not None:
                milestones.append({
                    'date': milestone_row.name,
                    'type': 'achievement',
                    'description': f'Reached {count:,} stars',
                    'stars': milestone_row['cumulative_stars'],
                    'forks': milestone_row['cumulative_forks']
                })
        
        # 2. Find days with unusually high star activity (>3 standard deviations)
        mean_stars = timeline_df['new_stars'].mean()
        std_stars = timeline_df['new_stars'].std()
        threshold = mean_stars + (3 * std_stars)
        
        exceptional_days = timeline_df[timeline_df['new_stars'] > max(threshold, 10)]
        
        for _, row in exceptional_days.iterrows():
            milestones.append({
                'date': row.name,
                'type': 'peak_activity',
                'description': f'Exceptional growth: {int(row["new_stars"])} new stars in one day',
                'stars': row['cumulative_stars'],
                'forks': row['cumulative_forks']
            })
        
        # Convert to DataFrame and sort by date
        milestones_df = pd.DataFrame(milestones)
        if not milestones_df.empty:
            milestones_df = milestones_df.sort_values('date')
        
        return milestones_df

    def plot_timeline(self, timeline_df, repo_name, save_dir=None, milestones_df=None):
        """
        Create an interactive timeline plot with three subplots:
        1. Cumulative growth with milestones
        2. New stars and forks bar plot
        3. Growth rate (30-day Rolling Average)

        Parameters:
        -----------
        timeline_df : pandas.DataFrame
            DataFrame containing timeline data
        repo_name : str
            Repository name for the plot title
        save_dir : str, optional
            Directory to save the plot. If None, plot won't be saved
        milestones_df : pandas.DataFrame, optional
            DataFrame containing milestone information
            
        Returns:
        --------
        plotly.graph_objects.Figure
            The generated plot figure
        """
        if timeline_df is None or timeline_df.empty:
            print("No data available to plot")
            return None
            
        # Create figure with secondary y-axis
        fig = make_subplots(
            rows=3, cols=1,
            subplot_titles=(
                'Repository Growth with Milestones',
                'New Stars and Forks Over Time',
                'Growth Rate '
            ),
            vertical_spacing=0.12,
            row_heights=[0.4, 0.3, 0.3]
        )
        
        # Plot 1: Cumulative growth with milestones
        fig.add_trace(
            go.Scatter(
                x=timeline_df.index,
                y=timeline_df['cumulative_stars'],
                mode='lines',
                name='Total Stars',
                line=dict(color='gold', width=3)
            ),
            row=1, col=1
        )
        
        fig.add_trace(
            go.Scatter(
                x=timeline_df.index,
                y=timeline_df['cumulative_forks'],
                mode='lines',
                name='Total Forks',
                line=dict(color='blue', width=3)
            ),
            row=1, col=1
        )
        
        # Add milestones if provided
        if milestones_df is not None and not milestones_df.empty:
            for i, milestone in milestones_df.iterrows():
                milestone_num = i + 1  # Start numbering from 1
                fig.add_trace(
                    go.Scatter(
                        x=[milestone['date']],
                        y=[milestone['stars']],
                        mode='markers+text',
                        name=f"M{milestone_num}: {milestone['description']}",
                        marker=dict(size=12, color='red', symbol='star'),
                        text=[f"M{milestone_num}"],
                        textposition='top center',
                        hoverinfo='text',
                        hovertext=f"Milestone {milestone_num}: {milestone['description']}<br>Date: {milestone['date'].strftime('%Y-%m-%d')}<br>Stars: {milestone['stars']}"
                    ),
                    row=1, col=1
                )
        
        # Plot 2: New stars and forks bar plot
        fig.add_trace(
            go.Bar(
                x=timeline_df.index,
                y=timeline_df['new_stars'],
                name='New Stars',
                marker_color='gold'
            ),
            row=2, col=1
        )
        
        fig.add_trace(
            go.Bar(
                x=timeline_df.index,
                y=timeline_df['new_forks'],
                name='New Forks',
                marker_color='blue'
            ),
            row=2, col=1
        )
        
        # Plot 3: Growth rate - 30-day rolling average
        window_size = 1
        timeline_df['stars_growth_rate'] = timeline_df['new_stars'].rolling(window=window_size).mean()
        timeline_df['forks_growth_rate'] = timeline_df['new_forks'].rolling(window=window_size).mean()
        
        fig.add_trace(
            go.Scatter(
                x=timeline_df.index,
                y=timeline_df['stars_growth_rate'],
                mode='lines',
                name=f'Stars ({window_size}-day avg)',
                line=dict(color='gold', width=3)
            ),
            row=3, col=1
        )
        
        fig.add_trace(
            go.Scatter(
                x=timeline_df.index,
                y=timeline_df['forks_growth_rate'],
                mode='lines',
                name=f'Forks ({window_size}-day avg)',
                line=dict(color='blue', width=3)
            ),
            row=3, col=1
        )
        
        # Update layout
        fig.update_layout(
            title=f'{repo_name} - Repository Analytics Dashboard',
            template='plotly_white',
            height=1200,  # Increased height for 3 subplots
            showlegend=False,  # We'll use individual legends for each subplot
            margin=dict(r=20, l=20)  # Reduced margins since legends are inside plots
        )
        
        # Update axis labels and add legends for each subplot
        fig.update_xaxes(title_text="Date", row=3, col=1)  # Only bottom plot shows x-axis title
        fig.update_yaxes(title_text="Count", row=1, col=1)
        fig.update_yaxes(title_text="Count", row=2, col=1)
        fig.update_yaxes(title_text="Average New Count (per 30 days)", row=3, col=1)

        # Add legends for each subplot with appropriate positioning
        fig.update_layout(
            showlegend=True,
            legend1=dict(
                yanchor="top",
                y=0.95,
                xanchor="left",
                x=1.0,
                title="Growth Metrics",
                bordercolor="Black",
                borderwidth=1,
            ),
            legend2=dict(
                yanchor="top",
                y=0.62,
                xanchor="left",
                x=1.0,
                title="New Activity",
                bordercolor="Black",
                borderwidth=1,
            ),
            legend3=dict(
                yanchor="top",
                y=0.28,
                xanchor="left",
                x=1.0,
                title="Growth Rate",
                bordercolor="Black",
                borderwidth=1,
            )
        )

        # Update legend groups to separate by subplot
        for trace in fig.data[:2 + (len(milestones_df) if milestones_df is not None else 0)]:
            trace.update(legendgroup="1", legend="legend1")
        for trace in fig.data[2 + (len(milestones_df) if milestones_df is not None else 0):4 + (len(milestones_df) if milestones_df is not None else 0)]:
            trace.update(legendgroup="2", legend="legend2")
        for trace in fig.data[4 + (len(milestones_df) if milestones_df is not None else 0):]:
            trace.update(legendgroup="3", legend="legend3")
        
        if save_dir:
            os.makedirs(save_dir, exist_ok=True)
            fig.write_html(os.path.join(save_dir, f"{repo_name.replace('/', '_')}_timeline.html"))
            
            try:
                # Try to save as PNG using regular plotly approach
                fig.write_image(os.path.join(save_dir, f"{repo_name.replace('/', '_')}_timeline.png"))
            except Exception as e:
                print(f"Could not save PNG with default renderer: {e}")
                print("Saving with alternative method...")
                
                try:
                    # First try kaleido
                    img_bytes = pio.to_image(fig, format="png", engine="kaleido")
                except Exception as e:
                    print(f"Failed to use kaleido: {e}")
                    try:
                        # Try orca
                        img_bytes = pio.to_image(fig, format="png", engine="orca")
                        
                        img = Image.open(io.BytesIO(img_bytes))
                        img.save(os.path.join(save_dir, f"{repo_name.replace('/', '_')}_timeline.png"))
                    except Exception as e:
                        print(f"All image export methods failed: {e}")
        
        return fig

    def plot_activity_heatmap(self, stars_df, repo_name, save_dir=None):
        """
        Create a heatmap showing activity patterns by day of week and hour.
        
        Parameters:
        -----------
        stars_df : pandas.DataFrame
            DataFrame containing stars data
        repo_name : str
            Repository name for the plot title
        save_dir : str, optional
            Directory to save the plot. If None, plot won't be saved
            
        Returns:
        --------
        plotly.graph_objects.Figure
            The generated plot figure
        """
        if stars_df is None or stars_df.empty:
            print("No data available to plot")
            return None
            
        # Extract day of week and hour from timestamp
        stars_df['day_of_week'] = stars_df['starred_at'].dt.day_name()
        stars_df['hour'] = stars_df['starred_at'].dt.hour
        
        # Create pivot table for heatmap
        activity_pivot = pd.pivot_table(
            stars_df,
            values='user',
            index='day_of_week',
            columns='hour',
            aggfunc='count',
            fill_value=0
        )
        
        # Reorder days of week
        days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        activity_pivot = activity_pivot.reindex(days_order)
        
        # Create heatmap
        fig = go.Figure(data=go.Heatmap(
            z=activity_pivot.values,
            x=[f"{i:02d}:00" for i in range(24)],
            y=activity_pivot.index,
            colorscale='Viridis'
        ))
        
        fig.update_layout(
            title=f"Activity Heatmap for {repo_name}",
            xaxis_title="Hour of Day (UTC)",
            yaxis_title="Day of Week",
            height=400
        )
        
        if save_dir:
            os.makedirs(save_dir, exist_ok=True)
            fig.write_html(os.path.join(save_dir, f"{repo_name.replace('/', '_')}_heatmap.html"))
            fig.write_image(os.path.join(save_dir, f"{repo_name.replace('/', '_')}_heatmap.png"))
            
        return fig

    def generate_all_plots(self, repo_name, save_dir='plots'):
        """
        Generate and save all available plots for a repository.
        
        Parameters:
        -----------
        repo_name : str
            Repository name in format "owner/repo"
        save_dir : str
            Directory to save the plots
            
        Returns:
        --------
        tuple
            (dict, dict) containing:
            - Dictionary of generated plot figures 
            - Dictionary of timeline data including DataFrames for stars, forks, timeline, and milestones
        """
        # Create save directory if it doesn't exist
        os.makedirs(save_dir, exist_ok=True)
        
        # Fetch repository data
        stars_df, forks_df = self.fetch_repo_data(repo_name)
        if stars_df is None or forks_df is None:
            print("Could not generate plots: No data available")
            return None, None
            
        # Process timeline data using monthly frequency
        timeline_df = self.process_timeline_data(stars_df, forks_df, freq='ME')
        
        # Identify milestones
        milestones_df = self.identify_milestones(timeline_df)
        
        # Generate plots
        plots = {}
        plots['timeline'] = self.plot_timeline(timeline_df, repo_name, save_dir, milestones_df)
        
        # Prepare timeline data
        timeline_data = {
            'stars_df': stars_df,
            'forks_df': forks_df,
            'timeline_df': timeline_df,
            'milestones_df': milestones_df
        }
        
        return plots, timeline_data
